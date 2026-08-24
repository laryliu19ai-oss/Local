#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python Master Test Controller for OneTest Co-Simulation
Architecture: Python-Led DPI-C Master Controller (matching i2c_communication_python)
"""

from __future__ import annotations
import os
import sys
import json
import time

try:
    import onetest_hw as hw
except ImportError:
    # Mock hardware bridge for standalone testing outside EDA simulator
    class MockHW:
        @staticmethod
        def set_tm_on(val): print(f"[MockHW] set_tm_on({val})")
        @staticmethod
        def set_tm_meas(val): print(f"[MockHW] set_tm_meas({val})")
        @staticmethod
        def set_trim_code(code): print(f"[MockHW] set_trim_code(0x{code:02X})")
        @staticmethod
        def set_clk(val): print(f"[MockHW] set_clk({val})")
        @staticmethod
        def set_done(val): print(f"[MockHW] set_done({val})")
        @staticmethod
        def get_cmp(): return 0
        @staticmethod
        def delay_ns(ns): pass
        @staticmethod
        def delay_us(us): pass
        @staticmethod
        def finish(): print("[MockHW] finish()")

    hw = MockHW()


def _parse_time_us(t_str: str | float | int) -> float:
    """Parse time string like '100u', '1.4m', '10n', '1.8ms' into microseconds."""
    if isinstance(t_str, (int, float)):
        return float(t_str)
    s = str(t_str).strip()
    if s.endswith("ms"): return float(s[:-2]) * 1000.0
    if s.endswith("us") or s.endswith("u"): return float(s.rstrip("us"))
    if s.endswith("ns") or s.endswith("n"): return float(s.rstrip("ns")) / 1000.0
    if s.endswith("s"): return float(s[:-1]) * 1e6
    try:
        return float(s)
    except ValueError:
        return 0.0


def find_config_json() -> str:
    """Locate cosim.oneTest.json in current and standard project paths."""
    search_paths = [
        os.environ.get("ONETEST_JSON_PATH", ""),
        "cosim.oneTest.json",
        "cosim.oneTest.sim.json",
        "../cosim.oneTest.json",
        "/home/lary/project/BVU025/SCH/cosim/pattern/TM14/cosim.oneTest.json",
        "/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/ams/config/netlist/cosim.oneTest.json",
        "c:/Antgravity/Local/BVU025_Lary/sim_TOP_cosim_python_A1/cosim.oneTest.json"
    ]
    for p in search_paths:
        if p and os.path.exists(p):
            return os.path.abspath(p)
    return ""


def run_test(json_path: str = None) -> dict:
    """
    Main Master Test Execution Flow.
    Directly executed by C bridge (c_main_tester) or standalone test.
    """
    print("\n=======================================================")
    print(" [Python Virtual Tester] Starting Python-Led Master Test")
    print("=======================================================")

    if not json_path:
        json_path = find_config_json()

    config_data = {}
    if json_path and os.path.exists(json_path):
        print(f"[Python Virtual Tester] Loaded test definition: {json_path}")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception as e:
            print(f"[Python Virtual Tester] Warning: could not parse JSON ({e})")
    else:
        print("[Python Virtual Tester] Notice: Using built-in default SAR test plan.")

    one_test = config_data.get("oneTest", {})
    setup_steps = one_test.get("setup", {}).get("steps", [])

    # Default timeline values if not in JSON
    power_up_us = 100.0
    trim_start_us = 390.0
    meas_start_us = 1400.0
    sim_stop_us = 1800.0

    # Parse timeline from JSON steps
    for step in setup_steps:
        sid = step.get("id", "")
        t_val = _parse_time_us(step.get("time", {}).get("value", 0))
        if sid == "power_up":
            power_up_us = t_val
        elif sid in ("enable_iref_trim_mode", "force_calibration_current"):
            trim_start_us = min(trim_start_us, t_val) if trim_start_us else t_val
        elif sid == "enable_iref_measure_mode":
            meas_start_us = t_val

    stop_str = one_test.get("setup", {}).get("stop_time", {}).get("value")
    if stop_str:
        sim_stop_us = _parse_time_us(stop_str)

    current_sim_time_us = 0.0

    def advance_to(target_us: float):
        nonlocal current_sim_time_us
        dt = target_us - current_sim_time_us
        if dt > 0:
            hw.delay_us(dt)
            current_sim_time_us = target_us

    # -------------------------------------------------------------
    # Step 1: Power-Up & Circuit Settling (0 -> 390us)
    # -------------------------------------------------------------
    print(f"\n[Step 1] Power-up and analog supply settling until {trim_start_us:.1f} us...")
    hw.set_tm_on(0)
    hw.set_tm_meas(0)
    hw.set_clk(0)
    hw.set_done(0)
    hw.set_trim_code(0x20)
    advance_to(trim_start_us)

    # -------------------------------------------------------------
    # Step 2: Enable Trim Mode (390us -> 400us)
    # -------------------------------------------------------------
    print(f"[Step 2 @ {current_sim_time_us:.1f} us] Enabling Trim Mode (TMIRefOn = 1)...")
    hw.set_tm_on(1)
    advance_to(trim_start_us + 10.0)

    # -------------------------------------------------------------
    # Step 3: Active SAR 6-bit Binary Search Calibration (400us -> 1000us)
    # -------------------------------------------------------------
    print(f"[Step 3 @ {current_sim_time_us:.1f} us] Executing 6-Bit SAR Binary Search Algorithm...")
    sar_code = 0

    for bit in range(5, -1, -1):
        trial_code = sar_code | (1 << bit)
        
        # High clock phase (50us): Assert trial code
        hw.set_clk(1)
        hw.set_trim_code(trial_code)
        hw.delay_us(50.0)
        current_sim_time_us += 50.0

        # Falling clock edge: Sample comparator
        hw.set_clk(0)
        cmp_val = hw.get_cmp()

        if cmp_val == 1:
            # Current too high -> discard trial bit (keep 0)
            print(f"  -> SAR Bit[{bit}]: CMP = 1 (High) -> Discard 1 to 0. Code: {sar_code} (0x{sar_code:02X})")
        else:
            # Current too low -> keep trial bit (1)
            sar_code = trial_code
            print(f"  -> SAR Bit[{bit}]: CMP = 0 (Low)  -> Keep 1.        Code: {sar_code} (0x{sar_code:02X})")

        # Low clock phase (50us settling)
        hw.delay_us(50.0)
        current_sim_time_us += 50.0

    # -------------------------------------------------------------
    # Step 4: SAR Convergence Confirmation & Lock (1000us -> 1400us)
    # -------------------------------------------------------------
    hw.set_done(1)
    hw.set_trim_code(sar_code)
    print(f"\n[Step 4 @ {current_sim_time_us:.1f} us] *** SAR Calibration Converged! ***")
    print(f"       Optimal Trim Code = 0x{sar_code:02X} ({sar_code}), dDone = 1")

    # Persist state file for test report parser
    state_payload = {
        "final_trim_code": sar_code,
        "final_trim_code_hex": f"0x{sar_code:02X}",
        "converged": True,
        "timestamp": time.time()
    }
    for dest_dir in [".", "result", "/home/lary/project/BVU025/SCH/cosim/pattern/TM14/result", "/home/lary/simulation/BVU025/BVU025A/result"]:
        try:
            os.makedirs(dest_dir, exist_ok=True)
            with open(os.path.join(dest_dir, ".py_tester_state.json"), "w", encoding="utf-8") as f:
                json.dump(state_payload, f, indent=4)
        except Exception:
            pass

    advance_to(meas_start_us)

    # -------------------------------------------------------------
    # Step 5: Switch to Measure Mode (1400us -> sim_stop_us)
    # -------------------------------------------------------------
    print(f"[Step 5 @ {current_sim_time_us:.1f} us] Switching to Measure Mode (TMIRefOn=0, TMIRefMeas=1)...")
    hw.set_tm_on(0)
    hw.set_tm_meas(1)
    advance_to(sim_stop_us)

    print(f"[Python Virtual Tester] Simulation completed successfully at {current_sim_time_us:.1f} us.\n")
    return state_payload


if __name__ == "__main__":
    run_test()