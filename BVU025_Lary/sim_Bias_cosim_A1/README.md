# sim_Bias_cosim_A1 AMS 混訊模擬修復檔案說明

本目錄包含本次針對 `BVU025_Lary` 的 `sim_Bias_cosim_A1:config` AMS 混訊模擬錯誤排查與修復所產生及使用的相關檔案：

## 檔案清單

| 檔案名稱 | 說明 |
| :--- | :--- |
| **`xrun_wrapper.sh`** | 工作站上的 `/home/lary/bin/xrun` 封裝腳本（修正 Xcelium 2409 執行路徑、自動引入 License、自動補齊 netlist 模組與引腳宣告、清理非必要 binding）。 |
| **`deploy_xrun_fix.py`** | 將修復後的 `xrun` 腳本自動部署並設定許可權至虛擬工作站的本機 Python 腳本。 |
| **`run_remote_simulation.py`** | 可在 Windows 端直接遠端觸發虛擬工作站執行該 cell 模擬的 Python 腳本。 |
| **`xrun.log`** | 完整模擬執行成功的日誌記錄（Transient 0~2ms，0 errors）。 |
| **`netlist.vams`** | 自動組裝並補充了 electrical 連接引腳宣告的完整 Verilog-AMS netlist。 |
| **`xrunArgs`** | Xcelium 執行的編譯與模擬參數設定檔。 |
| **`ie_card.scs`** | AMS Interface Element (IE) 介面轉換規則設定檔。 |
| **`amsControlSpectre.scs`** | Spectre 類比解算器暫態分析與參數控制檔。 |
| **`runSimulation.ksh`** | 工作站端負責執行模擬呼叫的 shell 腳本。 |
| **`expand.cfg`** | Hierarchy Editor 的設定結構檔。 |

## 修復摘要
1. 修正了 `/home/lary/bin/xrun` 中錯誤的 Xcelium 二進位檔路徑 (`/tools/cadence/XCELIUM/2409/tools/bin/xrun`)。
2. 補齊 `spectre_root`、`cds_root` 等符號連結，解決 `amsspice` 無法定位 Spectre 實體安裝與 License API 的問題。
3. 修正 `${IC_INVOKE_DIR}` 展開為 `/home/lary/project/BVU025/SCH`，使 Verilog-A 模組（`vaSAR6b` 與 `vaVDAC6b_FIXED`）正常編譯。
4. 移除非本電路所需的 `Buffer_DIG` binding 參數，消除 `NOUNIT` / `EXANCU` 報錯。
