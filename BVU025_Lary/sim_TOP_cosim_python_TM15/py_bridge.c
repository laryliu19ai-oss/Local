#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include "svdpi.h"

/* Extern SV functions exported from py_tester.sv */
extern void sv_set_tm_on(int val);
extern void sv_set_tm_meas(int val);
extern void sv_set_trim_code(int code);
extern void sv_set_clk(int val);
extern void sv_set_done(int val);
extern void sv_delay_ns(int ns);
extern int  sv_get_cmp(void);
extern void sv_finish_simulation(void);

/* Python C-Extension: onetest_hw wrappers */

static PyObject* py_set_tm_on(PyObject* self, PyObject* args) {
    int val = 0;
    if (!PyArg_ParseTuple(args, "i", &val)) return NULL;
    sv_set_tm_on(val);
    Py_RETURN_NONE;
}

static PyObject* py_set_tm_meas(PyObject* self, PyObject* args) {
    int val = 0;
    if (!PyArg_ParseTuple(args, "i", &val)) return NULL;
    sv_set_tm_meas(val);
    Py_RETURN_NONE;
}

static PyObject* py_set_trim_code(PyObject* self, PyObject* args) {
    int code = 0;
    if (!PyArg_ParseTuple(args, "i", &code)) return NULL;
    sv_set_trim_code(code);
    Py_RETURN_NONE;
}

static PyObject* py_set_clk(PyObject* self, PyObject* args) {
    int val = 0;
    if (!PyArg_ParseTuple(args, "i", &val)) return NULL;
    sv_set_clk(val);
    Py_RETURN_NONE;
}

static PyObject* py_set_done(PyObject* self, PyObject* args) {
    int val = 0;
    if (!PyArg_ParseTuple(args, "i", &val)) return NULL;
    sv_set_done(val);
    Py_RETURN_NONE;
}

static PyObject* py_get_cmp(PyObject* self, PyObject* args) {
    int cmp_val = sv_get_cmp();
    return PyLong_FromLong(cmp_val);
}

static PyObject* py_delay_ns(PyObject* self, PyObject* args) {
    int ns = 0;
    if (!PyArg_ParseTuple(args, "i", &ns)) return NULL;
    if (ns > 0) {
        sv_delay_ns(ns);
    }
    Py_RETURN_NONE;
}

static PyObject* py_delay_us(PyObject* self, PyObject* args) {
    double us = 0.0;
    if (!PyArg_ParseTuple(args, "d", &us)) {
        int us_int = 0;
        PyErr_Clear();
        if (!PyArg_ParseTuple(args, "i", &us_int)) return NULL;
        us = (double)us_int;
    }
    if (us > 0.0) {
        sv_delay_ns((int)(us * 1000.0));
    }
    Py_RETURN_NONE;
}

static PyObject* py_finish(PyObject* self, PyObject* args) {
    sv_finish_simulation();
    Py_RETURN_NONE;
}

static PyMethodDef onetest_hw_methods[] = {
    {"set_tm_on",     py_set_tm_on,     METH_VARARGS, "Set TMIRefOn digital pin (0 or 1)"},
    {"set_tm_meas",   py_set_tm_meas,   METH_VARARGS, "Set TMIRefMeas digital pin (0 or 1)"},
    {"set_trim_code", py_set_trim_code, METH_VARARGS, "Set NvTrmIref<5:0> bus (0..63)"},
    {"set_clk",       py_set_clk,       METH_VARARGS, "Set CLK digital pin (0 or 1)"},
    {"set_done",      py_set_done,      METH_VARARGS, "Set dDone digital pin (0 or 1)"},
    {"get_cmp",       py_get_cmp,       METH_NOARGS,  "Get dIRefTMO digital comparator value (0 or 1)"},
    {"delay_ns",      py_delay_ns,      METH_VARARGS, "Advance simulation time by specified nanoseconds"},
    {"delay_us",      py_delay_us,      METH_VARARGS, "Advance simulation time by specified microseconds"},
    {"finish",        py_finish,        METH_NOARGS,  "Finish simulation"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef onetest_hw_module = {
    PyModuleDef_HEAD_INIT,
    "onetest_hw",
    "Hardware Control DPI Bridge for OneTest Co-Simulation",
    -1,
    onetest_hw_methods
};

PyMODINIT_FUNC PyInit_onetest_hw(void) {
    return PyModule_Create(&onetest_hw_module);
}

/* Master Entry Point invoked by SystemVerilog py_tester initial block */
void c_main_tester(void) {
    printf("\n[py_bridge.c] =======================================================\n");
    printf("[py_bridge.c] Initializing Python-Led Virtual Tester Engine (DPI-C)...\n");
    printf("[py_bridge.c] =======================================================\n");

    if (PyImport_AppendInittab("onetest_hw", PyInit_onetest_hw) == -1) {
        fprintf(stderr, "[py_bridge.c] ERROR: Failed to register onetest_hw in inittab!\n");
        sv_finish_simulation();
        return;
    }

    if (!Py_IsInitialized()) {
        Py_Initialize();
    }

    PyRun_SimpleString(
        "import sys, os\n"
        "sys.dont_write_bytecode = True\n"  /* prevent stale .pyc masking new py_tester */
        "if 'py_tester' in sys.modules: del sys.modules['py_tester']\n"  /* force fresh load */
        "search_paths = [\n"
        "    os.getcwd(),\n"
        "    os.path.abspath(os.path.join(os.getcwd(), '../../..')),\n"
        "    os.path.abspath(os.path.join(os.getcwd(), '..')),\n"
        "    '/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_TM15',\n"
        "    '/home/lary/project/BVU025/SCH/cosim/pattern/TM15',\n"
        "    '/home/lary/project/BVU025/python/sim_TOP_cosim_python_TM15'\n"
        "]\n"
        "for p in search_paths:\n"
        "    if os.path.exists(p) and p not in sys.path:\n"
        "        sys.path.insert(0, p)\n"
        "print('[py_bridge.c] Python sys.path:', sys.path[:4])\n"
    );

    PyObject* pModule = PyImport_ImportModule("py_tester");
    if (pModule == NULL) {
        fprintf(stderr, "[py_bridge.c] ERROR: Failed to import py_tester module!\n");
        if (PyErr_Occurred()) PyErr_Print();
        Py_Finalize();
        sv_finish_simulation();
        return;
    }

    PyObject* pRunFunc = PyObject_GetAttrString(pModule, "run_test");
    if (pRunFunc == NULL || !PyCallable_Check(pRunFunc)) {
        fprintf(stderr, "[py_bridge.c] ERROR: py_tester.run_test function not found or not callable!\n");
        if (PyErr_Occurred()) PyErr_Print();
        Py_XDECREF(pRunFunc);
        Py_DECREF(pModule);
        Py_Finalize();
        sv_finish_simulation();
        return;
    }

    printf("[py_bridge.c] Handing over execution to Python master controller (py_tester.run_test)...\n\n");
    PyObject* pResult = PyObject_CallObject(pRunFunc, NULL);

    if (pResult == NULL) {
        fprintf(stderr, "[py_bridge.c] ERROR: py_tester.run_test failed during execution!\n");
        if (PyErr_Occurred()) PyErr_Print();
    } else {
        Py_DECREF(pResult);
    }

    Py_DECREF(pRunFunc);
    Py_DECREF(pModule);
    Py_Finalize();

    printf("\n[py_bridge.c] Python Master Test finished. Exiting simulation.\n");
    sv_finish_simulation();
}
