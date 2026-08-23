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
        self.work_dir = os.path.abspath(work_dir or os.path.dirname(json_path) or os.getcwd())
        self.json_path = os.path.join(self.work_dir, os.path.basename(json_path))
        os.makedirs(self.work_dir, exist_ok=True)
        
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
        self.top_cell = os.path.basename(self.work_dir)
        if not self.top_cell or self.top_cell == ".":
            self.top_cell = "sim_TOP_cosim_python_A1"

    def run_simulation(self):
        """Execute AMS simulation on the virtual workstation."""
        print(f"===> [OneTest Sim] Loaded specification from: {os.path.basename(self.json_path)}")
        print(f"===> [OneTest Sim] Starting AMS Simulation for DUT: {self.lib_name}.{self.cell_name}...")
        
        # Check netlist location
        search_netlist = [
            os.path.join(self.work_dir, "ams", "config", "netlist"),
            os.path.join(self.work_dir, "netlist"),
            f"/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/ams/config/netlist",
            f"/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/netlist"
        ]
        netlist_dir = None
        for nd in search_netlist:
            if os.path.exists(nd):
                netlist_dir = nd
                break
        
        if not netlist_dir:
            print(f"\n[OneTest Sim] *** FATAL ERROR: netlist directory not found in known paths! ***")
            return False
            
        # 1. Automatically assemble and fix netlist/bindings
        try:
            import auto_assemble_global
            auto_assemble_global.universal_assemble(netlist_dir)
        except Exception as e:
            print(f"[OneTest Sim] Error in auto_assemble: {e}")
            
        # 2. Run xrun
        cmd = "xrun -f xrunArgs"
        print(f"[OneTest Sim] Executing simulation in: {netlist_dir}")
        res = subprocess.run(cmd, cwd=netlist_dir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print("[OneTest Sim] Simulation Execution Output:")
        lines = res.stdout.splitlines()
        for line in lines[-25:]:
            print("  ", line)
        
        if res.returncode != 0:
            print(f"\n[OneTest Sim] *** ERROR: Simulation exited with error code {res.returncode} ***")
            return False

        # Sync PSF results into local psf directory if needed
        possible_src_psf = [
            os.path.join(self.work_dir, "ams", "config", "psf"),
            os.path.join(netlist_dir, "..", "psf")
        ]
        dst_psf = os.path.join(self.work_dir, "psf")
        for src_psf in possible_src_psf:
            if os.path.exists(src_psf) and src_psf != dst_psf:
                print(f"[OneTest Sim] Synchronizing PSF results to: {dst_psf}")
                if os.path.exists(dst_psf):
                    shutil.rmtree(dst_psf, ignore_errors=True)
                shutil.copytree(src_psf, dst_psf)
                print(f"[OneTest Sim] PSF waveform database successfully stored in {dst_psf}")
                break

        self.evaluate_results()
        return True

    def open_viva(self):
        """Launch Viva waveform viewer directly pointing to local psf directory."""
        psf_dir = os.path.join(self.work_dir, "psf")
        print(f"[OneTest Sim] Launching Virtuoso Viva Waveform Viewer for {psf_dir}...")
        cmd = f"viva -mode xl -results {psf_dir} &"
        subprocess.Popen(cmd, shell=True, cwd=self.work_dir)
        print("[OneTest Sim] Viva viewer started.")

    def get_trim_code_from_simulation(self):
        """Extract optimal SAR trim code NvTrmIref<5:0> from simulation log / PSF."""
        search_logs = [
            os.path.join(self.work_dir, "psf", "xrun.log"),
            os.path.join(self.work_dir, "ams", "config", "netlist", "xrun.log"),
            os.path.join(self.work_dir, "xrun.log")
        ]
        for log_path in search_logs:
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    matches = re.findall(r'Optimal Trim Code\s*=\s*(\d+)', content)
                    if matches:
                        code_int = int(matches[-1])
                        return code_int
                except Exception:
                    pass
        return None

    def get_real_psf_value(self, sample_time="1.6m"):
        """Query EXACT real simulation measurement from PSF database using Ocean."""
        psf_path = os.path.join(self.work_dir, "psf")
        if not os.path.exists(psf_path):
            psf_path = os.path.join(self.work_dir, "ams", "config", "psf")
            
        ocn_script = f"""
openResults("{psf_path}")
selectResult('tran)

// Check all possible flow / terminal current signals
sig = getData("{self.top_cell}.Board.GPIO8_$flow")
if(!sig sig = getData("sim_TOP_cosim_python_A1.Board.GPIO8_$flow"))
if(!sig sig = getData("{self.top_cell}.Board.TOP.GPIO8_$flow"))
if(!sig sig = IT("/Board/GPIO8"))

if(sig then
    val = abs(value(sig {sample_time})) * 1e6
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

        # Load waveform definition if present
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
        res = img_settings.get("resolution", 100)
        bg = img_settings.get("backgroundColor", "white")

        ocn_code = f"""
openResults("{psf_dir}")
selectResult('tran)

b5 = getData("{self.top_cell}.NvTrmIref[5]")
b4 = getData("{self.top_cell}.NvTrmIref[4]")
b3 = getData("{self.top_cell}.NvTrmIref[3]")
b2 = getData("{self.top_cell}.NvTrmIref[2]")
b1 = getData("{self.top_cell}.NvTrmIref[1]")
b0 = getData("{self.top_cell}.NvTrmIref[0]")

bus_sig = awvCreateBus("NvTrmIref[5:0]" list(b5 b4 b3 b2 b1 b0) "hex")
if(!bus_sig bus_sig = bus(list(b5 b4 b3 b2 b1 b0)))

i_gpio = getData("{self.top_cell}.Board.GPIO8_$flow")
if(!i_gpio i_gpio = getData("sim_TOP_cosim_python_A1.Board.GPIO8_$flow"))
if(!i_gpio i_gpio = IT("/Board/GPIO8"))

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
            subprocess.run("xvfb-run -a ocean -replay /tmp/auto_wave_gen.ocn", shell=True, executable="/bin/bash", capture_output=True)
            if os.path.exists(img_file):
                print(f"[OneTest Sim] Waveform screenshot successfully generated: {img_file}")
                self.open_image(img_file)
                return img_file
        except Exception as e:
            print(f"[OneTest Sim] Waveform capture error: {e}")
        return None

    def open_image(self, img_path):
        """Open the generated waveform screenshot in default viewer without blocking."""
        if os.path.exists(img_path):
            print(f"[OneTest Sim] Launching Image Viewer for: {img_path}...")
            try:
                if sys.platform.startswith("linux"):
                    subprocess.Popen(f"nohup eog '{img_path}' >/dev/null 2>&1 &", shell=True)
                elif sys.platform.startswith("win"):
                    os.startfile(img_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", img_path])
            except Exception as e:
                print(f"[OneTest Sim] Could not launch image viewer: {e}")

    def evaluate_results(self):
        """Dynamically parse cosim.oneTest.json and generate test_report.json."""
        test_summary = self.config.get("description", f"OneTest Calibration & Trim Verification ({os.path.basename(self.work_dir)})")
        report = {
            "test_summary": test_summary,
            "tester_mode": "sim",
            "spec_file": os.path.basename(self.json_path),
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
                    item_name = act_val.get("name", f"Measurement at {step_id}")
                    capability = act_val.get("capability", "")
                    measure_cfg = act_val.get("measure", {})
                    metric = measure_cfg.get("metric", "")
                    limits = act_val.get("limits")

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
                        item_report["viva_command"] = f"viva -mode xl -results {os.path.join(self.work_dir, 'psf')}"
                        psf_exists = os.path.exists(os.path.join(self.work_dir, "psf")) or os.path.exists(os.path.join(self.work_dir, "ams", "config", "psf"))
                        item_report["status"] = "PASS" if psf_exists else "FAIL (NO_PSF_DATABASE)"

                    # Item 101 (Trim Code NvTrmIref<5:0>)
                    elif item_id == "101" or metric == "TRIM_CODE" or "NvTrmIref" in act_val.get("connection", ""):
                        item_report["result_file"] = "result/Result.json"
                        item_report["result_path"] = os.path.join(self.work_dir, "result", "Result.json")
                        code_int = self.get_trim_code_from_simulation()
                        if code_int is None:
                            item_report["measured"] = "N/A"
                            item_report["status"] = "FAIL (CODE_NOT_FOUND)"
                        else:
                            code_hex = f"0x{code_int:02X}"
                            item_report["measured"] = f"{code_hex} ({code_int})"
                            # Fail if 0x00 (0) or 0x3F (63)
                            if code_int == 0 or code_int == 63 or code_hex in ["0x00", "0x3F"]:
                                item_report["status"] = "FAIL"
                            else:
                                item_report["status"] = "PASS"

                    # Item 102 (Current measurement on GPIO8)
                    else:
                        unit = measure_cfg.get("unit", "uA")
                        item_report["unit"] = unit
                        val = self.get_real_psf_value(step_time or "1.6m")
                        item_report["measured"] = val
                        
                        if step_id == "measure_trimmed_iref" or item_id == "102":
                            item_report["result_file"] = "result/Result.json"
                            item_report["result_path"] = os.path.join(self.work_dir, "result", "Result.json")
                        
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

        report_file = os.path.join(result_dir, "test_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)

        # Save Result.json containing Item 101 and Item 102 measurement results
        result_data = {}
        for item_id, item_data in report["items"].items():
            if item_id in ["101", "102"] or item_data.get("step_id") in ["sar_calibration_search", "measure_trimmed_iref"]:
                result_data[item_id] = item_data
                
        result_file = os.path.join(result_dir, "Result.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=4)
            
        print(f"\n=======================================================")
        print(f"       OneTest Verification Summary (via cosim.oneTest.json)  ")
        print(f"=======================================================")
        print(json.dumps(report, indent=4))
        print(f"=======================================================")
        print(f"[OneTest Sim] Result.json generated successfully in {result_file}")
        return report

if __name__ == "__main__":
    runner = OneTestRunner()
    if len(sys.argv) > 1 and sys.argv[1] == "--viva":
        runner.open_viva()
    elif len(sys.argv) > 1 and sys.argv[1] == "--eval":
        runner.evaluate_results()
    else:
        runner.run_simulation()
