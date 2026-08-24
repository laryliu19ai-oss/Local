import subprocess
import os

ocn = """
openResults("/home/lary/simulation/BVU025/BVU025A/ocean/BVU025_Lary/sim_TOP_cosim_python_A1_ocean/psf")
printf("RESULTS: %L\\n", results())
selectResult('tran)
sigs = signals()
printf("TOTAL SIGNALS: %d\\n", length(sigs))
p = outfile("/tmp/all_signals.txt" "w")
foreach(s sigs
    fprintf(p "%s\\n" s)
    if(rexMatchp("Trm" s) || rexMatchp("Trim" s) || rexMatchp("Nv" s) || rexMatchp("GPIO" s) then
        printf("MATCH: %s\\n" s)
    )
)
close(p)
exit()
"""

with open("/tmp/find_sigs.ocn", "w") as f:
    f.write(ocn)

subprocess.run("ocean -nograph -replay /tmp/find_sigs.ocn", shell=True, executable="/bin/bash")
