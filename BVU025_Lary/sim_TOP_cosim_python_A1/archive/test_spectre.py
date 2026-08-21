import subprocess

# Write clean Spectre test file
scs_content = """// Spectre test
simulator lang=spectre
ahdl_include "/home/lary/project/BVU025/SCH/BVU025_Lary/py_tester/veriloga/veriloga.va"

vss (gnd 0) vsource dc=0
x1 (vdd gnd tmon tmmeas gpio8 trim5 trim4 trim3 trim2 trim1 trim0 tmo) py_tester
tran tran stop=1u
"""

subprocess.run(['ssh', 'lary@192.168.16.130', 'cat > /tmp/test_va2.scs'], input=scs_content.encode())
res = subprocess.run(['ssh', 'lary@192.168.16.130', 'spectre -64 /tmp/test_va2.scs'], capture_output=True, text=True)
print(res.stdout)
print(res.stderr)
