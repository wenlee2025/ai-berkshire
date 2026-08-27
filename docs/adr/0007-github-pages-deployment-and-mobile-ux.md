# ADR 0007: GitHub Pages 雲端對外部署、行動端響應式適配與每日自動更新管線 (GitHub Pages Deployment, Mobile UX & Daily CI/CD Pipeline)

## 狀態
已通過 (Accepted)

## 上下文 (Context)
AI Berkshire 的投研 Dashboard 原本僅於本機執行（`http://localhost:8080`），外部讀者或使用者無法透過手機與不同電腦進行遠端查閱。
為了將 Dashboard 轉化為免伺服器維護、高可用、支援全裝置瀏覽的對外公開站點（預計公開網址：`https://wenlee2025.github.io/ai-berkshire/`），需要解決以下架構問題：
1. **靜態託管架構選型**：如何將純前端 SPA 零摩擦部署至 GitHub Pages，且不破壞現有倉庫結構。
2. **行動端響應式體驗 (Mobile UX)**：如何讓手機（iOS/Android）在直式螢幕下流暢瀏覽 37 檔標的總表、雙向排序、TTM Squeeze 狀態與凱利持倉計算器。
3. **數據生命週期自動化**：如何免除手動本地運算，在每日台股收盤後自動獲取最新數據並刷新線上網站。

## 決策 (Decision)

### 1. 採用現代 GitHub Actions 官方部署工作流 (`deploy-pages.yml`)
- 使用 `actions/upload-pages-artifact@v3` 與 `actions/deploy-pages@v4`。
- 直接將 `dashboard/` 資料夾作為 Pages 構件打包發布，無需複製至根目錄或維護冗餘的 `docs/` 資料夾。
- 只要推送（`git push`）至 `main` 分支即自動觸發 0 停機熱更新。

### 2. 深度行動端響應式適配 (`dashboard/style.css`)
- **水平導覽滑動**：針對頁簽區 (`.tabs-nav`)、快捷標籤 (`.quick-tags`)、篩選按鈕 (`.screener-filter-group`) 與板塊選擇 (`.peer-selector-group`) 採用 `-webkit-overflow-scrolling: touch` 隱藏滾動條平滑滑動。
- **網格自適應摺疊**：電腦端 2 欄 / 4 欄佈局在小於 768px 螢幕自動轉為 1 欄垂直卡片流。
- **固定首欄表格**：37 檔全景總表首欄「代碼/名稱」設定 `position: sticky; left: 0;`，手機橫向滑動時代碼始終固定可見。
- **觸控目標優化**：所有輸入框、下拉選單與按鈕設置最小觸控高度 $\ge 40\text{px}$。

### 3. 盤後定時自動化更新管線 (`daily-update.yml`)
- 配置 GitHub Actions 定時排程（Cron: `30 8 * * 1-5`，即台灣時間週一至週五 16:30 盤後）。
- 自動調用 `scripts/generate_full_37_dataset.py` 重新生成 37 檔最新報價、TTM Squeeze 與凱利持倉。
- 若數據有變動則自動透過 GitHub Actions Bot 提交並推送至 `main`，隨後自動觸發網頁重新部署。

## 後果 (Consequences)
- **優勢**：
  - 真正實現 100% 雲端全自動化（Serverless & Zero-maintenance），無需本地電腦開機即可 24 小時服務全球訪客。
  - 手機端體驗大幅躍升，隨時隨地一鍵查閱標的與進行凱利持倉量化試算。
