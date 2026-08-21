#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real-time Dynamic Python SAR Controller for Cadence AMS Co-Simulation (Condition A)
Author: Antigravity Agent
"""

import os
import sys
import time
import json

IPC_CMD_FILE = "/tmp/py_sar_cmd.txt"
IPC_RESP_FILE = "/tmp/py_sar_resp.txt"

class RealtimePythonSAR:
    def __init__(self, trim_bits=6):
        self.trim_bits = trim_bits
        self.current_bit = trim_bits - 1
        self.code = 1 << (trim_bits - 1)  # Initial startcode: 32 (100000b)
        self.step = self.code >> 1
        self.done = 0
        self.iteration = 0
        self.history = []

    def reset(self):
        self.current_bit = self.trim_bits - 1
        self.code = 1 << (self.trim_bits - 1)
        self.step = self.code >> 1
        self.done = 0
        self.iteration = 0
        self.history = [(0, self.code, 0)]
        print(f"\n[Python SAR] === Reset SAR Engine (Initial Code = {self.code}) ===")

    def step_sar(self, cmp_val):
        """Execute one step of Successive Approximation in Python."""
        self.iteration += 1
        is_high = 1 if cmp_val > 1.5 else 0
        
        print(f"[Python SAR Step {self.iteration}] Received CMP={cmp_val:.3f}V (Logic {is_high}) | Current Code={self.code}")

        # If comparator is high, clear the previously tested bit
        if is_high:
            self.code -= self.step
            print(f"  -> CMP is HIGH: Clear bit, Code becomes {self.code}")
        else:
            print(f"  -> CMP is LOW: Keep bit, Code remains {self.code}")

        # Move to the next bit
        self.step = self.step >> 1
        if self.step > 0:
            self.code += self.step
            print(f"  -> Testing next bit: Code updated to {self.code}")
        else:
            self.done = 1
            print(f"  -> SAR Complete! Final Trim Code = {self.code} ({bin(self.code)})")

        self.history.append((self.iteration, self.code, self.done))
        return self.code, self.done

def run_ipc_server():
    print("=========================================================")
    print("   Real-Time Dynamic Python SAR Server (Condition A)    ")
    print("=========================================================")
    print(f"IPC Communication Files:\n  Command : {IPC_CMD_FILE}\n  Response: {IPC_RESP_FILE}\n")
    
    sar = RealtimePythonSAR()
    sar.reset()

    # Clean previous IPC files
    for f in [IPC_CMD_FILE, IPC_RESP_FILE]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

    # Write initial response so simulation starts with initial code
    with open(IPC_RESP_FILE, 'w') as f:
        f.write(f"{sar.code} {sar.done}\n")

    print("[Python SAR] Listening for real-time requests from Cadence AMS simulator...")
    
    last_mtime = 0
    try:
        while True:
            if os.path.exists(IPC_CMD_FILE):
                try:
                    mtime = os.path.getmtime(IPC_CMD_FILE)
                    if mtime != last_mtime:
                        last_mtime = mtime
                        with open(IPC_CMD_FILE, 'r') as f:
                            content = f.read().strip()
                        
                        if content:
                            tokens = content.split()
                            cmd_type = tokens[0]
                            
                            if cmd_type == "RESET":
                                sar.reset()
                                out_code, out_done = sar.code, sar.done
                            elif cmd_type == "STEP":
                                cmp_val = float(tokens[1]) if len(tokens) > 1 else 0.0
                                out_code, out_done = sar.step_sar(cmp_val)
                            else:
                                out_code, out_done = sar.code, sar.done

                            # Send response back to Verilog-A in real time
                            with open(IPC_RESP_FILE, 'w') as f:
                                f.write(f"{out_code} {out_done}\n")
                except Exception as e:
                    pass
            time.sleep(0.001)  # 1ms polling for ultra-low latency handshake
    except KeyboardInterrupt:
        print("\n[Python SAR] Server stopped.")

if __name__ == "__main__":
    run_ipc_server()
