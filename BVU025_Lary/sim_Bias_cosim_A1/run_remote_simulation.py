import subprocess
import sys

def run():
    print("=== Executing AMS Co-Simulation on Virtual Workstation (192.168.16.130) ===")
    cmd = "cd /home/lary/simulation/sim_Bias_cosim_A1/ams/config/netlist && ./runSimulation"
    res = subprocess.run(["ssh", "lary@192.168.16.130", cmd], capture_output=True, text=True)
    print("STDOUT:")
    print(res.stdout)
    if res.stderr:
        print("\nSTDERR:")
        print(res.stderr)
    print(f"\nExit Code: {res.returncode}")

if __name__ == "__main__":
    run()
