#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OneTest Python Virtual Tester Hardware Master Controller
Architecture: 100% Data-Driven Command Interpreter & SAR Search Engine for OneTest JSON specification.
"""

from __future__ import annotations
import os
import sys
import json
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import onetest_hw as hw
except ImportError:
    # Mock hardware bridge for standalone offline testing
    class MockHW:
        @staticmethod
        def set_tm_on(val: int): print(f"[MockHW] set_tm_on({val})")
        @staticmethod
        def set_tm_meas(val: int): print(f"[MockHW] set_tm_meas({val})")
        @staticmethod
        def set_trim_code(code: int): print(f"[MockHW] set_trim_code(0x{code:02X})")
        @staticmethod
        def set_clk(val: int): print(f"[MockHW] set_clk({val})")
        @staticmethod
        def set_done(val: int): print(f"[MockHW] set_done({val})")
        @staticmethod
        def get_cmp() -> int: return 0
        @staticmethod
        def delay_ns(ns: int): pass
        @staticmethod
        def delay_us(us: float): pass
        @staticmethod
        def finish(): print("[MockHW] finish()")

    hw = MockHW()


def _parse_time_us(t_str: str | float | int) -> float:
    """Parse time string with SI units (s, ms, m, us, u, ns, n, ps, p) into microseconds."""
    if t_str is None:
        return 0.0
    if isinstance(t_str, (int, float)):
        return float(t_str)
    s = str(t_str).strip()
    if s.endswith("ms"): return float(s[:-2]) * 1000.0
    if s.endswith("us"): return float(s[:-2])
    if s.endswith("ns"): return float(s[:-2]) / 1000.0
    if s.endswith("ps"): return float(s[:-2]) / 1e6
    if s.endswith("m"): return float(s[:-1]) * 1000.0
    if s.endswith("u"): return float(s[:-1])
    if s.endswith("n"): return float(s[:-1]) / 1000.0
    if s.endswith("p"): return float(s[:-1]) / 1e6
    if s.endswith("s"): return float(s[:-1]) * 1e6
    try:
        return float(s)
    except ValueError:
        return 0.0


def find_config_json() -> str:
    """Locate OneTest JSON specification dynamically across runtime search paths."""
    # 1. Environment variable override
    env_path = os.environ.get("ONETEST_JSON_PATH", "")
    if env_path and os.path.exists(env_path):
        return os.path.abspath(env_path)

    # 2. Standard filenames in current and parent directories
    candidate_names = [
        "run_cosim.oneTest.json",
        "cosim.oneTest.json",
        "cosim.oneTest.sim.json"
    ]
    candidate_dirs = [
        ".",
        "..",
        "../..",
        "../../../pattern/TM15",
        "../pattern/TM15"
    ]
    for d in candidate_dirs:
        for fname in candidate_names:
            p = os.path.join(d, fname)
            if os.path.exists(p):
                return os.path.abspath(p)

    # 3. Glob fallback
    for d in candidate_dirs:
        matches = [f for f in os.listdir(d) if f.endswith(".oneTest.json")] if os.path.exists(d) else []
        if matches:
            return os.path.abspath(os.path.join(d, matches[0]))

    return ""


def parse_dut_pins_from_json(config_data: dict[str, Any]) -> tuple[Optional[str], int, Optional[str]]:
    """
    Dynamically extract Trim Bus name, Bit Width, and Comparator pin from JSON.
    Returns (trim_pin_name, trim_bits, comparator_pin_name).
    """
    one_test = config_data.get("oneTest", {})
    components = one_test.get("components", {})
    testboard_comps = one_test.get("testboard", {}).get("components", {})

    # Locate primary DUT
    dut_info = {}
    if "TOP" in testboard_comps and "id" in testboard_comps["TOP"]:
        dut_id = testboard_comps["TOP"]["id"]
        dut_info = components.get(dut_id, {})
    else:
        for comp_id, comp_val in components.items():
            if comp_val.get("spice_type") == "sub-circuit" and "pins" in comp_val:
                dut_info = comp_val
                break
        if not dut_info and components:
            dut_info = list(components.values())[0]

    pins: dict[str, dict[str, Any]] = dut_info.get("pins", {})
    trim_pin_name = None
    trim_bits = 6
    comparator_pin_name = None

    for pin_name, pin_meta in pins.items():
        pos = pin_meta.get("position")
        p_type = str(pin_meta.get("type", "")).lower()
        p_func = str(pin_meta.get("function", "")).lower()

        # Identify Trim Bus Pin & Bit Width
        if isinstance(pos, list) and len(pos) > 1:
            trim_pin_name = pin_name
            trim_bits = len(pos)
        elif "trim" in pin_name.lower() or "trim" in p_func:
            if not trim_pin_name:
                trim_pin_name = pin_name
                if isinstance(pos, list):
                    trim_bits = len(pos)

        # Identify Comparator Output Pin
        if "comparator" in p_func or "cmp" in pin_name.lower() or ("output" in p_type and ("tmo" in pin_name.lower() or "done" in pin_name.lower())):
            comparator_pin_name = pin_name

    return trim_pin_name, trim_bits, comparator_pin_name


def execute_sar_search(
    action_def: dict[str, Any],
    current_time_us: float,
    num_bits: int = 6,
    clock_half_period_us: float = 50.0,
    output_dirs: Optional[list[str]] = None
) -> tuple[int, float]:
    """
    Execute data-driven N-Bit SAR Binary Search algorithm over hardware pins.
    Supports any arbitrary bit width dynamically (4-bit, 6-bit, 8-bit, etc.).
    Returns (optimal_code, updated_time_us).
    """
    print(f"[{current_time_us:.1f} us] Executing SAR Binary Search Algorithm ({num_bits} bits)...")
    sar_code = 0

    # Binary search from MSB (num_bits - 1) down to LSB (0)
    for bit in range(num_bits - 1, -1, -1):
        trial_code = sar_code | (1 << bit)
        
        # High clock phase: Assert trial trim code
        hw.set_clk(1)
        hw.set_trim_code(trial_code)
        hw.delay_us(clock_half_period_us)
        current_time_us += clock_half_period_us

        # Falling clock edge: Sample analog comparator output
        hw.set_clk(0)
        cmp_val = hw.get_cmp()

        if cmp_val == 1:
            # Current too high -> discard trial bit (keep 0)
            print(f"  -> Bit[{bit}]: CMP = 1 (High) -> Discard. Code: {sar_code} (0x{sar_code:02X})")
        else:
            # Current too low -> keep trial bit (1)
            sar_code = trial_code
            print(f"  -> Bit[{bit}]: CMP = 0 (Low)  -> Keep.    Code: {sar_code} (0x{sar_code:02X})")

        # Low clock phase settling
        hw.delay_us(clock_half_period_us)
        current_time_us += clock_half_period_us

    # Lock optimal converged code and assert done
    hw.set_done(1)
    hw.set_trim_code(sar_code)
    print(f"[{current_time_us:.1f} us] *** SAR Converged: 0x{sar_code:02X} ({sar_code}) ***")

    # Persist state payload for reporting
    state_payload = {
        "final_trim_code": sar_code,
        "final_trim_code_hex": f"0x{sar_code:02X}",
        "num_bits": num_bits,
        "converged": True,
        "timestamp": time.time()
    }
    
    save_dirs = [".", "result"]
    if output_dirs:
        save_dirs.extend(output_dirs)

    for dest_dir in save_dirs:
        try:
            os.makedirs(dest_dir, exist_ok=True)
            with open(os.path.join(dest_dir, ".py_tester_state.json"), "w", encoding="utf-8") as f:
                json.dump(state_payload, f, indent=4)
        except Exception:
            pass

    return sar_code, current_time_us


def run_test(json_path: Optional[str] = None) -> dict:
    """
    Main Master Test Execution Flow.
    100% Data-Driven: strictly interprets and dispatches commands defined in the OneTest specification.
    """
    print("\n=======================================================")
    print(" [Python Virtual Tester] Starting Data-Driven Master Test")
    print("=======================================================")

    if not json_path:
        json_path = find_config_json()

    if not json_path or not os.path.exists(json_path):
        raise FileNotFoundError(f"OneTest specification JSON not found! Searched standard paths.")

    print(f"[Python Virtual Tester] Loaded JSON specification: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    # Dynamically extract pin and bit configurations
    trim_pin_name, trim_bits, comparator_pin_name = parse_dut_pins_from_json(config_data)
    if trim_pin_name:
        print(f"[Python Virtual Tester] Detected Trim Bus: '{trim_pin_name}' ({trim_bits} bits)")
    if comparator_pin_name:
        print(f"[Python Virtual Tester] Detected Comparator: '{comparator_pin_name}'")

    one_test = config_data.get("oneTest", {})
    setup_steps = one_test.get("setup", {}).get("steps", [])
    stop_time_str = one_test.get("setup", {}).get("stop_time", {}).get("value", "")

    # Resolve simulation output directory for state persistence
    sim_cfg = config_data.get("simulation", {})
    sim_out_dir = sim_cfg.get("ams", {}).get("output", {}).get("directory", "") or sim_cfg.get("spectre", {}).get("output", {}).get("directory", "")
    output_dirs = [os.path.join(sim_out_dir, "result")] if sim_out_dir else []

    current_sim_time_us = 0.0

    def advance_to(target_us: float):
        nonlocal current_sim_time_us
        dt = target_us - current_sim_time_us
        if dt > 0:
            hw.delay_us(dt)
            current_sim_time_us = target_us

    # -------------------------------------------------------------
    # Iterate dynamically through all setup steps in JSON
    # -------------------------------------------------------------
    for step in setup_steps:
        step_id = step.get("id", "unnamed_step")
        target_time_us = _parse_time_us(step.get("time", {}).get("value", 0))
        advance_to(target_time_us)

        print(f"[{current_sim_time_us:.1f} us] Step '{step_id}': Dispatching actions...")
        actions = step.get("actions", {})

        for act_name, act in actions.items():
            act_type = act.get("type", "")
            conn = act.get("connection", "")

            # 1. Voltage Source Actions (Driving digital/enable pins)
            if act_type == "voltage_source":
                volt = float(act.get("voltage", 0.0))
                pin_val = 1 if volt > 0.5 else 0
                
                if conn == trim_pin_name:
                    hw.set_trim_code(int(volt))
                elif "meas" in conn.lower():
                    hw.set_tm_meas(pin_val)
                elif "on" in conn.lower() or "en" in conn.lower() or "tm" in conn.lower():
                    hw.set_tm_on(pin_val)
                elif "clk" in conn.lower():
                    hw.set_clk(pin_val)
                elif "done" in conn.lower():
                    hw.set_done(pin_val)

            # 2. Digital Source Actions (Driving digital buses / codes)
            elif act_type == "digital_source":
                dig_val = int(act.get("value", 0))
                if conn == trim_pin_name or "trim" in conn.lower():
                    hw.set_trim_code(dig_val)
                elif "meas" in conn.lower():
                    hw.set_tm_meas(dig_val)
                elif "on" in conn.lower() or "en" in conn.lower() or "tm" in conn.lower():
                    hw.set_tm_on(dig_val)
                elif "clk" in conn.lower():
                    hw.set_clk(dig_val)
                elif "done" in conn.lower():
                    hw.set_done(dig_val)

            # 3. Measurement / Algorithm Actions
            elif act_type == "measure":
                capability = str(act.get("capability", "")).lower()
                metric = str(act.get("measure", {}).get("metric", "")).upper()
                
                # Check if this measurement is an active SAR calibration search
                is_sar_action = (
                    "sar" in step_id.lower() or
                    metric == "TRIM_CODE" or
                    (capability == "digital_measurement" and (conn == trim_pin_name or "trim" in conn.lower()))
                )

                if is_sar_action:
                    _, current_sim_time_us = execute_sar_search(
                        action_def=act,
                        current_time_us=current_sim_time_us,
                        num_bits=trim_bits,
                        output_dirs=output_dirs
                    )
                else:
                    # Passive measurement checkpoint for report extraction
                    print(f"  -> Passive measure checkpoint '{act_name}' ({conn}, {metric}) at {current_sim_time_us:.1f} us")

    # Advance to overall simulation stop time if specified
    if stop_time_str:
        sim_stop_us = _parse_time_us(stop_time_str)
        advance_to(sim_stop_us)

    print(f"\n[Python Virtual Tester] Test plan completed at {current_sim_time_us:.1f} us.\n")
    return {"status": "SUCCESS", "sim_time_us": current_sim_time_us}


if __name__ == "__main__":
    run_test()