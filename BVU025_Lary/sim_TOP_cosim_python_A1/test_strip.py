import subprocess

ocn_code = """
openResults("/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/ams/config/psf")
selectResult('tran)

v_vdd = v("/VDD_PCB")
i_gpio8 = IT("/Board/GPIO8")

win = newWindow()
awvSetStripMode(win "strip")
awvPlotWaveform(?window win ?stripNumber 1 ?expr '("VDD_PCB") ?color '("red") ?trace v_vdd)
awvPlotWaveform(?window win ?stripNumber 2 ?expr '("I(GPIO8)") ?color '("blue") ?trace i_gpio8)

saveGraphImage(?window win ?fileName "/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/ams/config/images/cosim_waveform.png" ?resolution 100 ?width 1600 ?height 900 ?backgroundColor "white" ?saveAllSubwindows t)
printf("SUCCESS_STRIP_PLOT\\n")
"""

subprocess.run(["ssh", "lary@192.168.16.130", "cat > /tmp/test_strip_plot.ocn"], input=ocn_code.encode("utf-8"))
res = subprocess.run(["ssh", "lary@192.168.16.130", "export DISPLAY=:0; source ~/.bashrc; ocean -replay /tmp/test_strip_plot.ocn"], capture_output=True, text=True)
print(res.stdout)
print(res.stderr)
