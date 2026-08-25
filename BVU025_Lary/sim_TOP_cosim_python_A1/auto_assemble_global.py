#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto-Assemble Engine for Cadence AMS Co-Simulation
Dynamically detects netlist directory, cleans subcircuit leaks,
links DPI-C bridges, configures Spectre probes, and binds HDL models.
"""

import os
import sys
import glob
import re
import json
import shutil

def parse_unit_val(s, default=0.0):
    if s is None:
        return default
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    multipliers = {
        'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3, 'k': 1e3, 'K': 1e3, 'M': 1e6, 'G': 1e9
    }
    match = re.match(r'^([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*([a-zA-Z]*)', s)
    if match:
        val = float(match.group(1))
        unit = match.group(2)
        if unit:
            for k, m in multipliers.items():
                if unit.startswith(k):
                    return val * m
        return val
    try:
        return float(s)
    except:
        return default

def find_first_existing(path_list):
    """Return the first path that exists from a list of candidates."""
    for p in path_list:
        if p and os.path.exists(p):
            return os.path.abspath(p)
    return None

def load_onetest_config(netlist_dir, top_cell, pattern_dir=None):
    """Find and load run_cosim.oneTest.json / cosim.oneTest.json dynamically from pattern or netlist directory."""
    search_paths = [
        os.path.join(pattern_dir, "run_cosim.oneTest.json") if pattern_dir else None,
        os.path.join(pattern_dir, "cosim.oneTest.json") if pattern_dir else None,
        os.path.join(netlist_dir, "run_cosim.oneTest.json"),
        os.path.join(netlist_dir, "cosim.oneTest.json"),
        os.path.join(os.getcwd(), "run_cosim.oneTest.json"),
        os.path.join(os.getcwd(), "cosim.oneTest.json")
    ]
    for p in search_paths:
        if p and os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    print(f"[Auto-Assemble] Loaded configuration from: {p}")
                    return cfg
            except Exception as e:
                print(f"[Auto-Assemble] Warning: failed to parse {p}: {e}")
    return {}

def universal_assemble(netlist_dir, pattern_dir=None):
    """Assemble AMS netlist, subcircuits, and control files using TM14 pattern objects."""
    netlist_dir = os.path.abspath(netlist_dir)
    
    # Resolve valid pattern directory containing run_cosim.oneTest.json / cosim.oneTest.json
    candidates = [
        pattern_dir,
        os.getcwd(),
        "/home/lary/project/BVU025/SCH/cosim/pattern/TM14",
        "c:/Antgravity/Local/BVU025_Lary/sim_TOP_cosim_python_A1",
        os.path.dirname(os.path.abspath(__file__))
    ]
    resolved_pattern_dir = None
    for cand in candidates:
        if cand and (os.path.exists(os.path.join(cand, "run_cosim.oneTest.json")) or os.path.exists(os.path.join(cand, "cosim.oneTest.json"))):
            resolved_pattern_dir = os.path.abspath(cand)
            break
    if not resolved_pattern_dir:
        resolved_pattern_dir = os.path.abspath(pattern_dir or os.path.dirname(os.path.abspath(__file__)))
    pattern_dir = resolved_pattern_dir
    
    cwd = os.getcwd()
    try:
        os.chdir(netlist_dir)
        print(f"[Auto-Assemble] Working in: {netlist_dir}")
        print(f"[Auto-Assemble] Using Pattern Objects from: {pattern_dir}")

        lib_name = "BVU025_Lary"
        top_cell = "sim_TOP_cosim_python_A1"

        design_info_path = os.path.join(netlist_dir, "designInfo")
        if os.path.exists(design_info_path):
            info = open(design_info_path, 'r', encoding='utf-8', errors='ignore').read()
            m_cell = re.search(r'cell\s+([^\s\n]+)', info)
            if m_cell:
                top_cell = m_cell.group(1).replace('"', '').strip()
            m_lib = re.search(r'library\s+([^\s\n]+)', info)
            if m_lib:
                lib_name = m_lib.group(1).replace('"', '').strip()

        print(f"[Auto-Assemble] Detected design: {lib_name}.{top_cell}")

        # Load dynamic settings strictly from cosim.oneTest.json (no default fallbacks)
        onetest_cfg = load_onetest_config(netlist_dir, top_cell, pattern_dir)
        if not onetest_cfg:
            raise ValueError(f"[Auto-Assemble] ERROR: Could not find or parse cosim.oneTest.json in {pattern_dir} or {netlist_dir}!")
            
        steps = onetest_cfg.get("oneTest", {}).get("setup", {}).get("steps", [])
        if not steps:
            raise ValueError("[Auto-Assemble] ERROR: No setup steps found in cosim.oneTest.json!")

        vdd_val = None
        t_power_up = None
        t_trim_start = None
        i_isar_val = None
        v_isar_limit = None
        t_measure_mode = None
        t_stop_sim = None

        for step in steps:
            s_id = step.get("id", "")
            s_time = parse_unit_val(step.get("time", {}).get("value"))
            actions = step.get("actions", {})
            
            if s_id == "power_up":
                t_power_up = s_time
                if "V_VDD" in actions:
                    vdd_val = parse_unit_val(actions["V_VDD"]["voltage"])
            elif s_id == "enable_iref_trim_mode":
                t_trim_start = s_time
            elif s_id == "force_calibration_current":
                if "I_ISAR" in actions:
                    i_isar_val = parse_unit_val(actions["I_ISAR"]["current"])
                    if "voltage_limiting" in actions["I_ISAR"]:
                        v_isar_limit = parse_unit_val(actions["I_ISAR"]["voltage_limiting"])
                    elif "voltage" in actions["I_ISAR"]:
                        v_isar_limit = parse_unit_val(actions["I_ISAR"]["voltage"])
            elif s_id == "enable_iref_measure_mode":
                t_measure_mode = s_time
            elif s_id == "capture_full_waveform":
                t_stop_sim = s_time

        # Validate that all required values were provided by cosim.oneTest.json
        if vdd_val is None:
            raise ValueError("[Auto-Assemble] ERROR: 'V_VDD' voltage not specified in cosim.oneTest.json 'power_up' step!")
        if t_power_up is None:
            raise ValueError("[Auto-Assemble] ERROR: 'power_up' step time not specified in cosim.oneTest.json!")
        if t_trim_start is None:
            raise ValueError("[Auto-Assemble] ERROR: 'enable_iref_trim_mode' step time not specified in cosim.oneTest.json!")
        if i_isar_val is None:
            raise ValueError("[Auto-Assemble] ERROR: 'I_ISAR' current not specified in cosim.oneTest.json 'force_calibration_current' step!")
        if v_isar_limit is None:
            v_isar_limit = vdd_val
        if t_measure_mode is None:
            raise ValueError("[Auto-Assemble] ERROR: 'enable_iref_measure_mode' step time not specified in cosim.oneTest.json!")
        if t_stop_sim is None:
            raise ValueError("[Auto-Assemble] ERROR: 'capture_full_waveform' step time not specified in cosim.oneTest.json!")

        print(f"[Auto-Assemble] Applied dynamic parameters strictly from cosim.oneTest.json:")
        print(f"  - VDD Voltage        : {vdd_val} V (Power-up @ {t_power_up*1e6:.1f} us)")
        print(f"  - Calibration Current: {i_isar_val*1e6:.2f} uA (Voltage Limit: {v_isar_limit:.2f} V, Trim Mode @ {t_trim_start*1e6:.1f} us ~ {t_measure_mode*1e3:.2f} ms)")
        print(f"  - Measurement Mode   : Switch @ {t_measure_mode*1e3:.2f} ms")
        print(f"  - Simulation Stop    : {t_stop_sim*1e3:.2f} ms")

        # 1. Header and HDL files
        header_file = os.path.join(netlist_dir, '.amsOSSHeader')
        h = open(header_file).read() if os.path.exists(header_file) else ''
        hdl_info_file = os.path.join(netlist_dir, '.hdlFileInfo_forNetlist')
        hdl = open(hdl_info_file).read() if os.path.exists(hdl_info_file) else ''

        # 2. Common digital helpers
        common_digital_helpers = f"""
// Common Helper Modules for {lib_name}
`timescale 1ns / 1ns 

`worklib {lib_name}
`view functional

module Buffer_DIG (out, in);
output out;
input in;
assign out = in;
endmodule
"""

        # 3. Clean TOP_A1 Module Definition
        top_a1_block = f"""
// Specialized 3.3V TOP_A1 Module
`timescale 1ns / 1ns 

`worklib {lib_name}
`view schematic

(* cds_ams_schematic *) 
module TOP_A1 (dIRefTMO, GPIO8, aVdd, aVss, NvTrmIref, TMIRefMeas, TMIRefOn);
output dIRefTMO;
inout GPIO8, aVdd, aVss;
input TMIRefMeas, TMIRefOn;
input [5:0] NvTrmIref;

electrical GPIO8, aVdd, aVss;
wire TMIRefOni, TMIRefMeasi;
electrical aTrimRef_5, aTrimRef_4, aTrimRef_3, aTrimRef_2, aTrimRef_1, aTrimRef_0;
electrical eTMIRefOn, eTMIRefMeas;

real vtrim_5, vtrim_4, vtrim_3, vtrim_2, vtrim_1, vtrim_0;
real vtmon, vtmmeas;

analog begin
    vtrim_5 = (NvTrmIref[5] == 1'b1 ? {vdd_val:.4f} : 0.0);
    vtrim_4 = (NvTrmIref[4] == 1'b1 ? {vdd_val:.4f} : 0.0);
    vtrim_3 = (NvTrmIref[3] == 1'b1 ? {vdd_val:.4f} : 0.0);
    vtrim_2 = (NvTrmIref[2] == 1'b1 ? {vdd_val:.4f} : 0.0);
    vtrim_1 = (NvTrmIref[1] == 1'b1 ? {vdd_val:.4f} : 0.0);
    vtrim_0 = (NvTrmIref[0] == 1'b1 ? {vdd_val:.4f} : 0.0);

    vtmon   = (TMIRefOni == 1'b1 ? {vdd_val:.4f} : 0.0);
    vtmmeas = (TMIRefMeasi == 1'b1 ? {vdd_val:.4f} : 0.0);

    V(aTrimRef_5, aVss) <+ transition(vtrim_5, 0, 10e-09, 10e-09);
    V(aTrimRef_4, aVss) <+ transition(vtrim_4, 0, 10e-09, 10e-09);
    V(aTrimRef_3, aVss) <+ transition(vtrim_3, 0, 10e-09, 10e-09);
    V(aTrimRef_2, aVss) <+ transition(vtrim_2, 0, 10e-09, 10e-09);
    V(aTrimRef_1, aVss) <+ transition(vtrim_1, 0, 10e-09, 10e-09);
    V(aTrimRef_0, aVss) <+ transition(vtrim_0, 0, 10e-09, 10e-09);

    V(eTMIRefOn, aVss)   <+ transition(vtmon, 0, 10e-09, 10e-09);
    V(eTMIRefMeas, aVss) <+ transition(vtmmeas, 0, 10e-09, 10e-09);
end

Bias_A1 I_Bias (
    .En(aVdd),
    .IRefTMO(dIRefTMO),
    .SUB(aVss),
    .TMIRefMeas(eTMIRefMeas),
    .TMIRefOn(eTMIRefOn),
    .VBNC(VBNC),
    .VBNC1(VBNC),
    .aVdd(aVdd),
    .aVss(aVss),
    .ibp_250n_0(net1),
    .rgTrim_IRef_5(aTrimRef_5),
    .rgTrim_IRef_4(aTrimRef_4),
    .rgTrim_IRef_3(aTrimRef_3),
    .rgTrim_IRef_2(aTrimRef_2),
    .rgTrim_IRef_1(aTrimRef_1),
    .rgTrim_IRef_0(aTrimRef_0),
    .xIRefTMIO(GPIO8)
);

Buffer_DIG I_BUF1 ( .out(TMIRefOni), .in(TMIRefOn));
Buffer_DIG I_BUF2 ( .out(TMIRefMeasi), .in(TMIRefMeas));

endmodule
"""

        # 4. Clean Board_A1 Module Definition (wraps TOP_A1)
        board_a1_block = f"""
// Specialized 3.3V Board_A1 Module
`timescale 1ns / 1ns 

`worklib {lib_name}
`view schematic

(* cds_ams_schematic *) 
module Board_A1 (dIRefTMO, GPIO8, aVdd, aVss, NvTrmIref, TMIRefMeas, TMIRefOn);
output dIRefTMO;
inout GPIO8, aVdd, aVss;
input TMIRefMeas, TMIRefOn;
input [5:0] NvTrmIref;

TOP_A1 TOP (
    .GPIO8(GPIO8),
    .aVdd(aVdd),
    .aVss(aVss),
    .dIRefTMO(dIRefTMO),
    .NvTrmIref(NvTrmIref[5:0]),
    .TMIRefMeas(TMIRefMeas),
    .TMIRefOn(TMIRefOn)
);

endmodule
"""

        # 5. Dynamically locate HDL source files (Buffer_DIG and py_tester)
        buffer_dig_candidates = [
            os.path.join(pattern_dir, "Buffer_DIG.v"),
            f"/home/lary/project/BVU025/SCH/{lib_name}/Buffer_DIG/functional/verilog.v",
            os.path.join(netlist_dir, "Buffer_DIG.v")
        ]
        buffer_dig_path = find_first_existing(buffer_dig_candidates) or buffer_dig_candidates[0]

        py_tester_sv_candidates = [
            os.path.join(pattern_dir, "py_tester.sv"),
            f"/home/lary/project/BVU025/SCH/{lib_name}/py_tester/systemVerilog/verilog.sv",
            os.path.join(netlist_dir, "py_tester.sv")
        ]
        py_tester_sv_path = find_first_existing(py_tester_sv_candidates) or py_tester_sv_candidates[0]

        # 6. TB block with exact schematic instance names: Board & TESTER
        tb_block = f"""
// Exact Schematic Top Module for {top_cell}
`timescale 1ns / 1ns 

`worklib {lib_name}
`view schematic

(* cds_ams_schematic *) 
module {top_cell} ();

wire [5:0] NvTrmIref;
wire TMIRefOn, TMIRefMeas, dIRefTMO;
wire CLK, dDone;
electrical VDD_PCB, VSS_PCB, GPIO8;
ground VSS_PCB;

real i_isar_target;

analog begin
    // Dynamic Power Supply from cosim.oneTest.json ({vdd_val}V)
    V(VDD_PCB, VSS_PCB) <+ transition(($abstime < {t_power_up:.6e} ? 0.0 : {vdd_val:.4f}), 0, 10e-06);

    // Dynamic Calibration Current from cosim.oneTest.json ({i_isar_val*1e6:.2f} uA)
    i_isar_target = ($abstime >= {t_trim_start:.6e} && $abstime < {t_measure_mode:.6e}) ? {i_isar_val:.6e} : 0.0;
    I(VDD_PCB, GPIO8) <+ transition(i_isar_target, 0, 10e-09);

    // Voltage Compliance Limit for I_ISAR (clamps GPIO8 so it does not exceed {v_isar_limit:.4f}V)
    if ($abstime >= {t_trim_start:.6e} && $abstime < {t_measure_mode:.6e} && V(GPIO8, VSS_PCB) > {v_isar_limit:.4f}) begin
        I(GPIO8, VDD_PCB) <+ (V(GPIO8, VSS_PCB) - {v_isar_limit:.4f}) / 1e-3;
    end

    // Dynamic Measurement Mode from cosim.oneTest.json (10 Ohm Sense Load @ >= {t_measure_mode*1e3:.2f} ms)
    if ($abstime >= {t_measure_mode:.6e}) begin
        I(GPIO8, VSS_PCB) <+ V(GPIO8, VSS_PCB) / 10.0;
    end
end

// Board_A1 Instance: Board
Board_A1 Board (
    .GPIO8(GPIO8),
    .dIRefTMO(dIRefTMO),
    .NvTrmIref(NvTrmIref[5:0]),
    .aVss(VSS_PCB),
    .aVdd(VDD_PCB),
    .TMIRefOn(TMIRefOn),
    .TMIRefMeas(TMIRefMeas)
);

// py_tester Instance: TESTER
py_tester TESTER (
    .TMIRefOn(TMIRefOn),
    .TMIRefMeas(TMIRefMeas),
    .CLK(CLK),
    .dDone(dDone),
    .NvTrmIref(NvTrmIref[5:0]),
    .dIRefTMO(dIRefTMO)
);

endmodule
"""
        amsbind_content = f"""// Binding AMSD Control Block for {lib_name}.{top_cell}:config
amsd {{
\tconfig designtop="{lib_name}.{top_cell}:schematic"

\tconfig cell="Buffer_DIG" lib="{lib_name}" view="functional"
\tconfig cell="Board_A1" lib="{lib_name}" view="schematic"
\tconfig cell="TOP_A1" lib="{lib_name}" view="schematic"
\tconfig cell="Bias_A1" lib="{lib_name}" view="analogtext"
}}
"""
        text_inputs = f"""// HDL file for Lib - {lib_name} ,Cell - Buffer_DIG, View - functional
-amscompilefile "file:{buffer_dig_path} lib:{lib_name} cell:Buffer_DIG view:functional"

// HDL file for Lib - {lib_name} ,Cell - py_tester, View - systemVerilog
-amscompilefile "file:{py_tester_sv_path} lib:{lib_name} cell:py_tester view:systemVerilog"

-makelib umc18cdmos
-endlib
-makelib {lib_name}
-endlib
"""

        # Write netlist.vams with exact schematic nets & instances
        full_vams = h + '\n\n`include "disciplines.vams"\n`include "userDisciplines.vams"\n\n' + hdl + common_digital_helpers + '\n\n' + top_a1_block + '\n\n' + board_a1_block + '\n\n' + tb_block + '\n'
        with open(os.path.join(netlist_dir, 'netlist.vams'), 'w') as f:
            f.write(full_vams)

        # 7. Clean Subcircuits: Copy only genuine subckt blocks (filter any leaked testbench lines)
        raw_scs = ""
        candidate_subckts = [
            os.path.join(netlist_dir, "subckts.scs"),
            os.path.join(netlist_dir, "analog", "netlist")
        ]
        
        found_subckt_file = find_first_existing(candidate_subckts)
        if found_subckt_file:
            raw_scs = open(found_subckt_file, 'r', encoding='utf-8', errors='ignore').read()

        final_lines = ['simulator lang=spectre\nglobal 0\n\n']
        in_subckt = False
        skip_subckt = False

        for line in raw_scs.splitlines(True):
            stripped = line.strip()
            if stripped.startswith('subckt '):
                parts = stripped.split()
                subckt_name = parts[1] if len(parts) > 1 else ''
                if subckt_name.startswith('sim_'):
                    in_subckt = False
                    skip_subckt = True
                else:
                    in_subckt = True
                    skip_subckt = False
            if in_subckt and not skip_subckt:
                final_lines.append(line)
            if stripped.startswith('ends ') or stripped == 'ends':
                if in_subckt and not skip_subckt:
                    final_lines.append('\n')
                in_subckt = False
                skip_subckt = False

        dest_subckts = os.path.join(netlist_dir, 'subckts.scs')
        with open(dest_subckts, 'w') as f:
            f.writelines(final_lines)

        # 8. Invalidate top-level elaboration snapshot so dynamic parameters in netlist.vams always take effect
        xcelium_d = os.path.join(netlist_dir, "xcelium.d")
        _snaps_deleted = []
        if os.path.exists(xcelium_d):
            worklib_dir = os.path.join(xcelium_d, "worklib")
            if os.path.exists(worklib_dir):
                for item in os.listdir(worklib_dir):
                    if item.startswith("sim_"):
                        p = os.path.join(worklib_dir, item)
                        if os.path.isdir(p):
                            shutil.rmtree(p, ignore_errors=True)
                            _snaps_deleted.append(p)
            for item in os.listdir(xcelium_d):
                if item.startswith("sim_"):
                    p = os.path.join(xcelium_d, item)
                    if os.path.islink(p):
                        os.unlink(p)
                        _snaps_deleted.append(p)
                    elif os.path.isdir(p):
                        shutil.rmtree(p, ignore_errors=True)
                        _snaps_deleted.append(p)
        if _snaps_deleted:
            print(f"[Auto-Assemble] Invalidated snapshots: {_snaps_deleted}")
        else:
            print(f"[Auto-Assemble] No stale snapshots found in: {netlist_dir}/xcelium.d/")

        # 9. Update spiceModels.scs
        spice_models_file = os.path.join(netlist_dir, 'spiceModels.scs')
        if os.path.exists(spice_models_file):
            sm_lines = [l for l in open(spice_models_file).read().splitlines() if 'analog/netlist' not in l and 'subckts.scs' not in l]
            sm_clean = '\n'.join(sm_lines) + '\ninclude "./subckts.scs" amsd_subckt_bind=yes\n'
        else:
            sm_clean = 'simulator lang=spectre\ninclude "./subckts.scs" amsd_subckt_bind=yes\n'
        with open(spice_models_file, 'w') as f:
            f.write(sm_clean)

        # 10. Update amsbind.scs, .amsbind.scs, and textInputs
        for abfile in ['amsbind.scs', '.amsbind.scs']:
            with open(os.path.join(netlist_dir, abfile), 'w') as f:
                f.write(amsbind_content)
        with open(os.path.join(netlist_dir, 'textInputs'), 'w') as f:
            f.write(text_inputs)

        # 11. Clean and configure xrunArgs
        xrun_args_file = os.path.join(netlist_dir, 'xrunArgs')
        args = open(xrun_args_file).read() if os.path.exists(xrun_args_file) else ''
        args = args.replace('${IC_INVOKE_DIR}/', f'/home/lary/project/BVU025/SCH/')
        if "python" in top_cell or "sv" in top_cell:
            args = args.replace('AN2x1', '').replace('vaSAR6b', '').replace('vaVDAC6b_FIXED', '')
        
        # 12. Link DPI-C py_bridge.c dynamically
        candidate_c = [
            os.path.join(pattern_dir, "py_bridge.c"),
            os.path.join(netlist_dir, "py_bridge.c")
        ]
        py_bridge_path = find_first_existing(candidate_c) or candidate_c[0]

        # 14. Configure PSF output database directory (clean stale traces from previous runs)
        psf_dir = os.path.join(pattern_dir, "psf") if pattern_dir and pattern_dir != netlist_dir else os.path.join(netlist_dir, "psf")
        if os.path.exists(psf_dir):
            for item in os.listdir(psf_dir):
                if item != ".simvision":
                    item_p = os.path.join(psf_dir, item)
                    if os.path.isfile(item_p) or os.path.islink(item_p):
                        try: os.remove(item_p)
                        except: pass
                    elif os.path.isdir(item_p):
                        shutil.rmtree(item_p, ignore_errors=True)
        os.makedirs(psf_dir, exist_ok=True)

        # --- Detect whether this is being called by ADE L or by run_cosim.py ---
        # ADE L generates its own -xmsimargs containing -l, -amspartinfo, -name, -top etc.
        # If we inject our own -xmsimargs into xrunArgs, ADE L gets 'unmatched quote' error.
        # Strategy: ONLY inject DPI-C compile flags (py_bridge.c + python headers).
        # For run_cosim.py: also inject psf dir, log path via xmsimargs.
        is_adel_run = os.environ.get('CDS_INST_DIR', '') != '' or os.environ.get('CDS_MAPI_RUN', '') != ''
        # More robust: check if xrunArgs already contains -amspartinfo (ADE L puts it there)
        # If ADE L manages it, -amspartinfo is already inside -xmsimargs so we must NOT add ours.
        existing_has_amspartinfo_outside_xmsimargs = any(
            l.strip().startswith('-amspartinfo') and 'xmsimargs' not in l
            for l in args.splitlines()
        )

        # Clean any old/broken DPI lines from xrunArgs
        clean_args_lines = []
        for l in args.splitlines():
            s = l.strip()
            if not s:
                continue
            # Always remove old DPI/Python compile flags (we will re-add them)
            if "py_bridge.c" in s or "-I/usr/include/python" in s or "-lpython" in s or "-L/usr/lib" in s:
                continue
            # Remove old xmsimargs ONLY if they are NOT ADE L's generated ones
            # ADE L's xmsimargs contain -name, -top etc.; ours only have +amsrawdir
            if s.startswith("-xmsimargs") and "-name" not in s and "-top" not in s:
                continue
            # Remove stale log/partinfo lines if they point to a DIFFERENT psf_dir
            # (don't remove if ADE L put them there in a xmsimargs block)
            if not s.startswith("-xmsimargs"):
                if s.startswith("-l ") and psf_dir not in s:
                    continue
                if s.startswith("-amspartinfo") and psf_dir not in s:
                    continue
            if ".amsbind.scs" in s:
                continue
            clean_args_lines.append(s)

        # Only add psf/log args when NOT run under ADE L (i.e. run_cosim.py / bvSim)
        # ADE L already puts these inside its own -xmsimargs block
        has_adel_xmsimargs = any("-name" in l and "-xmsimargs" in l for l in clean_args_lines)
        if not has_adel_xmsimargs and not existing_has_amspartinfo_outside_xmsimargs:
            clean_args_lines.append(f'-xmsimargs "+amsrawdir {psf_dir} -simcompatible_ams spectre"')
            clean_args_lines.append(f'-amspartinfo {psf_dir}/partition.info -rnm_partinfo')
            clean_args_lines.append(f'-l {psf_dir}/xrun.log')

        # Always add DPI-C Python compile flags (required for both ADE L and run_cosim.py)
        clean_args_lines.append(f"{py_bridge_path}")
        clean_args_lines.append("-I/usr/include/python3.10")
        clean_args_lines.append("-L/usr/lib/x86_64-linux-gnu")
        clean_args_lines.append("-lpython3.10")

        with open(xrun_args_file, 'w') as f:
            f.write("\n".join(clean_args_lines) + "\n")

        # --- Ensure py_tester.py (Python Master) is always up-to-date in netlist dir ---
        # Copy the canonical py_tester.py to ensure ADE L finds the correct version
        py_tester_src = find_first_existing([
            os.path.join(pattern_dir, "py_tester.py"),
            os.path.join(netlist_dir, "py_tester.py")
        ])
        if py_tester_src and os.path.dirname(py_tester_src) != netlist_dir:
            import shutil
            shutil.copy2(py_tester_src, os.path.join(netlist_dir, "py_tester.py"))

        # Also sync py_tester.sv and py_bridge.c to netlist dir to ensure ADE L compiles fresh ones!
        for sf in ["py_tester.sv", "py_bridge.c"]:
            src_f = find_first_existing([
                os.path.join(pattern_dir, sf),
                os.path.join(netlist_dir, sf)
            ])
            if src_f and os.path.dirname(src_f) != netlist_dir:
                shutil.copy2(src_f, os.path.join(netlist_dir, sf))

        # --- Delete stale __pycache__ (prevents old .pyc from masking updated py_tester.py) ---
        for pycache_root in [netlist_dir, pattern_dir]:
            pycache_dir = os.path.join(pycache_root, "__pycache__")
            if os.path.isdir(pycache_dir):
                for f_name in os.listdir(pycache_dir):
                    if "py_tester" in f_name:
                        try:
                            os.remove(os.path.join(pycache_dir, f_name))
                        except Exception:
                            pass

        # 13. Rewrite amsControlSpectre.scs to include AMSD bindings and save ALL voltage and current nodes
        ctrl_final = amsbind_content + f"""\n// Auto-generated amsControlSpectre.scs - Save All Voltages & Currents
simulator lang=spectre
global 0

simulatorOptions options temp=25 tnom=27 scale=1.0 scalem=1.0 reltol=1e-3 \\
vabstol=1e-6 iabstol=1e-12 gmin=1e-12 rforce=1 maxnotes=5 maxwarns=5 \\
digits=5 pivrel=1e-3 checklimitdest=psf

saveOptions options subcktprobelvl=5 currents=all save=allpub
save {top_cell}:all
save {top_cell}.Board:all
save {top_cell}.Board.TOP:all
save {top_cell}.Board.TOP.I_Bias:all

tran tran stop={t_stop_sim:.6e} errpreset=moderate writefinal="spectre.fc" annotate=status maxiters=5 

finalTimeOP info what=oppoint where=rawfile
modelParameter info what=models where=rawfile 
element info what=inst where=rawfile 
outputParameter info what=output where=rawfile 
wave_out options rawfmt=sst2
"""
        with open(os.path.join(netlist_dir, 'amsControlSpectre.scs'), 'w') as f:
            f.write(ctrl_final)

        # probe.tcl: probe all voltages and currents across all hierarchy depths
        probe_tcl = f"""
database -open ams_database -into "{psf_dir}" -default
probe -create -emptyok -database ams_database -all -depth all {{{top_cell}}}
probe -create -emptyok -database ams_database -flow -depth all {{{top_cell}}}
probe -create -emptyok -database ams_database -flow -ports -index -depth all {{{top_cell}}}
"""
        with open(os.path.join(netlist_dir, 'probe.tcl'), 'w') as f:
            f.write(probe_tcl)

        # spiceModels.scs: save all terminal currents and internal nodes
        save_stmts = f"""
save {top_cell}.Board:all
save {top_cell}.Board.TOP:all
save {top_cell}.Board.TOP.I_Bias:all
"""
        sm_content = open(spice_models_file).read()
        if f"{top_cell}.Board.TOP.I_Bias:all" not in sm_content:
            with open(spice_models_file, 'a') as f:
                f.write(save_stmts)

        # 16. Remove old stray hierarchy directories
        for stray in [os.path.join(pattern_dir, "BVU025_Lary"), os.path.join(pattern_dir, lib_name)]:
            if os.path.exists(stray):
                shutil.rmtree(stray, ignore_errors=True)

        print(f"[Auto-Assemble] Finished auto-assembling {lib_name}.{top_cell} successfully!")

    finally:
        os.chdir(cwd)

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    pat_dir = sys.argv[2] if len(sys.argv) > 2 else None
    universal_assemble(target, pattern_dir=pat_dir)
