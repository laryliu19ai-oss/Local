#!/usr/bin/env python3
import os
import subprocess

netlist_dir = "/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/ams/config/netlist"
os.chdir(netlist_dir)

# 1. Update textInputs
text_inputs = """// HDL file for Lib - BVU025_Lary ,Cell - Buffer_DIG, View - functional
-amscompilefile "file:/home/lary/project/BVU025/SCH/BVU025_Lary/Buffer_DIG/functional/verilog.v lib:BVU025_Lary cell:Buffer_DIG view:functional"

// HDL file for Lib - BVU025_Lary ,Cell - py_tester, View - systemVerilog
-amscompilefile "file:/home/lary/project/BVU025/SCH/BVU025_Lary/py_tester/systemVerilog/verilog.sv lib:BVU025_Lary cell:py_tester view:systemVerilog"

-makelib umc18cdmos
-endlib
-makelib BVU025_Lary
-endlib
"""
with open("textInputs", "w") as f:
    f.write(text_inputs)

# 2. Update .amsbind.scs
amsbind = """// Binding AMSD Control Block for BVU025_Lary.sim_TOP_cosim_python_A1:config
amsd {
\tconfig designtop="BVU025_Lary.sim_TOP_cosim_python_A1:schematic"

\tconfig cell="Buffer_DIG" lib="BVU025_Lary" view="functional"
\tconfig cell="TOP_A1" lib="BVU025_Lary" view="schematic"
\tconfig cell="Bias_A1" lib="BVU025_Lary" view="analogtext"
}
"""
with open(".amsbind.scs", "w") as f:
    f.write(amsbind)

# 3. Clean xrunArgs
with open("xrunArgs", "r") as f:
    args = f.read()

# Add -sv and binding for py_tester
if "-sv" not in args:
    args = args.replace("-v93", "-v93 -sv")

for obsolete in ["AN2x1", "vaSAR6b", "vaVDAC6b_FIXED"]:
    args = args.replace(obsolete, "")

with open("xrunArgs", "w") as f:
    f.write(args)

print("[Fix] Ready to execute simulation.")

# 4. Run simulation
print("===> Executing ./runSimulation...")
res = subprocess.run(["./runSimulation"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
print(res.stdout[-3500:] if len(res.stdout) > 3500 else res.stdout)
