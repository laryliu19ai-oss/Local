# sim_TOP_cosim_python_A1 Python OneTest 協同模擬說明

本目錄為 **情況 B：Python 作為 OneTest 測試執行器（Outer Orchestrator）** 之模擬環境。

所有產生的模擬腳本、波形資料庫（PSF）與測試量測報告均完全儲存於本資料夾（`sim_TOP_cosim_python_A1/`）內。

---

## 檔案清單

| 檔案名稱 | 說明 |
| :--- | :--- |
| **`cosim.oneTest.json`** | 定義 DUT (`TOP_A1`)、測試規格、Pin 腳定義、Setup 激勵步驟與量測項目 (Items 101, 102, 103)。 |
| **`run_cosim.py`** | 核心 Python 執行腳本：解析 JSON、產生 OCEAN 模擬指令、調度 AMS 模擬、量測並產生 JSON 驗證報告。 |
| **`run_test.ocn`** | 由 Python 自動生成的 OCEAN 批次模擬腳本（包含全部電壓與電流 All-probe 設定）。 |
| **`measurement_results.txt`** | 模擬完成後自動匯出的各項測量數據。 |
| **`test_report.json`** | Python 自動比對規格 Limits 後產生的 PASS / FAIL 測試報告。 |

---

## 在虛擬工作站執行模擬指令

進入該資料夾並執行：

```bash
cd ~/project/BVU025/python/sim_TOP_cosim_python_A1
# 或 Windows/Samba 掛載路徑

# 1. 產生模擬腳本並執行模擬
python3 run_cosim.py --run

# 2. 或單獨解析量測結果
python3 run_cosim.py --eval
```

---

## 為什麼不需要建立 Python Symbol？
在 **情況 B** 架構下，Python 擔任的是外層自動化調度（Test Orchestrator）角色，直接讀取 `cosim.oneTest.json` 的時間軸電壓/電流設定，並調用 Virtuoso / AMS 批次核心模擬，模擬完成後自動抓取波形驗證，因此**不需要在電路圖中額外建立 Python Symbol**。
