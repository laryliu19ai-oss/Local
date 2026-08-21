# sim_TOP_cosim_sv_A1 SystemVerilog OneTest 協同模擬說明

本目錄為 **sim_TOP_cosim_sv_A1 SystemVerilog 虛擬測試機（Virtual Host Controller / Tester）** 之模擬環境。

所有產生的模擬腳本、波形資料庫（PSF）與測試量測報告均儲存於本資料夾（`sim_TOP_cosim_sv_A1/`）內。

---

## 檔案清單

| 檔案名稱 | 說明 |
| :--- | :--- |
| **`cosim.oneTest.json`** | 定義 DUT (`TOP_A1`)、測試規格、Pin 腳定義、Setup 激勵步驟與量測項目 (Items 101, 102, 103)。 |
| **`run_cosim.py`** | 核心 Python 執行腳本：解析 JSON、調度 AMS 模擬、量測並產生 JSON 驗證報告。 |
| **`py_tester.sv`** | SystemVerilog 虛擬測試機台 HDL 代碼（實現 50us SAR 時鐘校準與量測模式切換）。 |
| **`cosim.waveform.json`** | 波型擷取設定檔（VDD_PCB 與 GPIO8 電流多軌波型）。 |
| **`cosim.evaluation.json`** | 波型評估計算設定檔（計算 1.8ms 下的 GPIO8 穩態電流值）。 |
| **`test_report.json`** | 比對規格 Limits 後產生的 PASS / FAIL 測試報告。 |

---

## 在虛擬工作站執行模擬指令

進入該資料夾並執行：

```bash
cd /home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_sv_A1

# 1. 執行 AMS 模擬並評估
python3 run_cosim.py

# 2. 或單獨解析量測結果
python3 run_cosim.py --eval

# 3. 開啟 Viva 波型檢視器
python3 run_cosim.py --viva
```
