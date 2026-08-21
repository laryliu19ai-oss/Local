import subprocess

ocn_code = """
openResults("/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/ams/config/psf")
selectResult('tran)

v_vdd = v("sim_TOP_cosim_python_A1.VDD_PCB")
i_gpio8 = IT("/sim_TOP_cosim_python_A1/Board/GPIO8")

win = newWindow()
plot(v_vdd ?expr '("VDD_PCB"))
plot(i_gpio8 ?expr '("I_GPIO8"))

saveGraphImage(?window win ?fileName "/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/ams/config/images/cosim_waveform.png" ?resolution 100 ?width 1600 ?height 900 ?backgroundColor "white" ?saveAllSubwindows t)
printf("SUCCESS: Image generated at /home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/ams/config/images/cosim_waveform.png\\n")
"""

subprocess.run(["ssh", "lary@192.168.16.130", "cat > /tmp/gen_wave.ocn"], input=ocn_code.encode("utf-8"))
res = subprocess.run(["ssh", "lary@192.168.16.130", "export DISPLAY=:0; source ~/.bashrc; ocean -replay /tmp/gen_wave.ocn"], capture_output=True, text=True)
print(res.stdout)
print(res.stderr)
