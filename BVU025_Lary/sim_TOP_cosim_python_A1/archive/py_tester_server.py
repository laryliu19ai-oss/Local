#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python Full Virtual Tester Server for sim_TOP_cosim_python_A1 (Condition A)
Controls: aVdd, aVss, TMIRefOn, TMIRefMeas, GPIO8, NvTrmIref<5:0>, dIRefTMO
"""

import os
import sys
import time

IPC_CMD = "/tmp/py_tester_cmd.txt"
IPC_RESP = "/tmp/py_tester_resp.txt"

class FullVirtualTester:
    def __init__(self):
        self.reset()

    def reset(self):
        self.v_avdd = 0.0
        self.v_tmon = 0.0
        self.v_tmmeas = 0.0
        self.gpio8_mode = 0  # 0: Off, 1: Force Curr (2uA), 2: Force 0V (Sense)
        self.i_gpio8 = 0.0
        self.code = 0
        self.sar_step = 32
        self.sar_active = False
        print("\n[Python Full Tester] === Initialized Virtual Tester ===")

    def process_event(self, t_sec, cmp_val):
        """Process simulation time event and return new control vector."""
        t_ms = t_sec * 1e3

        # Step 1: Power up (t >= 0.1ms)
        if t_ms >= 0.09 and t_ms < 0.38:
            self.v_avdd = 3.3
            self.v_tmon = 0.0
            self.v_tmmeas = 0.0
            self.gpio8_mode = 0
            print(f"[Python Tester @ {t_ms:.3f}ms] -> Power Up: aVdd=3.3V")

        # Step 2: Enable Trim Mode (t >= 0.39ms)
        elif t_ms >= 0.38 and t_ms < 0.40:
            self.v_tmon = 3.3
            print(f"[Python Tester @ {t_ms:.3f}ms] -> Enable Trim Mode: TMIRefOn=3.3V")

        # Step 3: Force Calibration Current 2uA (t >= 0.40ms)
        elif t_ms >= 0.40 and t_ms < 0.49:
            self.gpio8_mode = 1
            self.i_gpio8 = 2e-6
            self.code = 32
            self.sar_step = 16
            self.sar_active = True
            print(f"[Python Tester @ {t_ms:.3f}ms] -> Force 2uA ISAR to GPIO8 | Init SAR Code=32")

        # Step 4: SAR Successive Approximation (t >= 0.5ms ~ 1.4ms)
        elif t_ms >= 0.49 and t_ms < 1.40:
            is_high = 1 if cmp_val > 1.5 else 0
            print(f"[Python Tester SAR @ {t_ms:.3f}ms] -> Sampled dIRefTMO={cmp_val:.3f}V (Logic {is_high})")
            
            if is_high:
                self.code -= self.sar_step
                print(f"  -> CMP is HIGH: Clear bit, Code becomes {self.code}")
            else:
                print(f"  -> CMP is LOW: Keep bit, Code remains {self.code}")

            self.sar_step = self.sar_step >> 1
            if self.sar_step > 0:
                self.code += self.sar_step
                print(f"  -> Next Test Code = {self.code} (Testing step {self.sar_step})")
            else:
                print(f"  -> SAR Finished! Final Calibrated Code = {self.code} ({bin(self.code)})")

        # Step 5: Enable Measure Mode (t >= 1.41ms)
        elif t_ms >= 1.40 and t_ms < 1.59:
            self.v_tmon = 0.0
            self.v_tmmeas = 3.3
            self.gpio8_mode = 2 # Sense ground
            print(f"[Python Tester @ {t_ms:.3f}ms] -> Switch to Measure Mode: TMIRefOn=0V, TMIRefMeas=3.3V, GPIO8=Sense(0V)")

        # Step 6: Measurement Output (t >= 1.6ms)
        elif t_ms >= 1.59:
            print(f"[Python Tester @ {t_ms:.3f}ms] -> Ready for IRef measurement on GPIO8 (Code = {self.code})")

        return f"{self.v_avdd:.3f} {self.v_tmon:.3f} {self.v_tmmeas:.3f} {self.gpio8_mode} {self.i_gpio8:.9f} {self.code}\n"

def run_server():
    tester = FullVirtualTester()
    tester.reset()

    # Clean old IPC files
    for f in [IPC_CMD, IPC_RESP]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

    # Initial response
    with open(IPC_RESP, 'w') as f:
        f.write(f"0.0 0.0 0.0 0 0.0 0\n")

    print("=========================================================")
    print("   Real-Time Full Python Tester Server (Condition A)    ")
    print("   Controlling: aVdd, aVss, TMIRefOn, TMIRefMeas, GPIO8, NvTrmIref<5:0> ")
    print("=========================================================")
    print("[Python Tester] Listening for simulation events from py_tester symbol...")

    last_mtime = 0
    try:
        while True:
            if os.path.exists(IPC_CMD):
                try:
                    mtime = os.path.getmtime(IPC_CMD)
                    if mtime != last_mtime:
                        last_mtime = mtime
                        with open(IPC_CMD, 'r') as f:
                            content = f.read().strip()
                        
                        if content:
                            tokens = content.split()
                            if tokens[0] == "INIT":
                                tester.reset()
                                resp = "0.0 0.0 0.0 0 0.0 0\n"
                            elif tokens[0] == "TIME":
                                t_val = float(tokens[1])
                                cmp_val = float(tokens[3]) if len(tokens) > 3 else 0.0
                                resp = tester.process_event(t_val, cmp_val)
                            else:
                                resp = "0.0 0.0 0.0 0 0.0 0\n"

                            with open(IPC_RESP, 'w') as f:
                                f.write(resp)
                except Exception as e:
                    pass
            time.sleep(0.001)
    except KeyboardInterrupt:
        print("\n[Python Tester] Stopped.")

if __name__ == "__main__":
    run_server()
