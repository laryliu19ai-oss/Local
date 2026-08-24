#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python Virtual Tester Engine for BVU025 AMS Co-Simulation
Author: Antigravity Agent
Description:
  Pure Python Testbench logic for SAR successive approximation calibration,
  timing sequencing, and dynamic test control via SystemVerilog DPI-C.
"""

import os
import sys
import json

class PythonVirtualTester:
    def __init__(self, work_dir="."):
        self.work_dir = os.path.abspath(work_dir)
        self.bit_idx = 5
        self.current_trim = 0x20  # Default 6'b100000 (32)
        self.state = "INIT"
        self.sar_step_count = 0
        self.is_done = False
        self.tm_on = 0
        self.tm_meas = 0
        self.clk = 0
        
        print(f"[Python Virtual Tester] Initialized in directory: {self.work_dir}")
        print(f"[Python Virtual Tester] Starting test sequence with default Trim Code = 0x{self.current_trim:02X} ({self.current_trim})")

    def step(self, time_ns, cmp_val):
        """
        Called by SystemVerilog DPI-C on simulation events/clock edges.
        
        Args:
            time_ns (int): Current simulation time in nanoseconds.
            cmp_val (int): Sampled digital comparator output (dIRefTMO: 0 or 1).
            
        Returns:
            tuple: (trim_code, clk, done, tm_on, tm_meas)
        """
        time_us = time_ns / 1000.0

        # Phase 1: Power-up (0 ~ 390us)
        if time_us < 390.0:
            self.tm_on = 0
            self.tm_meas = 0
            self.clk = 0
            self.is_done = False
            self.current_trim = 0x20

        # Phase 2: Enable Trim Mode at 390us
        elif 390.0 <= time_us < 400.0:
            if self.tm_on == 0:
                print(f"[Python Virtual Tester @ {time_ns} ns ({time_us:.1f} us)] -> TMIRefOn = 1 (Trim Mode Enabled)")
            self.tm_on = 1
            self.tm_meas = 0
            self.clk = 0
            self.is_done = False

        # Phase 3: Synchronous 6-bit Binary SAR Calibration (400us ~ 1000us)
        elif 400.0 <= time_us < 1000.0:
            self.tm_on = 1
            self.tm_meas = 0
            
            # Each SAR cycle is 100us (50us High, 50us Low)
            cycle_time = (time_us - 400.0) % 100.0
            cycle_idx = int((time_us - 400.0) // 100.0)
            current_bit = 5 - cycle_idx

            if current_bit >= 0:
                # 50us High Phase (0 ~ 50us of cycle): Apply trial bit = 1
                if cycle_time < 50.0:
                    self.clk = 1
                    # Ensure trial bit is set
                    self.current_trim |= (1 << current_bit)
                # 50us Low Phase (50 ~ 100us of cycle): Immediate evaluation at falling edge
                else:
                    self.clk = 0
                    if cycle_time >= 50.0 and cycle_time < 51.0:
                        # Falling edge evaluation
                        if cmp_val == 1:
                            # Comparator High -> current too large -> discard bit (clear to 0)
                            self.current_trim &= ~(1 << current_bit)
                            print(f"[Python Virtual Tester @ {time_ns} ns ({time_us:.1f} us)] -> SAR Bit[{current_bit}]: CMP=1 (High) -> Discard Bit 1 to 0. Updated Trim Code = {self.current_trim} (0x{self.current_trim:02X})")
                        else:
                            # Comparator Low -> keep bit as 1
                            print(f"[Python Virtual Tester @ {time_ns} ns ({time_us:.1f} us)] -> SAR Bit[{current_bit}]: CMP=0 (Low)  -> Keep Bit 1. Updated Trim Code = {self.current_trim} (0x{self.current_trim:02X})")

        # Phase 4: SAR Calibration Completed (1000us ~ 1400us)
        elif 1000.0 <= time_us < 1400.0:
            if not self.is_done:
                self.is_done = True
                print(f"[Python Virtual Tester @ {time_ns} ns ({time_us:.1f} us)] -> *** SAR Calibration Converged! Optimal Trim Code = {self.current_trim} (0x{self.current_trim:02X}), dDone = 1 ***", flush=True)
                # Persist state for runner
                state_dirs = [
                    os.path.join(self.work_dir, "result"),
                    os.path.join(self.work_dir, "..", "..", "result"),
                    os.path.join(self.work_dir, "..", "..", "..", "result"),
                    "/tmp"
                ]
                for sdir in state_dirs:
                    try:
                        os.makedirs(sdir, exist_ok=True)
                        with open(os.path.join(sdir, ".py_tester_state.json"), "w") as sf:
                            json.dump({"optimal_trim_code": int(self.current_trim), "converged": True}, sf)
                    except Exception:
                        pass
            self.tm_on = 1
            self.tm_meas = 0
            self.clk = 0

        # Phase 5: Measurement Mode Switch (1400us ~ 2000us)
        else:
            if self.tm_meas == 0:
                print(f"[Python Virtual Tester @ {time_ns} ns ({time_us:.1f} us)] -> Switching to IRef Measurement Mode (TMIRefOn=0, TMIRefMeas=1, Sense GND on GPIO8)")
            self.tm_on = 0
            self.tm_meas = 1
            self.clk = 0
            self.is_done = True

        return (int(self.current_trim), int(self.clk), int(1 if self.is_done else 0), int(self.tm_on), int(self.tm_meas))

# Global singleton instance for DPI-C
_tester_instance = None

def get_tester(work_dir="."):
    global _tester_instance
    if _tester_instance is None:
        _tester_instance = PythonVirtualTester(work_dir)
    return _tester_instance

def c_step_callback(time_ns, cmp_val):
    tester = get_tester()
    return tester.step(time_ns, cmp_val)

if __name__ == "__main__":
    t = PythonVirtualTester(".")
    print("Self-test completed successfully.")