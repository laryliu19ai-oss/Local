import subprocess
import os

ocn_code = """
openResults("/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_sv_A1/ams/config/psf")
selectResult('tran)

v_vdd = v("/VDD_PCB")
i_gpio8 = IT("/Board/GPIO8")

win = newWindow()
awvSetStripMode(win "strip")
awvPlotWaveform(?window win ?stripNumber 1 ?expr '("VDD_PCB") ?color '("red") ?trace v_vdd)
awvPlotWaveform(?window win ?stripNumber 2 ?expr '("I(GPIO8)") ?color '("blue") ?trace i_gpio8)

saveGraphImage(?window win ?fileName "/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_sv_A1/ams/config/images/cosim_waveform.png" ?resolution 100 ?width 1600 ?height 900 ?backgroundColor "white" ?saveAllSubwindows t)
printf("SUCCESS_STRIP_PLOT\\n")
exit()
"""

with open("/tmp/strip_plot.ocn", "w") as f:
    f.write(ocn_code)

res = subprocess.run("export DISPLAY=:0; source ~/.bashrc; ocean -nograph -replay /tmp/strip_plot.ocn", shell=True, executable="/bin/bash", capture_output=True, text=True)
print(res.stdout)
if "SUCCESS_STRIP_PLOT" in res.stdout:
    print("Waveform image updated successfully at /home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_sv_A1/ams/config/images/cosim_waveform.png")
