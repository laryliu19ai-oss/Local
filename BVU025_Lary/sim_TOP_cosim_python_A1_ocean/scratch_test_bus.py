import subprocess

ocn = """
openResults("/home/lary/simulation/BVU025/BVU025A/ocean/BVU025_Lary/sim_TOP_cosim_python_A1_ocean/psf")
selectResult('tran)
bus = getData("sim_TOP_cosim_python_A1.NvTrmIref[5:0]")
printf("BUS OBJ: %L\\n", bus)
v = value(bus 1.2e-3)
printf("VAL AT 1.2m: %L (type: %s)\\n", v, type(v))

for(i 0 5
    sig = getData(sprintf(nil "sim_TOP_cosim_python_A1.NvTrmIref[%d]" i))
    printf("BIT %d: %L -> value at 1.2m: %L\\n", i, sig, value(sig 1.2e-3))
)
exit()
"""

with open("/tmp/test_bus.ocn", "w") as f:
    f.write(ocn)

subprocess.run("ocean -nograph -replay /tmp/test_bus.ocn", shell=True, executable="/bin/bash")
