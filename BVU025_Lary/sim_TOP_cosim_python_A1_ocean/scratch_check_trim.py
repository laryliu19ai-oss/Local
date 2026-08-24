import os
import sys

sys.path.insert(0, "/home/lary/simulation/BVU025/BVU025A/ocean/BVU025_Lary/sim_TOP_cosim_python_A1_ocean")
os.chdir("/home/lary/simulation/BVU025/BVU025A/ocean/BVU025_Lary/sim_TOP_cosim_python_A1_ocean")

import run_cosim

r = run_cosim.OneTestRunner()
print("work_dir:", r.work_dir)
print("top_cell:", r.top_cell)
code = r.get_trim_code_from_simulation()
print("TRIM CODE RETURNED:", code)
