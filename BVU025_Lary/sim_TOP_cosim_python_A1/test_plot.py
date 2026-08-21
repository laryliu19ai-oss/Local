import subprocess

ocn_code = """
openResults("/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/ams/config/psf")
selectResult('tran)

sig1 = IT("/sim_TOP_cosim_python_A1/Board/GPIO8")
printf("sig1 (IT sim_TOP_...): %L\\n" sig1)

sig2 = IT("/Board/GPIO8")
printf("sig2 (IT /Board/GPIO8): %L\\n" sig2)

sig3 = i("sim_TOP_cosim_python_A1.Board:GPIO8")
printf("sig3 (i sim_TOP_...): %L\\n" sig3)

win = newWindow()
plot(v("/VDD_PCB") ?expr '("VDD_PCB"))
if(sig1 then
    plot(sig1 ?expr '("I(GPIO8)"))
else if(sig2 then
    plot(sig2 ?expr '("I(GPIO8)"))
))

saveGraphImage(?window win ?fileName "/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/ams/config/images/cosim_waveform.png" ?resolution 100 ?width 1600 ?height 900 ?backgroundColor "white" ?saveAllSubwindows t)
printf("Generated image successfully!\\n")
"""

subprocess.run(["ssh", "lary@192.168.16.130", "cat > /tmp/test_plot_sig.ocn"], input=ocn_code.encode("utf-8"))
res = subprocess.run(["ssh", "lary@192.168.16.130", "export DISPLAY=:0; source ~/.bashrc; ocean -replay /tmp/test_plot_sig.ocn"], capture_output=True, text=True)
print(res.stdout)
print(res.stderr)
