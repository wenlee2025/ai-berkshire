# ADR 0004: 結合 TTM Squeeze 策略、數學期望值與凱利公式之個股量化持倉決策架構

## 狀態
已通過 (Accepted)

## 上下文 (Context)
在價值投資體系中，巴菲特與芒格解決了「買什麼公司（優質護城河、好管理層）」與「什麼價格買（安全邊際）」的核心問題。然而，在實盤交易中，投資人常面臨以下實踐痛點：
1. **進場時機痛點 (Timing & Momentum)**：優質標的可能處於長達數月的低波動盤整期，過早重倉會耗損資金時間成本；
2. **數學期望值不明 (Unquantified Edge)**：缺乏對單筆交易勝率（\( p \)）與盈虧比（\( b \)）的精確量化計算；
3. **倉位管理隨意 (Arbitrary Sizing)**：憑感覺下單，在勝率高的機會下注過小，在勝率不確定的標的下注過大。

## 決策 (Decision)

### 1. 引入 TTM Squeeze 波動率壓縮指標作為時機過濾器 (Timing Trigger)
- **指標定義**：
  - 布林帶 (Bollinger Bands)：20 週期 SMA，2.0 倍標準差 (SD)
  - 肯特納通道 (Keltner Channels)：20 週期 EMA，1.5 倍真實波幅 (ATR)
  - 動量振盪器 (Momentum)：20 週期收盤價線性回歸斜率 (Linear Regression Slope)
- **四態狀態機 (4-State Machine)**：
  - 🟡 **Squeeze On (強烈壓縮蓄勢)**：BB 進入 KC 內部，波動率處於極限收縮，醞釀爆發。
  - 🟢 **Squeeze Fired Long (多頭突破釋放)**：BB 擴張出 KC 外部且動量為正，波段最佳買點。
  - 🔴 **Squeeze Fired Short (空頭跌破釋放)**：BB 擴張出 KC 外部且動量為負，避險防守。
  - ⚪ **No Squeeze (常態波動擴張)**：常態震盪整理。

### 2. 建立基本面 + 技術面混合數學期望值模型 (EV Model)
- **單筆期望值**：
  \[
  EV = P_{win} \times (\text{Target Price} - \text{Entry Price}) - (1 - P_{win}) \times (\text{Entry Price} - \text{Stop Loss})
  \]
- **勝率 \( P_{win} \)** 由「四大家綜合評分（質量確信度）」與「歷史 Squeeze 突破勝率」動態加權（基準 55%，高護城河標的加權至 65%~75%）。
- **盈虧比 \( b \)** 嚴格要求 \( b \ge 2.5:1 \)，以確保正期望值（\( EV > 0 \)）。

### 3. 採用半凱利公式 (Half Kelly) 與硬性持倉護欄 (Position Sizing Guardrails)
- **理論最優倉位 (Full Kelly)**：
  \[
  f^* = \frac{b \cdot p - (1 - p)}{b}
  \]
- **實盤執行倉位 (Half Kelly)**：
  \[
  f_{\text{actual}} = \min\left( \frac{1}{2} f^*, \, 20\% \right)
  \]
  - 單一個股最大倉位不得超過總資金的 **20%**（週期股 **12%**）。
  - 單筆交易最大停損金額不得超過總帳戶淨值的 **1.5%~2.0%**。

### 4. Dashboard 全面升級 TTM Squeeze 與凱利持倉引擎
- 新增專屬 **「⚡ TTM Squeeze 與凱利持倉引擎」 Tab**。
- 提供即時壓縮指示燈、動量方向直方圖與壓縮天數監控。
- 內建互動式資金配置計算器：輸入總資產與當前價格，即時計算最佳買進股數與建議資金占比。
- 在「📋 37 檔全景看板」新增 TTM Squeeze 狀態燈號標籤。

## 後果 (Consequences)
- **優勢**：
  - 實現「四大家基本面（選股） + TTM Squeeze（擇時） + 凱利公式（風控）」的三位一體機構級體系。
  - 徹底消除下單時的隨意性與情緒干擾，所有倉位皆具備嚴格數學期望值依據。
- **限制**：
  - TTM Squeeze 屬於順勢突破策略，在極端黑天鵝事件或假突破行情下仍需嚴格執行 \( 2 \times ATR \) 停損紀律。
