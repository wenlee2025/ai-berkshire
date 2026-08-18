# AI Berkshire

AI 價值投資研究框架，專注於美股（US Equities）與台股（Taiwan Equities）的深度基本面與量化研究。

## Language

### 核心市場與標的

**US Equities (美股)**:
在美國主要交易所（NYSE、NASDAQ）掛牌交易的企業，以 SEC EDGAR 申報文件（10-K、10-Q、8-K）為一手信源，並以 Macrotrends、StockAnalysis 與 `tools/usstock_data.py` 為主要交叉驗證與快速取數源。
_Avoid_: 中概股、OTC 投機粉單

**Taiwan Equities (台股)**:
在台灣證券交易所（TWSE 上市）與證券櫃檯買賣中心（TPEx 上櫃）掛牌交易的企業，以公開資訊觀測站（MOPS）與 FinMind API (`tools/twstock_data.py`) 為數據核心，並以 Goodinfo 台灣股市資訊網為輔助交叉驗證源。
_Avoid_: 港股、A股、台股投機主力明牌

### 核心研究指標與規範

**Monthly Revenue (月營收)**:
台股法規強制每月 10 日前申報之上一月份營業收入數據，為判斷基本面與產業景氣拐點之最高頻、領先之官方驗證指標。
_Avoid_: 季度營收均攤、非官方預估月營收

**Cross Validation (雙源交叉驗證)**:
所有關鍵財務數據（營收、毛利率、營業利益率、歸母淨利、EPS、ROE 等）必須來自至少兩個獨立資料源進行精確比對，誤差率 ≤ 1% 為一致，1%~5% 標註差異，> 5% 必須查證原始財報。
_Avoid_: 單一信源直接引用、未註明估計值

**Market Cap Verification (市值手算驗算)**:
透過「最新收盤價 × 最新實際流通發行股數」進行精確算術驗算，防止因 ADR 換股比例、減資增資、不同幣別轉換所產生之市值幻覺。
_Avoid_: 盲信第三方網站顯示市值

**ADR Depositary Ratio (ADR 換股存託比例)**:
美股掛牌之海外存託憑證與原股之折算比例（如 1 TSM ADR = 5 股台股 2330 原始股）。在市值換算與本益比對比時必須進行換算，嚴禁直接以 ADR 股價乘上台股發行股數。
_Avoid_: 忽略存託比率直接跨市場比價

**Pre-adjusted Price (前復權價格)**:
以最新收盤價為基準回溯調整歷史股價，用於計算歷史波段漲幅、52 週高低區間與歷史本益比河流圖。
_Avoid_: 歷史序列混用未復權價格

### 量化動量、期望值與資金管理

**TTM Squeeze Indicator (TTM 波動率壓縮指標)**:
John Carter 經典動量指標。當布林帶（Bollinger Bands, 20 SMA / 2.0 SD）收縮至肯特納通道（Keltner Channels, 20 EMA / 1.5 ATR）內部時，代表波動率極致壓縮蓄勢（Squeeze On）；當布林帶重新擴張至肯特納通道外部時，代表動量釋放爆發（Squeeze Fired），搭配線性回歸斜率（Linear Regression Slope）判定多空突破方向。
_Avoid_: 忽視波動率壓縮盲目追高

**Expected Value per Trade (單筆交易數學期望值, EV)**:
評估單筆交易在統計意義上的期望獲利：\( EV = P_{win} \times \text{Win Amount} - (1 - P_{win}) \times \text{Loss Amount} \)。結合四大家基本面確定性評分與技術面停損停利點，確保每筆進場具備正期望值（\( EV > 0 \)）。
_Avoid_: 期望值為負的賭徒式下單

**Kelly Criterion & Half-Kelly Sizing (凱利公式與半凱利持倉引擎)**:
計算長期幾何增長率最大化的最佳資金配置比例：\( f^* = \frac{b \cdot p - (1 - p)}{b} \)。實盤交易中嚴格採用 **半凱利 (Half Kelly, \( \frac{1}{2} f^* \))** 或 **四分之一凱利 (Quarter Kelly, \( \frac{1}{4} f^* \))**，並施加單股持倉硬上限（如不超過總資產 20%），以避免極端回撤。
_Avoid_: 滿額全凱利梭哈、無停損邊界的無限制加倉

**Payoff Ratio / Reward-to-Risk (盈虧比 / 報償風險比, b)**:
潛在獲利空間與承擔停損風險之比值：\( b = \frac{\text{Target Price} - \text{Entry Price}}{\text{Entry Price} - \text{Stop Loss}} \)。價值投資與動量突破結合要求 \( b \ge 2.5:1 \)。
_Avoid_: 盈虧比小於 1.5:1 的不對稱劣勢交易

### 系統架構與進階分析模型

**SQLite Data Cache (本地數據快取層)**:
透過 Python 標準庫 `sqlite3` 構建的零外部依賴本地資料儲存庫（`data/berkshire.db`），實現行情、月營收與 5 年財報數據的 TTL 緩存，解決 API 頻率限制並提供毫秒級查詢。
_Avoid_: 無快取高頻輪詢、快取過期未標註

**Peer Comparison Matrix (同業橫向對比矩陣)**:
在同一細分產業（如散熱、晶圓代工、伺服器代工、CCL、IC 載板）中，對多家龍頭企業的毛利率、營益率、ROE、四大家評分與估值進行多維度橫向對比，揭示真實產業競爭力與定價權。
_Avoid_: 跨不相關產業無意義比價

**Portfolio Allocation Simulator (投資組合配置模擬器)**:
根據巴菲特與李錄的集中投資組合紀律，由投資人配置多檔標的之自訂權重，即時試算整個投資組合的加權預期 ROE、前瞻本益比、股息殖利率與綜合護城河評分。
_Avoid_: 過度分散投資、忽略單檔權重上限

**Thesis Drift Pipeline (投資論文漂移監控管線)**:
自動化比對最新月營收與季度法說會獲利數據，偵測企業基本面與歷史承諾之偏差，在營收拐點或承諾跳票時自動觸發警報與重審。
_Avoid_: 忽視事實變化的靜態論文追蹤

**Multi-Model Valuation Matrix (多模型產業適配估值矩陣)**:
根據產業生命週期與商業模式特性（成長型、強週期型、重資產代工型），結合 FCF 反向 DCF、P/B 河流圖、EV/EBITDA 與葛拉漢淨流動資產 (NCAV)，提供統計信賴度估值區間。
_Avoid_: 單一 P/E 公式套用全產業週期

**MarketDataEngine (統一市場數據引擎 / 深度模組)**:
遵循深度模組（Deep Module: 小介面 + 大實作）架構模式，對外部調用者（CLI、Dashboard、監控管線）僅呈現極簡介面（`get_quote`、`get_revenue`、`get_full_bundle`），內部高度封裝本地 SQLite 快取管理、雙源交叉驗證（誤差 ≤ 1%）、TTM Squeeze 4 態計算、半凱利持倉量化與跨市場降級適配。
_Avoid_: 調用端自行組織多工具取數、無結構裸 dict 散落傳遞
