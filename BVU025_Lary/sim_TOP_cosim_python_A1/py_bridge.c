#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include "svdpi.h"

static PyObject* pModule = NULL;
static PyObject* pStepFunc = NULL;

/* Initialize Python Environment and load py_tester.py */
void py_init_tester(const char* work_dir) {
    if (!Py_IsInitialized()) {
        Py_Initialize();
    }
    
    PyRun_SimpleString("import sys, os\n"
                       "search_paths = [\n"
                       "    os.getcwd(),\n"
                       "    os.path.abspath(os.path.join(os.getcwd(), '../../..')),\n"
                       "    os.path.abspath(os.path.join(os.getcwd(), '..')),\n"
                       "    '/home/lary/simulation/BVU025/BVU025A/ocean/BVU025_Lary/sim_TOP_cosim_python_A1',\n"
                       "    '/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1',\n"
                       "    '/home/lary/project/BVU025/python/sim_TOP_cosim_python_A1'\n"
                       "]\n"
                       "for p in search_paths:\n"
                       "    if os.path.exists(p) and p not in sys.path:\n"
                       "        sys.path.insert(0, p)\n");
    
    pModule = PyImport_ImportModule("py_tester");
    if (pModule != NULL) {
        pStepFunc = PyObject_GetAttrString(pModule, "c_step_callback");
        if (pStepFunc && PyCallable_Check(pStepFunc)) {
            printf("[py_bridge.c] Python Virtual Tester successfully connected via DPI-C!\n");
        } else {
            fprintf(stderr, "[py_bridge.c] ERROR: c_step_callback not callable!\n");
            if (PyErr_Occurred()) PyErr_Print();
        }
    } else {
        fprintf(stderr, "[py_bridge.c] ERROR: Failed to import py_tester module!\n");
        if (PyErr_Occurred()) PyErr_Print();
    }
}

/* Call Python step function from SystemVerilog */
void py_tester_step(
    long long time_ns,
    int cmp_val,
    int* trim_code,
    int* clk_out,
    int* done_out,
    int* tm_on_out,
    int* tm_meas_out
) {
    if (!pStepFunc) {
        // Fallback safety values if Python is not initialized
        *trim_code = 0x20;
        *clk_out = 0;
        *done_out = 0;
        *tm_on_out = 1;
        *tm_meas_out = 0;
        return;
    }

    PyObject* pArgs = PyTuple_New(2);
    PyTuple_SetItem(pArgs, 0, PyLong_FromLongLong(time_ns));
    PyTuple_SetItem(pArgs, 1, PyLong_FromLong(cmp_val));

    PyObject* pValue = PyObject_CallObject(pStepFunc, pArgs);
    Py_DECREF(pArgs);

    if (pValue != NULL) {
        if (PyTuple_Check(pValue) && PyTuple_Size(pValue) == 5) {
            *trim_code   = (int)PyLong_AsLong(PyTuple_GetItem(pValue, 0));
            *clk_out     = (int)PyLong_AsLong(PyTuple_GetItem(pValue, 1));
            *done_out    = (int)PyLong_AsLong(PyTuple_GetItem(pValue, 2));
            *tm_on_out   = (int)PyLong_AsLong(PyTuple_GetItem(pValue, 3));
            *tm_meas_out = (int)PyLong_AsLong(PyTuple_GetItem(pValue, 4));
        }
        Py_DECREF(pValue);
    } else {
        fprintf(stderr, "[py_bridge.c] ERROR: Python step callback failed at time %lld ns!\n", time_ns);
        if (PyErr_Occurred()) PyErr_Print();
    }
}

/* Finalize Python */
void py_finish_tester(void) {
    Py_XDECREF(pStepFunc);
    Py_XDECREF(pModule);
    printf("[py_bridge.c] Python Virtual Tester closed successfully.\n");
}
