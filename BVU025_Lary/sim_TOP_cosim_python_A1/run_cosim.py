#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OneTest Generic Python Orchestrator for AMS Co-Simulation
Author: Antigravity Agent
Architecture: 100% Data-Driven Orchestrator dynamically configured by OneTest JSON specification.
"""

from __future__ import annotations
import os
import sys
import json
import subprocess
import shutil
import glob
import re
from typing import Any, Dict, List, Optional, Tuple


class OneTestRunner:
    def __init__(self, json_path: Optional[str] = None, work_dir: Optional[str] = None):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.work_dir = os.path.abspath(work_dir or (os.path.dirname(json_path) if json_path and os.path.dirname(json_path) else script_dir))
        
        # 1. Resolve target JSON specification file
        if json_path:
            self.json_path = os.path.abspath(json_path)
            if not os.path.exists(self.json_path):
                self.json_path = os.path.join(self.work_dir, os.path.basename(json_path))
        else:
            candidates = [
                os.path.join(self.work_dir, "run_cosim.oneTest.json"),
                os.path.join(self.work_dir, "cosim.oneTest.json"),
                os.path.join(self.work_dir, "cosim.oneTest.sim.json")
            ]
            self.json_path = candidates[0]
            for c in candidates:
                if os.path.exists(c):
                    self.json_path = c
                    break

        os.makedirs(self.work_dir, exist_ok=True)
        try:
            os.chdir(self.work_dir)
        except Exception:
            pass
        
        if self.work_dir not in sys.path:
            sys.path.insert(0, self.work_dir)
        
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"OneTest specification file not found: {self.json_path}")
            
        with open(self.json_path, 'r', encoding='utf-8') as f:
            self.config: Dict[str, Any] = json.load(f)
            
        # 2. Parse all design, DUT, pins, testbenches, and setup dynamically
        self._parse_config()

    def _parse_config(self):
        """Dynamically extract all DUT metadata, pin definitions, testbenches, and setup steps."""
        self.one_test = self.config.get("oneTest", {})
        components = self.one_test.get("components", {})
        testboard_comps = self.one_test.get("testboard", {}).get("components", {})
        testbenches = self.config.get("testbenches", {})

        # 1. Detect Top Cell Name
        self.top_cell = "sim_TOP"
        if testbenches:
            # First enabled testbench or first key
            for tb_name, tb_val in testbenches.items():
                if isinstance(tb_val, dict) and tb_val.get("enable", True):
                    self.top_cell = tb_name
                    self.top_cell_cfg = tb_val
                    break
            else:
                self.top_cell = list(testbenches.keys())[0]
                self.top_cell_cfg = testbenches[self.top_cell]
        else:
            self.top_cell_cfg = {}

        # 2. Detect Primary DUT Component
        self.dut_id = None
        self.dut_info = {}
        # Priority: Check component referenced by "TOP" in testboard
        if "TOP" in testboard_comps and "id" in testboard_comps["TOP"]:
            self.dut_id = testboard_comps["TOP"]["id"]
            self.dut_info = components.get(self.dut_id, {})
        else:
            # Fallback: Find component with spice_type "sub-circuit" and package defined
            for comp_id, comp_val in components.items():
                if comp_val.get("spice_type") == "sub-circuit" and "pins" in comp_val:
                    self.dut_id = comp_id
                    self.dut_info = comp_val
                    break
            if not self.dut_id and components:
                self.dut_id = list(components.keys())[0]
                self.dut_info = components[self.dut_id]

        dut_design = self.dut_info.get("design", {})
        self.cell_name = dut_design.get("cell", self.dut_id or "DUT")
        self.lib_name = dut_design.get("library", "DUT_Lib")

        # 3. Detect Pins and Bus Configurations
        self.dut_pins: Dict[str, Dict[str, Any]] = self.dut_info.get("pins", {})
        self.trim_pin_name: Optional[str] = None
        self.trim_bits: int = 6  # default fallback
        self.comparator_pin_name: Optional[str] = None

        for pin_name, pin_meta in self.dut_pins.items():
            pos = pin_meta.get("position")
            p_type = str(pin_meta.get("type", "")).lower()
            p_func = str(pin_meta.get("function", "")).lower()

            # Identify Trim Code Bus Pin
            if isinstance(pos, list) and len(pos) > 1:
                self.trim_pin_name = pin_name
                self.trim_bits = len(pos)
            elif "trim" in pin_name.lower() or "trim" in p_func:
                if not self.trim_pin_name:
                    self.trim_pin_name = pin_name
                    if isinstance(pos, list):
                        self.trim_bits = len(pos)

            # Identify Comparator / Feedback Output Pin
            if "comparator" in p_func or "cmp" in pin_name.lower() or ("output" in p_type and ("tmo" in pin_name.lower() or "done" in pin_name.lower())):
                self.comparator_pin_name = pin_name

        # 4. Simulation paths and engine configuration
        sim_cfg = self.config.get("simulation", {})
        self.sim_engine = "ams" if "ams" in sim_cfg else ("spectre" if "spectre" in sim_cfg else "ams")
        self.sim_output_dir = sim_cfg.get(self.sim_engine, {}).get("output", {}).get("directory", "")

        # 5. Setup steps
        self.setup_steps: List[Dict[str, Any]] = self.one_test.get("setup", {}).get("steps", [])

    def _resolve_netlist_dir(self) -> Optional[str]:
        """Locate netlist directory dynamically across potential locations."""
        search_paths = [
            os.path.join(self.work_dir, "ams", "config", "netlist"),
            os.path.join(self.work_dir, "netlist"),
            os.path.join(self.sim_output_dir, self.top_cell, "ams", "config", "netlist") if self.sim_output_dir else "",
            os.path.join(self.sim_output_dir, self.top_cell, "netlist") if self.sim_output_dir else "",
            os.path.join(self.sim_output_dir, "ams", "config", "netlist") if self.sim_output_dir else "",
            os.path.join(self.sim_output_dir, "netlist") if self.sim_output_dir else ""
        ]
        for p in search_paths:
            if p and os.path.exists(p):
                return os.path.abspath(p)
        return None

    def _resolve_psf_dir(self) -> str:
        """Locate PSF results directory dynamically."""
        candidates = [
            os.path.join(self.work_dir, "psf"),
            os.path.join(self.work_dir, "ams", "config", "psf"),
            os.path.join(self.sim_output_dir, self.top_cell, "ams", "config", "netlist", "psf") if self.sim_output_dir else "",
            os.path.join(self.sim_output_dir, self.top_cell, "psf") if self.sim_output_dir else "",
            os.path.join(self.sim_output_dir, "psf") if self.sim_output_dir else ""
        ]
        for c in candidates:
            if c and os.path.exists(c) and (os.path.exists(os.path.join(c, "tran.tran")) or os.path.exists(os.path.join(c, "psf.trn")) or os.path.exists(os.path.join(c, "runObjFile"))):
                return os.path.abspath(c)
        # Fallback to standard work_dir/psf
        return os.path.join(self.work_dir, "psf")

    def run_simulation(self) -> bool:
        """Execute AMS simulation on the virtual workstation."""
        print(f"===> [OneTest Sim] Loaded specification: {os.path.basename(self.json_path)}")
        print(f"===> [OneTest Sim] Top Cell: {self.top_cell}, DUT: {self.lib_name}.{self.cell_name}")
        if self.trim_pin_name:
            print(f"===> [OneTest Sim] Detected Trim Bus: {self.trim_pin_name} ({self.trim_bits} bits)")

        netlist_dir = self._resolve_netlist_dir()
        if not netlist_dir:
            print(f"\n[OneTest Sim] *** FATAL ERROR: netlist directory not found in known search paths! ***")
            self.generate_fail_report("Netlist directory not found")
            return False

        # Clean old state and report files
        clean_targets = [
            os.path.join(self.work_dir, "result", "test_report.json"),
            os.path.join(self.work_dir, "result", ".py_tester_state.json"),
            os.path.join(self.work_dir, ".py_tester_state.json"),
            os.path.join(netlist_dir, "result", ".py_tester_state.json"),
            os.path.join(netlist_dir, ".py_tester_state.json"),
            "/tmp/.py_tester_state.json",
            "/tmp/onetest_trim_code.txt",
            "/tmp/onetest_meas_val.txt"
        ]
        if self.sim_output_dir:
            clean_targets.append(os.path.join(self.sim_output_dir, "result", ".py_tester_state.json"))

        for sf in clean_targets:
            if os.path.exists(sf):
                try:
                    os.remove(sf)
                except Exception:
                    pass

        # 1. Sync simulation orchestration files to netlist_dir
        try:
            for fname in ["py_tester.py", "py_bridge.c", "py_tester.sv", os.path.basename(self.json_path), "run_cosim.oneTest.json", "cosim.oneTest.json", "auto_assemble_global.py"]:
                src_f = os.path.join(self.work_dir, fname)
                if os.path.exists(src_f):
                    shutil.copy2(src_f, os.path.join(netlist_dir, fname))
                    try:
                        shutil.copy2(src_f, os.path.join(netlist_dir, "..", "..", "..", fname))
                    except Exception:
                        pass
        except Exception as e:
            print(f"[OneTest Sim] Warning copying sync files: {e}")

        # 2. Dynamically execute auto_assemble_global
        try:
            script_path = os.path.join(self.work_dir, "auto_assemble_global.py")
            if os.path.exists(script_path):
                import importlib.util
                spec = importlib.util.spec_from_file_location("auto_assemble_global_dynamic", script_path)
                aag_module = importlib.util.module_from_spec(spec)
                sys.modules["auto_assemble_global_dynamic"] = aag_module
                spec.loader.exec_module(aag_module)
                aag_module.universal_assemble(netlist_dir, pattern_dir=self.work_dir)
        except Exception as e:
            print(f"\n[OneTest Sim] *** Auto-Assemble Error: {e} ***")
            self.generate_fail_report(f"Auto-Assemble Error: {e}")
            return False

        # 3. Execute xrun
        cmd = "xrun -f xrunArgs"
        print(f"[OneTest Sim] Executing simulation in: {netlist_dir}")
        res = subprocess.run(cmd, cwd=netlist_dir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print("[OneTest Sim] Simulation Execution Output:")
        lines = res.stdout.splitlines()
        for line in lines[-25:]:
            print("  ", line)

        if res.returncode != 0:
            print(f"\n[OneTest Sim] *** ERROR: Simulation exited with code {res.returncode} ***")
            self.generate_fail_report(f"Simulation execution failed with code {res.returncode}")
            return False

        # 4. Sync PSF database to work_dir/psf
        tm14_psf = os.path.join(self.work_dir, "psf")
        netlist_psf = os.path.join(netlist_dir, "psf")
        if os.path.exists(netlist_psf):
            os.makedirs(tm14_psf, exist_ok=True)
            for item in os.listdir(netlist_psf):
                s_item = os.path.join(netlist_psf, item)
                d_item = os.path.join(tm14_psf, item)
                if os.path.isfile(s_item):
                    shutil.copy2(s_item, d_item)

        self.evaluate_results()
        return True

    def open_viva(self):
        """Launch Viva waveform viewer pointing directly to resolved PSF database."""
        psf_dir = self._resolve_psf_dir()
        print(f"[OneTest Sim] Launching Virtuoso Viva Waveform Viewer for {psf_dir}...")
        cmd = f"viva -mode xl -results {psf_dir} &"
        subprocess.Popen(cmd, shell=True, cwd=self.work_dir)
        print("[OneTest Sim] Viva viewer started.")

    def get_trim_code_from_simulation(self, trim_pin: Optional[str] = None, num_bits: Optional[int] = None, sample_time: str = "1.2m") -> Optional[int]:
        """Dynamically extract optimal SAR trim code from state file, PSF database or simulation log."""
        pin_name = trim_pin or self.trim_pin_name or "NvTrmIref"
        bits = num_bits or self.trim_bits or 6
        tc = self.top_cell

        # 1. Check Python Virtual Tester state files
        state_files = [
            "/tmp/.py_tester_state.json",
            os.path.join(self.work_dir, "result", ".py_tester_state.json"),
            os.path.join(self.work_dir, ".py_tester_state.json"),
            os.path.join(self.work_dir, "ams", "config", "netlist", "result", ".py_tester_state.json"),
            os.path.join(self.work_dir, "ams", "config", "netlist", ".py_tester_state.json")
        ]
        if self.sim_output_dir:
            state_files.extend([
                os.path.join(self.sim_output_dir, "result", ".py_tester_state.json"),
                os.path.join(self.sim_output_dir, self.top_cell, "ams", "config", "netlist", "result", ".py_tester_state.json"),
                os.path.join(self.sim_output_dir, self.top_cell, "ams", "config", "netlist", ".py_tester_state.json")
            ])

        for sf in state_files:
            if sf and os.path.exists(sf):
                try:
                    with open(sf, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for k in ["final_trim_code", "optimal_trim_code", "trim_code"]:
                            if k in data:
                                return int(data[k])
                except Exception:
                    pass

        # 2. Extract from PSF waveform database via Ocean dynamically
        psf_path = self._resolve_psf_dir()
        if os.path.exists(psf_path):
            max_bit = bits - 1
            # Dynamic bit-by-bit assembly
            bit_queries = []
            for i in range(bits):
                bit_queries.append(f"""
        sig = getData(sprintf(nil "{tc}.{pin_name}[%d]" {i}))
        if(!sig sig = getData(sprintf(nil "{pin_name}[%d]" {i})))
        if(!sig sig = getData(sprintf(nil "{tc}.{pin_name}<%d>" {i})))
        if(!sig sig = getData(sprintf(nil "/{pin_name}<%d>" {i})))
        if(sig then
            bv = value(sig {sample_time})
            is_hi = nil
            if(numberp(bv) && bv > 0.5 is_hi = t)
            if(stringp(bv) && (bv == "1" || bv == "1'b1" || bv == "1'h1" || bv == "t") is_hi = t)
            if(bv == t is_hi = t)
            if(is_hi code = code + (1 << {i}))
        )""")
            bit_extraction_block = "\n".join(bit_queries)

            ocn_script = f"""
openResults("{psf_path}")
selectResult('tran)

bus = getData("{tc}.{pin_name}[{max_bit}:0]")
if(!bus bus = getData("{pin_name}[{max_bit}:0]"))
if(!bus bus = getData("/{pin_name}[{max_bit}:0]"))
if(!bus bus = getData("/{pin_name}<{max_bit}:0>"))

if(bus then
    v = value(bus {sample_time})
    p = outfile("/tmp/onetest_trim_code.txt" "w")
    fprintf(p "%s" sprintf(nil "%s" v))
    close(p)
else
    code = 0
{bit_extraction_block}
    p = outfile("/tmp/onetest_trim_code.txt" "w")
    fprintf(p "%d" code)
    close(p)
)
exit()
"""
            with open("/tmp/onetest_trim.ocn", "w") as f:
                f.write(ocn_script)
            try:
                subprocess.run("export DISPLAY=:0; source ~/.bashrc; ocean -nograph -replay /tmp/onetest_trim.ocn", shell=True, executable="/bin/bash", capture_output=True)
                if os.path.exists("/tmp/onetest_trim_code.txt"):
                    val_str = open("/tmp/onetest_trim_code.txt").read().strip().replace('"', '').strip()
                    if val_str and "ERROR" not in val_str:
                        if val_str.startswith("0b") or val_str.startswith("0B"):
                            return int(val_str, 2)
                        elif val_str.startswith("0x") or val_str.startswith("0X"):
                            return int(val_str, 16)
                        elif set(val_str).issubset({'0', '1'}) and len(val_str) == bits:
                            return int(val_str, 2)
                        else:
                            try:
                                return int(val_str)
                            except ValueError:
                                try:
                                    return int(val_str, 16)
                                except ValueError:
                                    pass
            except Exception:
                pass

        # 3. Fallback to log search
        search_logs = [
            os.path.join(self.work_dir, "ams", "config", "netlist", "xrun.log"),
            os.path.join(self.work_dir, "psf", "xrun.log"),
            os.path.join(self.work_dir, "xrun.log"),
            "/tmp/xrun.log"
        ]
        for log_path in search_logs:
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    matches = re.findall(r'(?:Optimal Trim Code|SAR Converged|final_trim_code)\s*[:=]\s*(?:0x)?([0-9a-fA-F]+)', content)
                    if matches:
                        try:
                            return int(matches[-1], 16) if any(c in matches[-1].lower() for c in 'abcdef') else int(matches[-1])
                        except ValueError:
                            pass
                except Exception:
                    pass
        return None

    def get_psf_signal_value(self, connection_net: str, sample_time: str = "1.6m", capability: str = "current_measurement") -> Optional[float]:
        """Query EXACT real simulation measurement from PSF database dynamically for any net."""
        if os.path.exists("/tmp/onetest_meas_val.txt"):
            try:
                os.remove("/tmp/onetest_meas_val.txt")
            except Exception:
                pass

        psf_path = self._resolve_psf_dir()
        tc = self.top_cell
        clean_net = connection_net.lstrip("/")

        is_current = "current" in capability.lower()
        if is_current:
            signal_queries = f"""
sig = getData("{tc}.Board.{clean_net}_$flow")
if(!sig sig = getData("{tc}.Board.TOP.{clean_net}_$flow"))
if(!sig sig = getData("{tc}.{clean_net}_$flow"))
if(!sig sig = IT("/Board/{clean_net}"))
if(!sig sig = IT("/{clean_net}"))
if(!sig sig = i("/Board/{clean_net}"))
if(!sig sig = i("/{clean_net}"))
"""
        else:
            signal_queries = f"""
sig = getData("{tc}.Board.{clean_net}")
if(!sig sig = getData("{tc}.{clean_net}"))
if(!sig sig = v("/Board/{clean_net}"))
if(!sig sig = v("/{clean_net}"))
"""

        ocn_script = f"""
openResults("{psf_path}")
selectResult('tran)

{signal_queries}

if(sig then
    raw_val = abs(value(sig {sample_time}))
    if(raw_val < 1e-3 then
        val = raw_val * 1e6
    else
        val = raw_val
    )
    p = outfile("/tmp/onetest_meas_val.txt" "w")
    fprintf(p "%.4f" val)
    close(p)
else
    p = outfile("/tmp/onetest_meas_val.txt" "w")
    fprintf(p "ERROR_SIG_NOT_FOUND")
    close(p)
)
exit()
"""
        with open("/tmp/onetest_meas.ocn", "w") as f:
            f.write(ocn_script)
            
        try:
            subprocess.run("export DISPLAY=:0; source ~/.bashrc; ocean -nograph -replay /tmp/onetest_meas.ocn", shell=True, executable="/bin/bash", capture_output=True)
            if os.path.exists("/tmp/onetest_meas_val.txt"):
                val_str = open("/tmp/onetest_meas_val.txt").read().strip()
                if val_str and "ERROR" not in val_str:
                    return float(val_str)
        except Exception as e:
            print(f"[OneTest Sim] Ocean extraction error: {e}")
        return None

    def capture_waveform_from_json(self) -> Optional[str]:
        """Parse cosim.waveform.json dynamically and automatically generate waveform screenshot."""
        wave_json_path = os.path.join(self.work_dir, "cosim.waveform.json")
        if not os.path.exists(wave_json_path):
            wave_json_path = os.path.join(self.work_dir, "..", "cosim.waveform.json")

        psf_dir = self._resolve_psf_dir()
        img_dir = os.path.join(self.work_dir, "images")
        os.makedirs(img_dir, exist_ok=True)
        img_file = os.path.join(img_dir, "cosim_waveform.png")

        # Load waveform definition
        wave_cfg = {}
        if os.path.exists(wave_json_path):
            try:
                with open(wave_json_path, 'r', encoding='utf-8') as f:
                    wave_cfg = json.load(f).get("waveform", {})
            except Exception:
                pass

        img_settings = wave_cfg.get("imageSettings", {})
        width = img_settings.get("width", 1600)
        height = img_settings.get("height", 900)
        res   = img_settings.get("resolution", 100)
        bg    = img_settings.get("backgroundColor", "white")

        # Parse custom yAxis ranges and signals dynamically
        y_limit_stmts = []
        plot_stmts = []
        tc = self.top_cell
        pin_name = self.trim_pin_name or "NvTrmIref"
        bits = self.trim_bits or 6
        max_bit = bits - 1

        plot_list = wave_cfg.get("plot", [])
        for p in plot_list:
            for res_item in p.get("results", []):
                for sig_info in res_item.get("signals", []):
                    strip_num = sig_info.get("stripNumber", 1)
                    sig_name = sig_info.get("signal", "")
                    sig_type = sig_info.get("type", "")
                    display_lbl = sig_info.get("display", sig_name)
                    
                    y_axis = sig_info.get("yAxis", {})
                    y_min = y_axis.get("min")
                    y_max = y_axis.get("max")
                    y_step = y_axis.get("step")
                    if y_min is not None and y_max is not None:
                        y_limit_stmts.append(f"yLimit(list({y_min} {y_max}) ?stripNumber {strip_num})")
                        y_limit_stmts.append(f"awvSetYLimit(win 1 list({y_min} {y_max}) ?stripNumber {strip_num})")
                    if y_step is not None:
                        y_limit_stmts.append(f"awvSetYAxisUseStepValue(win 1 t ?stripNumber {strip_num})")
                        y_limit_stmts.append(f"awvSetYAxisStepValue(win 1 {y_step} ?stripNumber {strip_num})")
                        if y_min is not None and y_max is not None:
                            try:
                                num_div = int(round((float(y_max) - float(y_min)) / float(y_step)))
                                y_limit_stmts.append(f"awvSetYAxisMajorDivisions(win 1 {num_div} ?stripNumber {strip_num})")
                            except Exception:
                                pass

        y_limits_code = "\n".join(y_limit_stmts)

        # Dynamic Ocean plotting code
        ocn_code = f"""
load("/home/lary/skill/bvViva_modules.il")
openResults("{psf_dir}")
selectResult('tran)

// 1. Dynamic bus extraction
bus_sig = getData("{tc}.{pin_name}[{max_bit}:0]")
if(!bus_sig bus_sig = getData("{pin_name}[{max_bit}:0]"))
if(!bus_sig bus_sig = getData("/{pin_name}[{max_bit}:0]"))
if(!bus_sig bus_sig = getData("{tc}.Board.{pin_name}[{max_bit}:0]"))

// 2. Current flow extraction
i_sig = getData("{tc}.Board.GPIO8_$flow")
if(!i_sig i_sig = getData("{tc}.Board.TOP.GPIO8_$flow"))
if(!i_sig i_sig = IT("/Board/GPIO8"))
if(!i_sig i_sig = i("/Board/GPIO8"))

win = newWindow()
if(bus_sig plot(bus_sig ?expr "{pin_name}[{max_bit}:0]" ?strip 1))
if(i_sig plot(i_sig ?expr "I(GPIO8)" ?strip 2))

{y_limits_code}

saveGraphImage(?window win ?fileName "{img_file}" ?resolution {res} ?width {width} ?height {height} ?backgroundColor "{bg}" ?saveAllSubwindows t)
printf("SUCCESS_AUTO_WAVE\\n")
exit()
"""
        with open("/tmp/auto_wave_gen.ocn", "w") as f:
            f.write(ocn_code)

        try:
            subprocess.run(
                "export DISPLAY=:0; source ~/.bashrc; ocean -nograph -replay /tmp/auto_wave_gen.ocn",
                cwd="/tmp",
                shell=True, executable="/bin/bash", capture_output=True, text=True)
            
            # Clean stray Cadence directories
            for stray in [os.path.join(self.work_dir, self.lib_name)]:
                if os.path.exists(stray):
                    shutil.rmtree(stray, ignore_errors=True)

            if os.path.exists(img_file):
                print(f"[OneTest Sim] Waveform screenshot generated: {img_file}")
                return img_file
        except Exception as e:
            print(f"[OneTest Sim] Waveform capture error: {e}")
        return None

    def open_image(self, img_path: str):
        """Open generated image in OS default viewer without blocking."""
        if os.path.exists(img_path):
            print(f"[OneTest Sim] Launching Image Viewer for: {img_path}...")
            try:
                if sys.platform.startswith("linux"):
                    clean_env = {
                        "DISPLAY": ":0",
                        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
                        "XAUTHORITY": "/home/lary/.Xauthority",
                        "HOME": "/home/lary",
                        "PATH": "/usr/bin:/bin"
                    }
                    try:
                        subprocess.run(["killall", "-q", "eog"], env=clean_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
                    subprocess.Popen(["/usr/bin/eog", img_path], env=clean_env, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif sys.platform.startswith("win"):
                    os.startfile(img_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", img_path])
            except Exception as e:
                print(f"[OneTest Sim] Could not launch image viewer: {e}")

    def load_specifications(self) -> Dict[str, Any]:
        """Load test specifications and limits from Specification.json if present."""
        spec_paths = [
            os.path.join(self.work_dir, "Specification.json"),
            os.path.join(self.work_dir, "..", "Specification.json")
        ]
        for sp in spec_paths:
            if os.path.exists(sp):
                try:
                    with open(sp, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data.get("specifications", data)
                except Exception as e:
                    print(f"[OneTest Sim] Warning: failed to parse {sp}: {e}")
        return {}

    def evaluate_results(self) -> Dict[str, Any]:
        """Completely data-driven evaluation of all setup actions in the JSON specification."""
        test_summary = self.config.get("description", f"OneTest Verification ({self.top_cell})")
        specs_dict = self.load_specifications()
        report: Dict[str, Any] = {
            "test_summary": test_summary,
            "tester_mode": "sim",
            "spec_file": "Specification.json" if specs_dict else os.path.basename(self.json_path),
            "top_cell": self.top_cell,
            "dut": f"{self.lib_name}.{self.cell_name}",
            "items": {}
        }

        # Dynamically iterate over all measure actions defined across setup steps
        for step in self.setup_steps:
            step_id = step.get("id", "")
            step_time = step.get("time", {}).get("value", "")
            actions = step.get("actions", {})
            
            for act_key, act_val in actions.items():
                if not isinstance(act_val, dict):
                    continue
                if act_val.get("type") == "measure" or "test_item_id" in act_val:
                    item_id = str(act_val.get("test_item_id", act_key))
                    item_spec = specs_dict.get(item_id, {})
                    
                    item_name = item_spec.get("name", act_val.get("name", f"Measurement at {step_id}"))
                    capability = str(item_spec.get("category", act_val.get("capability", ""))).lower()
                    measure_cfg = act_val.get("measure", {})
                    metric = str(item_spec.get("metric", measure_cfg.get("metric", ""))).upper()
                    limits = item_spec.get("limits", act_val.get("limits"))
                    connection = act_val.get("connection", "")

                    item_report: Dict[str, Any] = {
                        "name": item_name,
                        "step_id": step_id,
                        "sample_time": step_time,
                        "connection": connection
                    }

                    # Category 1: Waveform Measurement
                    if capability == "waveform_measurement" or measure_cfg.get("kind") == "waveform":
                        img_path = self.capture_waveform_from_json()
                        item_report["psf_database"] = "psf/"
                        if img_path:
                            item_report["waveform_image"] = "images/cosim_waveform.png"
                            item_report["image_path"] = img_path
                        item_report["viva_command"] = f"viva -mode xl -results {self._resolve_psf_dir()}"
                        psf_exists = os.path.exists(self._resolve_psf_dir())
                        item_report["status"] = "PASS" if psf_exists else "FAIL (NO_PSF_DATABASE)"

                    # Category 2: Digital / SAR Trim Code Measurement
                    elif capability == "digital_measurement" or metric == "TRIM_CODE" or (self.trim_pin_name and self.trim_pin_name in connection):
                        item_report["result_file"] = "result/test_report.json"
                        item_report["result_path"] = os.path.join(self.work_dir, "result", "test_report.json")
                        if limits:
                            item_report["limits"] = limits
                            
                        bits = self.trim_bits or 6
                        code_int = self.get_trim_code_from_simulation(trim_pin=connection or self.trim_pin_name, num_bits=bits, sample_time=step_time or "1.2m")
                        
                        if code_int is None:
                            item_report["measured"] = "N/A"
                            item_report["status"] = "FAIL (CODE_NOT_FOUND)"
                        else:
                            code_hex = f"0x{code_int:02X}"
                            item_report["measured"] = f"{code_hex} ({code_int})"
                            # Dynamic boundary exclusion based on bit-width
                            max_val = (1 << bits) - 1
                            default_exclude = [f"0x00", f"0x{max_val:02X}"]
                            exclude = limits.get("exclude", default_exclude) if isinstance(limits, dict) else default_exclude
                            
                            if code_hex in exclude or f"0x{code_int:X}" in exclude or code_int in [0, max_val]:
                                item_report["status"] = "FAIL"
                            else:
                                item_report["status"] = "PASS"

                    # Category 3: Analog Scalar Measurements (Current / Voltage)
                    else:
                        unit = item_spec.get("unit", measure_cfg.get("unit", "uA" if "current" in capability else "V"))
                        item_report["unit"] = unit
                        val = self.get_psf_signal_value(connection_net=connection, sample_time=step_time or "1.6m", capability=capability)
                        item_report["measured"] = val
                        item_report["result_file"] = "result/test_report.json"
                        item_report["result_path"] = os.path.join(self.work_dir, "result", "test_report.json")
                        
                        if val is None:
                            item_report["status"] = "FAIL (NO_SIGNAL_DATA)"
                        elif limits and isinstance(limits, dict):
                            item_report["limits"] = limits
                            lower = limits.get("lower", float("-inf"))
                            upper = limits.get("upper", float("inf"))
                            item_report["status"] = "PASS" if (lower <= val <= upper) else "FAIL"
                        else:
                            item_report["status"] = "PASS"

                    report["items"][item_id] = item_report

        result_dir = os.path.join(self.work_dir, "result")
        os.makedirs(result_dir, exist_ok=True)
        report_file = os.path.join(result_dir, "test_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)
            
        print(f"\n=======================================================")
        print(f"       OneTest Dynamic Verification Summary            ")
        print(f"=======================================================")
        print(json.dumps(report, indent=4))
        print(f"=======================================================")
        print(f"[OneTest Sim] test_report.json generated in {report_file}")

        # Pop up image viewer
        img_file = os.path.join(self.work_dir, "images", "cosim_waveform.png")
        if os.path.exists(img_file):
            self.open_image(img_file)

        return report

    def generate_fail_report(self, reason: str = "Execution Failed") -> Dict[str, Any]:
        """Dynamically generate FAIL report for all declared items in JSON specification."""
        result_dir = os.path.join(self.work_dir, "result")
        os.makedirs(result_dir, exist_ok=True)
        report_file = os.path.join(result_dir, "test_report.json")
        
        fail_report: Dict[str, Any] = {
            "test_summary": f"OneTest Verification Failed ({self.top_cell})",
            "tester_mode": "sim",
            "spec_file": os.path.basename(self.json_path),
            "error_reason": reason,
            "items": {}
        }
        
        for step in self.setup_steps:
            for act_key, act_val in step.get("actions", {}).items():
                if isinstance(act_val, dict) and (act_val.get("type") == "measure" or "test_item_id" in act_val):
                    item_id = str(act_val.get("test_item_id", act_key))
                    item_name = act_val.get("name", f"Measurement at {step.get('id', '')}")
                    fail_report["items"][item_id] = {
                        "name": item_name,
                        "measured": "NO_DATA (FAIL)",
                        "status": "FAIL"
                    }
                    
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(fail_report, f, indent=4)
            
        print(f"\n=======================================================")
        print(f"       OneTest Verification Summary [FAIL ENFORCED]    ")
        print(f"=======================================================")
        print(json.dumps(fail_report, indent=4))
        print(f"=======================================================")
        return fail_report


if __name__ == "__main__":
    runner = OneTestRunner()
    if len(sys.argv) > 1 and sys.argv[1] == "--viva":
        runner.open_viva()
    elif len(sys.argv) > 1 and sys.argv[1] == "--eval":
        runner.evaluate_results()
    else:
        runner.run_simulation()