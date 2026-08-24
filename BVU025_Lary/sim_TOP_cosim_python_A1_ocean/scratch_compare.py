import subprocess

ocn = """
p = outfile("/tmp/compare_result.txt" "w")

openResults("/home/lary/simulation/BVU025/BVU025A/ocean/BVU025_Lary/sim_TOP_cosim_python_A1_ocean/psf")
selectResult('tran)
sig_ocean = getData("sim_TOP_cosim_python_A1.Board.GPIO8_$flow")
val_ocean = value(sig_ocean 1.0e-3)
fprintf(p "OCEAN_DIR (sim_TOP_cosim_python_A1_ocean/psf) GPIO8 CURRENT @ 1.0ms: %f uA\\n" abs(val_ocean)*1e6)

if(isDir("/home/lary/simulation/BVU025/BVU025A/ocean/BVU025_Lary/sim_TOP_cosim_python_A1/psf") then
    openResults("/home/lary/simulation/BVU025/BVU025A/ocean/BVU025_Lary/sim_TOP_cosim_python_A1/psf")
    selectResult('tran)
    sig_old = getData("sim_TOP_cosim_python_A1.Board.GPIO8_$flow")
    val_old = value(sig_old 1.0e-3)
    fprintf(p "OLD_DIR   (sim_TOP_cosim_python_A1/psf)       GPIO8 CURRENT @ 1.0ms: %f uA\\n" abs(val_old)*1e6)
)
close(p)
exit()
"""

with open("/tmp/compare_psf.ocn", "w") as f:
    f.write(ocn)

subprocess.run("ocean -nograph -replay /tmp/compare_psf.ocn", shell=True, executable="/bin/bash")
