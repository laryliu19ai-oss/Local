#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OneTest Python Orchestrator for sim_TOP_cosim_python_A1
Author: Antigravity Agent
Purpose:
  1. Parse cosim.oneTest.json dynamically.
  2. Auto-assemble and clean AMS netlist bindings using auto_assemble_global.
  3. Execute AMS simulation (xrun -f xrunArgs).
  4. Keep PSF database in psf/.
  5. Item 101: Extract & evaluate NvTrmIref<5:0> (FAIL if 0x00 or 0x3F).
  6. Item 102: Extract & evaluate GPIO8 reference current against limits.
  7. Item 103: Auto-generate waveform screenshot & database from cosim.waveform.json.
"""

import os
import sys
import json
import subprocess
import shutil
import glob
import re

class OneTestRunner:
    def __init__(self, json_path="cosim.oneTest.json", work_dir=None):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.work_dir = os.path.abspath(work_dir or (os.path.dirname(json_path) if os.path.dirname(json_path) else script_dir))
        self.json_path = os.path.join(self.work_dir, os.path.basename(json_path))
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
            self.config = json.load(f)
            
        self.one_test = self.config.get("oneTest", {})
        self.dut_info = self.one_test.get("components", {}).get("TOP_A1", {})
        self.setup_steps = self.one_test.get("setup", {}).get("steps", [])
        self.cell_name = self.dut_info.get("design", {}).get("cell", "TOP_A1")
        self.lib_name = self.dut_info.get("design", {}).get("lib", "BVU025_Lary")
        self.top_cell = "sim_TOP_cosim_python_A1"

    def run_simulation(self):
        """Execute AMS simulation on the virtual workstation."""
        print(f"===> [OneTest Sim] Loaded specification from: {os.path.basename(self.json_path)}")
        print(f"===> [OneTest Sim] Starting AMS Simulation for DUT: {self.lib_name}.{self.cell_name}...")
        
        # Check netlist location
        search_netlist = [
            os.path.join(self.work_dir, "ams", "config", "netlist"),
            os.path.join(self.work_dir, "netlist"),
            f"/home/lary/simulation/BVU025/BVU025A/{self.top_cell}/ams/config/netlist",
            f"/home/lary/simulation/BVU025/BVU025A/{self.top_cell}/netlist"
        ]
        netlist_dir = None
        for nd in search_netlist:
            if os.path.exists(nd):
                netlist_dir = nd
                break
        
        if not netlist_dir:
            print(f"\n[OneTest Sim] *** FATAL ERROR: netlist directory not found in known paths! ***")
            return False

        # Clean old state and report files
        for sf in [
            os.path.join(self.work_dir, "result", "test_report.json"),
            os.path.join(self.work_dir, "result", ".py_tester_state.json"),
            os.path.join(self.work_dir, ".py_tester_state.json"),
            os.path.join(netlist_dir, "result", ".py_tester_state.json"),
            os.path.join(netlist_dir, ".py_tester_state.json"),
            "/home/lary/simulation/BVU025/BVU025A/result/.py_tester_state.json",
            "/home/lary/simulation/BVU025/BVU025A/ocean/result/.py_tester_state.json",
            "/tmp/.py_tester_state.json",
            "/tmp/onetest_trim_code.txt",
            "/tmp/onetest_meas_val.txt"
        ]:
            if os.path.exists(sf):
                try: os.remove(sf)
                except Exception: pass
            
        # 1. Ensure latest py_tester.py, py_bridge.c, py_tester.sv, cosim.oneTest.json, and auto_assemble_global.py are in netlist_dir
        try:
            for fname in ["py_tester.py", "py_bridge.c", "py_tester.sv", "cosim.oneTest.json", "auto_assemble_global.py"]:
                src_f = os.path.join(self.work_dir, fname)
                if os.path.exists(src_f):
                    shutil.copy2(src_f, os.path.join(netlist_dir, fname))
                    shutil.copy2(src_f, os.path.join(netlist_dir, "..", "..", "..", fname))
        except Exception as e:
            print(f"[OneTest Sim] Warning copying sync files: {e}")

        # 2. Dynamically import auto_assemble_global strictly from self.work_dir (TM14)
        try:
            import importlib.util
            script_path = os.path.join(self.work_dir, "auto_assemble_global.py")
            spec = importlib.util.spec_from_file_location("auto_assemble_global_tm14", script_path)
            aag_module = importlib.util.module_from_spec(spec)
            sys.modules["auto_assemble_global_tm14"] = aag_module
            spec.loader.exec_module(aag_module)
            aag_module.universal_assemble(netlist_dir, pattern_dir=self.work_dir)
        except Exception as e:
            print(f"\n[OneTest Sim] *** FOOLPROOF ERROR in auto_assemble: {e} ***")
            self.generate_fail_report(f"Auto-Assemble Error: {e}")
            return False
            
        # 3. Run xrun with clean compilation
        cmd = "xrun -f xrunArgs"
        print(f"[OneTest Sim] Executing simulation in: {netlist_dir}")
        res = subprocess.run(cmd, cwd=netlist_dir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print("[OneTest Sim] Simulation Execution Output:")
        lines = res.stdout.splitlines()
        for line in lines[-25:]:
            print("  ", line)
        
        if res.returncode != 0:
            print(f"\n[OneTest Sim] *** ERROR: Simulation exited with error code {res.returncode} ***")
            self.generate_fail_report(f"Simulation execution failed with code {res.returncode}")
            return False

        # Sync PSF database from netlist directory to TM14/psf if needed
        tm14_psf = os.path.join(self.work_dir, "psf")
        netlist_psf = os.path.join(netlist_dir, "psf")
        if os.path.exists(netlist_psf):
            os.makedirs(tm14_psf, exist_ok=True)
            for item in os.listdir(netlist_psf):
                s_item = os.path.join(netlist_psf, item)
                d_item = os.path.join(tm14_psf, item)
                if os.path.isfile(s_item):
                    shutil.copy2(s_item, d_item)

        if os.path.exists(tm14_psf):
            print(f"[OneTest Sim] PSF database available at: {tm14_psf}")
        else:
            print(f"[OneTest Sim] Warning: PSF not found at {tm14_psf}")

        self.evaluate_results()
        return True

    def open_viva(self):
        """Launch Viva waveform viewer pointing directly to TM14/psf."""
        psf_dir = "/home/lary/project/BVU025/SCH/cosim/pattern/TM14/psf"
        print(f"[OneTest Sim] Launching Virtuoso Viva Waveform Viewer for {psf_dir}...")
        cmd = f"viva -mode xl -results {psf_dir} &"
        subprocess.Popen(cmd, shell=True, cwd=self.work_dir)
        print("[OneTest Sim] Viva viewer started.")

    def get_trim_code_from_simulation(self):
        """Extract optimal SAR trim code NvTrmIref<5:0> from Python state, PSF database or simulation log."""
        # 1. Check Python Virtual Tester state file
        state_files = [
            "/tmp/.py_tester_state.json",
            os.path.join(self.work_dir, "result", ".py_tester_state.json"),
            os.path.join(self.work_dir, ".py_tester_state.json"),
            "/home/lary/simulation/BVU025/BVU025A/result/.py_tester_state.json",
            f"/home/lary/simulation/BVU025/BVU025A/{self.top_cell}/ams/config/netlist/result/.py_tester_state.json",
            f"/home/lary/simulation/BVU025/BVU025A/{self.top_cell}/ams/config/netlist/.py_tester_state.json",
            os.path.join(self.work_dir, "ams", "config", "netlist", "result", ".py_tester_state.json"),
            os.path.join(self.work_dir, "ams", "config", "netlist", ".py_tester_state.json")
        ]
        for sf in state_files:
            if os.path.exists(sf):
                try:
                    with open(sf, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if "optimal_trim_code" in data:
                            return int(data["optimal_trim_code"])
                except Exception:
                    pass

        # 2. Extract from PSF waveform database via Ocean
        psf_path = os.path.join(self.work_dir, "psf")
        if not os.path.exists(psf_path):
            psf_path = os.path.join(self.work_dir, "ams", "config", "psf")

        if os.path.exists(psf_path):
            ocn_script = f"""
openResults("{psf_path}")
selectResult('tran)

bus = getData("{self.top_cell}.NvTrmIref[5:0]")
if(!bus bus = getData("sim_TOP_cosim_python_A1.NvTrmIref[5:0]"))
if(!bus bus = getData("NvTrmIref[5:0]"))
if(!bus bus = getData("/NvTrmIref[5:0]"))

if(bus then
    v = value(bus 1.2m)
    p = outfile("/tmp/onetest_trim_code.txt" "w")
    fprintf(p "%s" sprintf(nil "%s" v))
    close(p)
else
    code = 0
    for(i 0 5
        sig = getData(sprintf(nil "{self.top_cell}.NvTrmIref[%d]" i))
        if(!sig sig = getData(sprintf(nil "sim_TOP_cosim_python_A1.NvTrmIref[%d]" i)))
        if(!sig sig = getData(sprintf(nil "{self.top_cell}.NvTrmIref<%d>" i)))
        if(!sig sig = getData(sprintf(nil "sim_TOP_cosim_python_A1.NvTrmIref<%d>" i)))
        if(sig then
            bv = value(sig 1.2m)
            is_hi = nil
            if(numberp(bv) && bv > 0.5 is_hi = t)
            if(stringp(bv) && (bv == "1" || bv == "1'b1" || bv == "1'h1" || bv == "t") is_hi = t)
            if(bv == t is_hi = t)
            if(is_hi code = code + (1 << i))
        )
    )
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
                        # 1. Binary string (e.g. 0b011111 or 0B...)
                        if val_str.startswith("0b") or val_str.startswith("0B"):
                            return int(val_str, 2)
                        # 2. Hex string (e.g. 0x1F or 0X...)
                        elif val_str.startswith("0x") or val_str.startswith("0X"):
                            return int(val_str, 16)
                        # 3. Pure binary bits without prefix (e.g. "011111")
                        elif set(val_str).issubset({'0', '1'}) and len(val_str) == 6:
                            return int(val_str, 2)
                        # 4. Fallback int / hex
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
                    matches = re.findall(r'Optimal Trim Code\s*=\s*(\d+)', content)
                    if matches:
                        return int(matches[-1])
                except Exception:
                    pass
        return None

    def get_real_psf_value(self, sample_time="1.6m"):
        """Query EXACT real simulation measurement from PSF database using Ocean."""
        if os.path.exists("/tmp/onetest_meas_val.txt"):
            try:
                os.remove("/tmp/onetest_meas_val.txt")
            except Exception:
                pass

        psf_candidates = [
            os.path.join(self.work_dir, "psf"),
            f"/home/lary/simulation/BVU025/BVU025A/{self.top_cell}/ams/config/netlist/psf",
            os.path.join(self.work_dir, "ams", "config", "psf")
        ]
        psf_path = None
        for p in psf_candidates:
            if os.path.exists(p) and (os.path.exists(os.path.join(p, "tran.tran")) or os.path.exists(os.path.join(p, "psf.trn"))):
                psf_path = p
                break
        if not psf_path:
            psf_path = psf_candidates[0]
            
        ocn_script = f"""
openResults("{psf_path}")
selectResult('tran)

// Check all possible flow / terminal current signals
sig = getData("{self.top_cell}.Board.GPIO8_$flow")
if(!sig sig = getData("sim_TOP_cosim_python_A1.Board.GPIO8_$flow"))
if(!sig sig = getData("{self.top_cell}.Board.TOP.GPIO8_$flow"))
if(!sig sig = IT("/Board/GPIO8"))

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

    def diagnose_psf_signals(self):
        """Dump all signal names from the PSF database to /tmp/psf_signals.txt for debugging."""
        psf_dir = os.path.join(self.work_dir, "psf")
        if not os.path.exists(psf_dir):
            psf_dir = os.path.join(self.work_dir, "ams", "config", "psf")
        ocn_diag = f"""
openResults("{psf_dir}")
selectResult('tran)
all_sigs = listSignals()
p = outfile("/tmp/psf_signals.txt" "w")
foreach(s all_sigs fprintf(p "%s\\n" s))
close(p)
printf("DIAG_DONE: %d signals written to /tmp/psf_signals.txt\\n" length(all_sigs))
exit()
"""
        with open("/tmp/psf_diag.ocn", "w") as f:
            f.write(ocn_diag)
        result = subprocess.run(
            "export DISPLAY=:0; source ~/.bashrc; ocean -nograph -replay /tmp/psf_diag.ocn",
            shell=True, executable="/bin/bash", capture_output=True, text=True)
        if os.path.exists("/tmp/psf_signals.txt"):
            signals = open("/tmp/psf_signals.txt").read().strip().splitlines()
            nv_sigs = [s for s in signals if "NvTrmIref" in s or "nvtrmIref" in s.lower()]
            print(f"[DiagPSF] Total signals in PSF: {len(signals)}")
            print(f"[DiagPSF] NvTrmIref-related signals found: {nv_sigs if nv_sigs else '*** NONE - not saved to PSF! ***'}")
            print(f"[DiagPSF] Full list: /tmp/psf_signals.txt")
            return nv_sigs
        else:
            print(f"[DiagPSF] Ocean diagnostic failed. stderr: {result.stderr[:300]}")
            return []

    def capture_waveform_from_json(self):
        """Parse cosim.waveform.json and automatically generate/capture waveform image."""
        wave_json_path = os.path.join(self.work_dir, "cosim.waveform.json")
        if not os.path.exists(wave_json_path):
            wave_json_path = os.path.join(self.work_dir, "..", "cosim.waveform.json")

        psf_dir = os.path.join(self.work_dir, "psf")
        if not os.path.exists(psf_dir):
            psf_dir = os.path.join(self.work_dir, "ams", "config", "psf")

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

        tc = self.top_cell  # e.g. "sim_TOP_cosim_python_A1_ocean"

        ocn_code = f"""
load("/home/lary/skill/bvViva_modules.il")
openResults("{psf_dir}")
selectResult('tran)

// 1. Try to get NvTrmIref[5:0] Bus directly from PSF
bus_sig = getData("{tc}.NvTrmIref[5:0]")
if(!bus_sig bus_sig = getData("sim_TOP_cosim_python_A1.NvTrmIref[5:0]"))
if(!bus_sig bus_sig = getData("NvTrmIref[5:0]"))
if(!bus_sig bus_sig = getData("/NvTrmIref[5:0]"))
if(!bus_sig bus_sig = getData("{tc}.Board.NvTrmIref[5:0]"))
if(!bus_sig bus_sig = getData("sim_TOP_cosim_python_A1.Board.NvTrmIref[5:0]"))

// 2. Fallback: try assembling from individual bits
if(!bus_sig then
    b5 = getData("{tc}.NvTrmIref[5]") if(!b5 b5=getData("sim_TOP_cosim_python_A1.NvTrmIref[5]")) if(!b5 b5=getData("{tc}.NvTrmIref<5>")) if(!b5 b5=getData("sim_TOP_cosim_python_A1.NvTrmIref<5>")) if(!b5 b5=v("/NvTrmIref<5>"))
    b4 = getData("{tc}.NvTrmIref[4]") if(!b4 b4=getData("sim_TOP_cosim_python_A1.NvTrmIref[4]")) if(!b4 b4=getData("{tc}.NvTrmIref<4>")) if(!b4 b4=getData("sim_TOP_cosim_python_A1.NvTrmIref<4>")) if(!b4 b4=v("/NvTrmIref<4>"))
    b3 = getData("{tc}.NvTrmIref[3]") if(!b3 b3=getData("sim_TOP_cosim_python_A1.NvTrmIref[3]")) if(!b3 b3=getData("{tc}.NvTrmIref<3>")) if(!b3 b3=getData("sim_TOP_cosim_python_A1.NvTrmIref<3>")) if(!b3 b3=v("/NvTrmIref<3>"))
    b2 = getData("{tc}.NvTrmIref[2]") if(!b2 b2=getData("sim_TOP_cosim_python_A1.NvTrmIref[2]")) if(!b2 b2=getData("{tc}.NvTrmIref<2>")) if(!b2 b2=getData("sim_TOP_cosim_python_A1.NvTrmIref<2>")) if(!b2 b2=v("/NvTrmIref<2>"))
    b1 = getData("{tc}.NvTrmIref[1]") if(!b1 b1=getData("sim_TOP_cosim_python_A1.NvTrmIref[1]")) if(!b1 b1=getData("{tc}.NvTrmIref<1>")) if(!b1 b1=getData("sim_TOP_cosim_python_A1.NvTrmIref<1>")) if(!b1 b1=v("/NvTrmIref<1>"))
    b0 = getData("{tc}.NvTrmIref[0]") if(!b0 b0=getData("sim_TOP_cosim_python_A1.NvTrmIref[0]")) if(!b0 b0=getData("{tc}.NvTrmIref<0>")) if(!b0 b0=getData("sim_TOP_cosim_python_A1.NvTrmIref<0>")) if(!b0 b0=v("/NvTrmIref<0>"))

    if(b5 && b4 && b3 && b2 && b1 && b0 then
        bus_sig = awvCreateBus("NvTrmIref[5:0]" list(b5 b4 b3 b2 b1 b0) "Hexadecimal")
        if(!bus_sig bus_sig = awvCreateBus("NvTrmIref[5:0]" list(b5 b4 b3 b2 b1 b0) "hex"))
    )
)

// 3. GPIO8 current
i_gpio = getData("{tc}.Board.GPIO8_$flow")
if(!i_gpio i_gpio=getData("sim_TOP_cosim_python_A1.Board.GPIO8_$flow"))
if(!i_gpio i_gpio=getData("{tc}.Board.TOP.GPIO8_$flow"))
if(!i_gpio i_gpio=IT("/Board/GPIO8"))
if(!i_gpio i_gpio=i("/Board/GPIO8"))

if(i_gpio then
    raw_val = abs(value(i_gpio 1.6m))
    val = if(raw_val < 1e-3 raw_val * 1e6 raw_val)
    p = outfile("/tmp/onetest_meas_val.txt" "w")
    fprintf(p "%.4f" val)
    close(p)
)

win = newWindow()
if(bus_sig plot(bus_sig ?expr "NvTrmIref[5:0]" ?strip 1))
if(i_gpio plot(i_gpio ?expr "I(GPIO8)" ?strip 2))

saveGraphImage(?window win ?fileName "{img_file}" ?resolution {res} ?width {width} ?height {height} ?backgroundColor "{bg}" ?saveAllSubwindows t)
printf("SUCCESS_AUTO_WAVE\\n")
exit()
"""
        with open("/tmp/auto_wave_gen.ocn", "w") as f:
            f.write(ocn_code)

        try:
            result = subprocess.run(
                "export DISPLAY=:0; source ~/.bashrc; ocean -nograph -replay /tmp/auto_wave_gen.ocn",
                cwd="/tmp",
                shell=True, executable="/bin/bash", capture_output=True, text=True)
            
            # Clean any stray Cadence library directories created in work_dir
            for stray in [os.path.join(self.work_dir, self.lib_name), os.path.join(self.work_dir, "BVU025_Lary")]:
                if os.path.exists(stray):
                    shutil.rmtree(stray, ignore_errors=True)

            if os.path.exists(img_file):
                print(f"[OneTest Sim] Waveform screenshot successfully generated: {img_file}")
                return img_file
            else:
                print(f"[OneTest Sim] WARNING: image not generated. Run diagnose_psf_signals() to check PSF contents.")
                self.diagnose_psf_signals()
        except Exception as e:
            print(f"[OneTest Sim] Waveform capture error: {e}")
        return None

    def open_image(self, img_path):
        """Open the generated waveform screenshot in default viewer without blocking."""
        if os.path.exists(img_path):
            print(f"[OneTest Sim] Launching Image Viewer for: {img_path}...")
            try:
                if sys.platform.startswith("linux"):
                    disp = os.environ.get("DISPLAY", ":0")
                    cmd = f"DISPLAY={disp} nohup eog '{img_path}' >/dev/null 2>&1 &"
                    subprocess.Popen(cmd, shell=True)
                elif sys.platform.startswith("win"):
                    os.startfile(img_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", img_path])
            except Exception as e:
                print(f"[OneTest Sim] Could not launch image viewer: {e}")

    def load_specifications(self):
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
                        specs = data.get("specifications", data)
                        print(f"[OneTest Sim] Loaded specifications from: {os.path.basename(sp)}")
                        return specs
                except Exception as e:
                    print(f"[OneTest Sim] Warning: failed to parse {sp}: {e}")
        return {}

    def evaluate_results(self):
        """Dynamically parse cosim.oneTest.json and evaluate against Specification.json."""
        if os.path.exists("/tmp/onetest_meas_val.txt"):
            try:
                os.remove("/tmp/onetest_meas_val.txt")
            except Exception:
                pass

        test_summary = self.config.get("description", f"OneTest Calibration & Trim Verification ({os.path.basename(self.work_dir)})")
        specs_dict = self.load_specifications()
        report = {
            "test_summary": test_summary,
            "tester_mode": "sim",
            "spec_file": "Specification.json" if specs_dict else os.path.basename(self.json_path),
            "items": {}
        }

        # Dynamically extract measurement actions from cosim.oneTest.json setup steps
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
                    capability = item_spec.get("category", act_val.get("capability", ""))
                    measure_cfg = act_val.get("measure", {})
                    metric = item_spec.get("metric", measure_cfg.get("metric", ""))
                    limits = item_spec.get("limits", act_val.get("limits"))

                    item_report = {
                        "name": item_name,
                        "step_id": step_id,
                        "sample_time": step_time
                    }

                    # Item 103 (Waveform)
                    if capability == "waveform_measurement" or measure_cfg.get("kind") == "waveform" or item_id == "103":
                        img_path = self.capture_waveform_from_json()
                        item_report["psf_database"] = "psf/"
                        if img_path:
                            item_report["waveform_image"] = "images/cosim_waveform.png"
                            item_report["image_path"] = img_path
                            self.open_image(img_path)
                        item_report["viva_command"] = f"viva -mode xl -results {os.path.join(self.work_dir, 'psf')}"
                        psf_exists = os.path.exists(os.path.join(self.work_dir, "psf")) or os.path.exists(os.path.join(self.work_dir, "ams", "config", "psf"))
                        item_report["status"] = "PASS" if psf_exists else "FAIL (NO_PSF_DATABASE)"

                    # Item 101 (Trim Code NvTrmIref<5:0>)
                    elif item_id == "101" or metric == "TRIM_CODE" or "NvTrmIref" in act_val.get("connection", ""):
                        item_report["result_file"] = "result/test_report.json"
                        item_report["result_path"] = os.path.join(self.work_dir, "result", "test_report.json")
                        if limits:
                            item_report["limits"] = limits
                        code_int = self.get_trim_code_from_simulation()
                        if code_int is None:
                            item_report["measured"] = "N/A"
                            item_report["status"] = "FAIL (CODE_NOT_FOUND)"
                        else:
                            code_hex = f"0x{code_int:02X}"
                            item_report["measured"] = f"{code_hex} ({code_int})"
                            exclude = limits.get("exclude", ["0x00", "0x3F"]) if isinstance(limits, dict) else ["0x00", "0x3F"]
                            # Fail if in exclude list or 0/63
                            if code_hex in exclude or f"0x{code_int:X}" in exclude or code_int in [0, 63]:
                                item_report["status"] = "FAIL"
                            else:
                                item_report["status"] = "PASS"

                    # Item 102 (Current measurement on GPIO8)
                    else:
                        unit = item_spec.get("unit", measure_cfg.get("unit", "uA"))
                        item_report["unit"] = unit
                        val = self.get_real_psf_value(step_time or "1.6m")
                        item_report["measured"] = val
                        
                        if step_id == "measure_trimmed_iref" or item_id == "102":
                            item_report["result_file"] = "result/test_report.json"
                            item_report["result_path"] = os.path.join(self.work_dir, "result", "test_report.json")
                        
                        if val is None:
                            item_report["status"] = "FAIL (NO_SIGNAL_DATA)"
                        elif limits:
                            item_report["limits"] = limits
                            lower = limits.get("lower", float("-inf"))
                            upper = limits.get("upper", float("inf"))
                            item_report["status"] = "PASS" if (lower <= val <= upper) else "FAIL"
                        else:
                            item_report["status"] = "PASS"

                    report["items"][item_id] = item_report

        result_dir = os.path.join(self.work_dir, "result")
        os.makedirs(result_dir, exist_ok=True)

        # Remove redundant Result.json if present
        old_result_file = os.path.join(result_dir, "Result.json")
        if os.path.exists(old_result_file):
            try:
                os.remove(old_result_file)
            except Exception:
                pass

        report_file = os.path.join(result_dir, "test_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)
            
        print(f"\n=======================================================")
        print(f"       OneTest Verification Summary (via cosim.oneTest.json)  ")
        print(f"=======================================================")
        print(json.dumps(report, indent=4))
        print(f"=======================================================")
        print(f"[OneTest Sim] test_report.json generated successfully in {report_file}")
        return report

    def generate_fail_report(self, reason="Execution Failed"):
        """Foolproof FAIL report generation when simulation, config, or measurement cannot proceed."""
        result_dir = os.path.join(self.work_dir, "result")
        os.makedirs(result_dir, exist_ok=True)
        report_file = os.path.join(result_dir, "test_report.json")
        
        fail_report = {
            "test_summary": f"OneTest Calibration & Trim Verification ({os.path.basename(self.work_dir)})",
            "tester_mode": "sim",
            "spec_file": os.path.basename(self.json_path),
            "error_reason": reason,
            "items": {
                "101": {
                    "name": "Verify SAR Optimal Trim Code on NvTrmIref<5:0>",
                    "measured": "NO_DATA (FAIL)",
                    "status": "FAIL"
                },
                "102": {
                    "name": "Measure trimmed reference current on GPIO8",
                    "measured": "NO_DATA (FAIL)",
                    "status": "FAIL"
                },
                "103": {
                    "name": "Capture transient simulation waveform",
                    "status": "FAIL"
                }
            }
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