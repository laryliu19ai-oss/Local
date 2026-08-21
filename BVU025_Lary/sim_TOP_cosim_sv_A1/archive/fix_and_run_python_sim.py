#!/usr/bin/env python3
import os
import sys
import glob
import re
import subprocess

def fix_and_run():
    netlist_dir = "/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/ams/config/netlist"
    if not os.path.exists(netlist_dir):
        print(f"Directory {netlist_dir} not found.")
        return

    os.chdir(netlist_dir)
    print(f"Working in: {netlist_dir}")

    # 1. Update .amsbind.scs
    amsbind_content = """// Binding AMSD Control Block for BVU025_Lary.sim_TOP_cosim_python_A1:config
amsd {
\tconfig designtop="BVU025_Lary.sim_TOP_cosim_python_A1:schematic"

\tconfig cell="py_tester" lib="BVU025_Lary" view="systemVerilog"
\tconfig cell="Buffer_DIG" lib="BVU025_Lary" view="functional"
\tconfig cell="TOP_A1" lib="BVU025_Lary" view="schematic"
\tconfig cell="Bias_A1" lib="BVU025_Lary" view="analogtext"
}
"""
    with open(".amsbind.scs", "w") as f:
        f.write(amsbind_content)
    print("Updated .amsbind.scs successfully.")

    # 2. Fix textInputs (remove old vaSAR6b, vaVDAC6b_FIXED and replace IC_INVOKE_DIR)
    if os.path.exists("textInputs"):
        lines = open("textInputs").read().splitlines()
        clean_lines = []
        for l in lines:
            if "vaSAR6b" in l or "vaVDAC6b_FIXED" in l:
                continue
            l = l.replace("${IC_INVOKE_DIR}", "/home/lary/project/BVU025/SCH")
            l = l.replace("ftype:va ", "")
            clean_lines.append(l)
        with open("textInputs", "w") as f:
            f.write("\n".join(clean_lines) + "\n")
        print("Cleaned textInputs successfully.")

    # 3. Fix xrunArgs (ensure -amsbind and proper options)
    if os.path.exists("xrunArgs"):
        content = open("xrunArgs").read()
        content = content.replace("AN2x1", "")
        with open("xrunArgs", "w") as f:
            f.write(content)

    # 4. Run simulation
    print("===> Executing ./runSimulation...")
    res = subprocess.run(["./runSimulation"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print("=== Simulation Output ===")
    print(res.stdout[-2500:] if len(res.stdout) > 2500 else res.stdout)
    return res.returncode

if __name__ == "__main__":
    fix_and_run()
