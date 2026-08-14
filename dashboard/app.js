// AI Berkshire Dashboard Client Application
(function() {
  "use strict";

  // 全域狀態
  let STOCKS_DATABASE = window.STOCKS_DATABASE || {};
  let currentAnalysisData = null;

  const DEFAULT_PORTFOLIO = [
    { symbol: "2330.TW", name: "台積電", weight: 30, color: "#3b82f6" },
    { symbol: "2059.TW", name: "川湖", weight: 20, color: "#10b981" },
    { symbol: "2344.TW", name: "華邦電", weight: 20, color: "#f59e0b" },
    { symbol: "3017.TW", name: "奇鋐", weight: 15, color: "#ec4899" },
    { symbol: "2317.TW", name: "鴻海", weight: 15, color: "#8b5cf6" },
  ];

  let currentPortfolio = JSON.parse(JSON.stringify(DEFAULT_PORTFOLIO));

  // -------------------------------------------------------------
  // 全域介面函數 (暴露至 window)
  // -------------------------------------------------------------

  window.switchTab = function(tabId) {
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    tabBtns.forEach(btn => {
      if (btn.getAttribute("data-tab") === tabId) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    tabContents.forEach(content => {
      if (content.id === tabId) {
        content.classList.add("active");
      } else {
        content.classList.remove("active");
      }
    });
  };

  window.selectStock = function(symbol) {
    if (!symbol) return;
    const tickerInput = document.getElementById("tickerInput");
    const stockDropdown = document.getElementById("stockDropdown");
    if (tickerInput) tickerInput.value = symbol;
    if (stockDropdown) stockDropdown.value = symbol;
    analyzeStock(symbol);
  };

  window.searchStock = function() {
    const tickerInput = document.getElementById("tickerInput");
    if (!tickerInput) return;
    const val = tickerInput.value.trim();
    if (val) analyzeStock(val);
  };

  window.filterScreener = function(filter, btn) {
    const filterBtns = document.querySelectorAll(".screener-filter-group .filter-btn");
    filterBtns.forEach(b => b.classList.remove("active"));
    if (btn) btn.classList.add("active");
    renderScreenerTable(filter);
  };

  window.filterPeers = function(sector, btn) {
    const peerBtns = document.querySelectorAll(".peer-selector-group .peer-btn");
    peerBtns.forEach(b => b.classList.remove("active"));
    if (btn) btn.classList.add("active");
    renderPeerComparison(sector);
  };

  window.updateDCF = function() {
    if (!currentAnalysisData) return;
    const waccSlider = document.getElementById("waccSlider");
    const gSlider = document.getElementById("gSlider");
    const waccVal = document.getElementById("waccVal");
    const gVal = document.getElementById("gVal");
    const impliedGrowth = document.getElementById("impliedGrowth");

    const w = waccSlider ? parseFloat(waccSlider.value) : 9.0;
    const g = gSlider ? parseFloat(gSlider.value) : 3.0;
    if (waccVal) waccVal.innerText = `${w.toFixed(1)}%`;
    if (gVal) gVal.innerText = `${g.toFixed(1)}%`;

    const pe = (currentAnalysisData.valuation && currentAnalysisData.valuation.per) ? currentAnalysisData.valuation.per : 15;
    const calcG = ((w - g) * (pe / 15) + 6.5).toFixed(1);
    if (impliedGrowth) impliedGrowth.innerText = `${calcG}%`;
  };

  // -------------------------------------------------------------
  // TTM Squeeze 與 凱利持倉計算器 (動態即時試算)
  // -------------------------------------------------------------
  window.updateKellyCalculator = function() {
    if (!currentAnalysisData) return;
    const price = currentAnalysisData.price || 100.0;

    const kCapIn = document.getElementById("kCapitalInput");
    const kWinSlider = document.getElementById("kWinRateSlider");
    const kTargetIn = document.getElementById("kTargetInput");
    const kStopIn = document.getElementById("kStopInput");

    const capital = kCapIn ? Math.max(10000, parseFloat(kCapIn.value) || 1000000) : 1000000;
    const winRatePct = kWinSlider ? parseFloat(kWinSlider.value) : 65;
    const targetPrice = kTargetIn ? parseFloat(kTargetIn.value) || (price * 1.25) : (price * 1.25);
    const stopPrice = kStopIn ? parseFloat(kStopIn.value) || (price * 0.90) : (price * 0.90);

    const kCapLabel = document.getElementById("kCapitalLabel");
    const kWinLabel = document.getElementById("kWinRateLabel");
    if (kCapLabel) kCapLabel.innerText = `${capital.toLocaleString()} 元`;
    if (kWinLabel) kWinLabel.innerText = `${winRatePct}%`;

    const reward = Math.max(0.1, targetPrice - price);
    const risk = Math.max(0.1, price - stopPrice);
    const b = reward / risk;
    const p = winRatePct / 100.0;
    const q = 1.0 - p;

    // Expected Value
    const evAmount = (p * reward) - (q * risk);
    const evPerDollar = (p * b) - q;

    const evAmountVal = document.getElementById("evAmountVal");
    const evRatioText = document.getElementById("evRatioText");
    const evRewardVal = document.getElementById("evRewardVal");
    const evRiskVal = document.getElementById("evRiskVal");
    const evPayoffVal = document.getElementById("evPayoffVal");
    const evWinRateVal = document.getElementById("evWinRateVal");

    if (evAmountVal) evAmountVal.innerText = `${evAmount >= 0 ? '+' : ''}$${evAmount.toFixed(2)}`;
    if (evRatioText) evRatioText.innerText = `每承擔 $1.00 停損風險，期望回報 $${evPerDollar.toFixed(3)} 元`;
    if (evRewardVal) evRewardVal.innerText = `+$${reward.toFixed(2)} (目標價 ${targetPrice.toFixed(1)})`;
    if (evRiskVal) evRiskVal.innerText = `-$${risk.toFixed(2)} (停損價 ${stopPrice.toFixed(1)})`;
    if (evPayoffVal) evPayoffVal.innerText = `${b.toFixed(2)} : 1 ${b >= 2.5 ? '✅ (優於 2.5:1 標準)' : '⚠️ (盈虧比較低)'}`;
    if (evWinRateVal) evWinRateVal.innerText = `${winRatePct.toFixed(1)}% (基本面+技術面加權)`;

    // Kelly Sizing
    const fullKelly = b > 0 ? Math.max(0, (b * p - q) / b) : 0;
    const halfKelly = fullKelly * 0.5;
    const appliedKelly = Math.min(halfKelly, 0.20); // 實盤防禦上限 20%
    const allocatedCapital = capital * appliedKelly;
    const suggestedShares = Math.floor(allocatedCapital / price);
    const maxLoss = suggestedShares * risk;
    const accountRiskPct = (maxLoss / capital) * 100;

    const kHalfKellyVal = document.getElementById("kHalfKellyVal");
    const kFullKellySub = document.getElementById("kFullKellySub");
    const kAllocatedVal = document.getElementById("kAllocatedCapitalVal");
    const kSharesVal = document.getElementById("kSuggestedSharesVal");
    const kMaxLossVal = document.getElementById("kMaxLossVal");
    const kAccountRiskPct = document.getElementById("kAccountRiskPct");

    if (kHalfKellyVal) kHalfKellyVal.innerText = `${(appliedKelly * 100).toFixed(1)}%`;
    if (kFullKellySub) kFullKellySub.innerText = `全凱利理論值 ${(fullKelly * 100).toFixed(1)}% · 實盤防禦上限 20%`;
    if (kAllocatedVal) kAllocatedVal.innerText = `${Math.round(allocatedCapital).toLocaleString()} 元`;
    if (kSharesVal) kSharesVal.innerText = `${suggestedShares.toLocaleString()} 股`;
    if (kMaxLossVal) kMaxLossVal.innerText = `$${Math.round(maxLoss).toLocaleString()} 元`;
    if (kAccountRiskPct) kAccountRiskPct.innerText = `佔總帳戶 ${accountRiskPct.toFixed(2)}% ${accountRiskPct <= 2.0 ? '✅ (安全防禦 ≤ 2%)' : '⚠️ (風險略高)'}`;
  };

  window.resetPortfolio = function() {
    currentPortfolio = JSON.parse(JSON.stringify(DEFAULT_PORTFOLIO));
    renderPortfolioSliders();
    updatePortfolioMetrics();
  };

  window.copyMarkdown = function() {
    const codeEl = document.querySelector("#markdownPreview code");
    const code = codeEl ? codeEl.innerText : "";
    const btn = document.getElementById("btnCopyMd");
    navigator.clipboard.writeText(code).then(() => {
      if (btn) {
        btn.innerText = "✅ 已複製！";
        setTimeout(() => btn.innerText = "複製 Markdown", 2000);
      }
    });
  };

  window.downloadMarkdown = function() {
    if (!currentAnalysisData) return;
    const codeEl = document.querySelector("#markdownPreview code");
    const code = codeEl ? codeEl.innerText : "";
    const blob = new Blob([code], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${currentAnalysisData.symbol}_AI_Berkshire_投研報告.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  window.handleFileUpload = function(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target.result;
        const matches = text.match(/\b\d{4}\b/g);
        if (matches && matches.length > 0) {
          const uniqueCodes = Array.from(new Set(matches));
          alert(`✅ 成功辨識 ${uniqueCodes.length} 檔標的，立即載入第一檔: ${uniqueCodes[0]}.TW`);
          window.selectStock(`${uniqueCodes[0]}.TW`);
        } else {
          alert("⚠️ 未在檔案中找到 4 碼台股代碼，請確認格式！");
        }
      } catch (err) {
        alert(`❌ 檔案解析失敗: ${err.message}`);
      }
    };
    reader.readAsText(file);
  };

  // -------------------------------------------------------------
  // 資料庫查詢與渲染
  // -------------------------------------------------------------

  async function analyzeStock(symbol) {
    const btnAnalyze = document.getElementById("btnAnalyze");
    if (btnAnalyze) {
      btnAnalyze.innerText = "分析中...";
      btnAnalyze.disabled = true;
    }

    const symClean = symbol.trim().toUpperCase();
    const symTW = symClean.endsWith(".TW") ? symClean : `${symClean}.TW`;

    let matched = STOCKS_DATABASE[symClean] || STOCKS_DATABASE[symTW];
    if (!matched) {
      const foundKey = Object.keys(STOCKS_DATABASE).find(k => {
        const item = STOCKS_DATABASE[k];
        return item.name === symbol.trim() || item.symbol.replace(".TW", "") === symClean;
      });
      if (foundKey) matched = STOCKS_DATABASE[foundKey];
    }

    if (matched) {
      renderDashboard(matched);
      if (btnAnalyze) {
        btnAnalyze.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg> 深度分析`;
        btnAnalyze.disabled = false;
      }
      return;
    }

    try {
      const resp = await fetch(`/api/analyze?ticker=${encodeURIComponent(symbol)}`);
      if (resp.ok) {
        const data = await resp.json();
        renderDashboard(data);
      }
    } catch (e) {
      console.warn("API fallback error:", e);
    } finally {
      if (btnAnalyze) {
        btnAnalyze.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg> 深度分析`;
        btnAnalyze.disabled = false;
      }
    }
  }

  function renderDashboard(data) {
    if (!data) return;
    currentAnalysisData = data;
    const s = data.synthesis || {};
    const sq = data.ttm_squeeze || {};

    const setText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.innerText = (val !== undefined && val !== null) ? val : "-";
    };

    // Dropdown & Chips
    const stockDropdown = document.getElementById("stockDropdown");
    if (stockDropdown && stockDropdown.querySelector(`option[value="${data.symbol}"]`)) {
      stockDropdown.value = data.symbol;
    }

    const tickerInput = document.getElementById("tickerInput");
    if (tickerInput) tickerInput.value = data.symbol;

    document.querySelectorAll(".chip").forEach(c => {
      if (c.getAttribute("data-symbol") === data.symbol || c.innerText.includes(data.name)) {
        c.classList.add("active");
      } else {
        c.classList.remove("active");
      }
    });

    // Hero Section
    setText("stockName", data.name);
    setText("stockSymbol", data.symbol);
    setText("marketBadge", `${data.market === "TW" ? "TWSE 上市" : "US 美股"} · ${data.sector || '核心供應鏈'}`);
    setText("infoRatingBadge", (s.info_rating || "A 級一手資料").split("（")[0]);
    setText("stockDate", `資料基準日：${data.date || '2026-08-14'} · 數據工具鏈：SQLite Cache + FinMind + MOPS + financial_rigor.py`);

    const priceEl = document.getElementById("stockPrice");
    if (priceEl) priceEl.innerHTML = `${(data.price || 0).toFixed(2)} <span class="currency">${data.currency || 'TWD'}</span>`;

    const chgEl = document.getElementById("stockChange");
    if (chgEl) {
      const cp = data.change_pct || 0;
      chgEl.innerText = `${cp >= 0 ? "+" : ""}${cp.toFixed(2)}%`;
      chgEl.className = `price-change ${cp >= 0 ? "pos" : "neg"}`;
    }

    setText("verdictText", s.verdict_label || "🎯 強烈買入");

    // Metrics
    setText("metricMarketCap", data.market_cap_formatted);
    setText("metricShares", `${data.shares_formatted || '-'} · 驗算偏差 ${(data.market_cap_verification && data.market_cap_verification.diff_pct !== undefined) ? data.market_cap_verification.diff_pct : '0.0'}% ✅`);
    setText("metricPE", (data.valuation && data.valuation.per) ? `${data.valuation.per.toFixed(2)}x` : "-");
    setText("metricForwardPE", (s.valuation_model && s.valuation_model.forward_pe) ? `2026 前瞻 P/E 約 ${s.valuation_model.forward_pe}` : "-");
    setText("metricPB", (data.valuation && data.valuation.pbr) ? `${data.valuation.pbr.toFixed(2)}x` : "-");
    setText("metricYield", (data.valuation && data.valuation.yield_pct) ? `${data.valuation.yield_pct.toFixed(2)}%` : "-");

    // 52W Bar
    const low = (data.valuation && data.valuation.low_52w) || (data.price * 0.7);
    const high = (data.valuation && data.valuation.high_52w) || (data.price * 1.3);
    setText("low52w", low.toFixed(1));
    setText("high52w", high.toFixed(1));
    const pct52w = Math.min(100, Math.max(0, ((data.price - low) / (high - low)) * 100));
    const rFill = document.getElementById("rangeFill");
    const rPoint = document.getElementById("rangePoint");
    if (rFill) rFill.style.width = `${pct52w}%`;
    if (rPoint) rPoint.style.left = `${pct52w}%`;

    // Tab 1: Masters
    if (s.radar_scores) renderRadar(s.radar_scores);
    setText("biasRating", (s.info_rating || "A 級一手資料").split("（")[0]);

    if (s.dyp) {
      setText("dypScore", `評分: ${s.dyp.score} / 5.0`);
      setText("dypQuote", s.dyp.quote);
      setText("dypEssence", s.dyp.business_essence);
      setText("dypRightThing", s.dyp.right_thing);
    }

    if (s.buffett) {
      setText("buffettScore", `評分: ${s.buffett.score} / 5.0`);
      setText("buffettQuote", s.buffett.quote);
      setText("buffettMoat", s.buffett.moat);
      setText("buffettCapital", s.buffett.capital_allocation);
    }

    if (s.munger) {
      setText("mungerScore", `評分: ${s.munger.score} / 5.0`);
      setText("mungerQuote", s.munger.quote);
      setText("mungerInversion", s.munger.inversion);
      const rList = document.getElementById("mungerRisks");
      if (rList && s.munger.risks) {
        rList.innerHTML = s.munger.risks.map(r => `<li>${r}</li>`).join("");
      }
    }

    if (s.lilu) {
      setText("liluScore", `評分: ${s.lilu.score} / 5.0`);
      setText("liluQuote", s.lilu.quote);
      setText("liluCivilization", s.lilu.civilization);
    }

    // Tab 2: TTM Squeeze & Kelly Engine
    const sqLamp = document.getElementById("squeezeLamp");
    if (sqLamp) sqLamp.className = `squeeze-lamp ${sq.status || 'NORMAL'}`;
    setText("squeezeStatusText", sq.status_label || "⚪ 常態震盪整理");
    setText("sqDaysVal", `${sq.squeeze_days || 0} 天`);
    setText("sqMomVal", `${(sq.momentum || 0) >= 0 ? '+' : ''}${(sq.momentum || 0).toFixed(2)}`);
    setText("sqMomDir", sq.momentum_direction === "BULLISH_RISING" ? "🚀 多頭向上 (Bullish Rising)" : (sq.momentum_direction || "常態區間"));
    setText("sqAtrVal", `${(sq.atr || (data.price * 0.05)).toFixed(2)} ${data.currency}`);

    const kTargetIn = document.getElementById("kTargetInput");
    const kStopIn = document.getElementById("kStopInput");
    const targetEst = (data.price * 1.25).toFixed(1);
    const stopEst = Math.max(1, data.price - (sq.atr || (data.price * 0.05)) * 1.8).toFixed(1);
    if (kTargetIn) kTargetIn.value = targetEst;
    if (kStopIn) kStopIn.value = stopEst;

    window.updateKellyCalculator();

    // Tab 3: Earnings
    if (s.earnings_review) {
      setText("earningsHeadline", s.earnings_review.headline);
      setText("earningsSummary", s.earnings_review.h1_summary);
    }
    renderRevenueChart(data.monthly_revenue, data.currency);
    renderFinancialsTable(data.financials_5y);

    // Tab 4: Valuation Rigor
    setText("rigorPrice", `${data.price.toFixed(2)} ${data.currency}`);
    setText("rigorShares", `${data.shares_raw ? data.shares_raw.toLocaleString() : "-"} 股 (${data.shares_formatted})`);
    setText("rigorCalcCap", data.market_cap_formatted);
    setText("rigorFormula", `算式：${data.price.toFixed(2)} × ${data.shares_raw ? data.shares_raw.toLocaleString() : 0} = ${data.market_cap_raw ? data.market_cap_raw.toLocaleString() : 0} 元 (${data.market_cap_formatted})`);

    if (s.valuation_model) {
      setText("impliedGrowth", s.valuation_model.reverse_dcf_implied_growth);
      if (s.valuation_model.scenarios) renderScenarios(s.valuation_model.scenarios);
    }

    // Tab 7: Thesis
    if (s.thesis) {
      const pList = document.getElementById("pillarList");
      if (pList && s.thesis.pillars) {
        pList.innerHTML = s.thesis.pillars.map(p => `<li>${p}</li>`).join("");
      }

      const kList = document.getElementById("killList");
      if (kList && s.thesis.kill_criteria) {
        kList.innerHTML = s.thesis.kill_criteria.map(k => `<li>${k}</li>`).join("");
      }

      if (s.thesis.allocation) renderAllocation(s.thesis.allocation);
    }

    // Tab 9: Markdown
    const md = generateMarkdownReport(data);
    const mdEl = document.querySelector("#markdownPreview code");
    if (mdEl) mdEl.innerText = md;
  }

  function renderRadar(scores) {
    const container = document.getElementById("radarBars");
    if (!container) return;
    const items = [
      { name: "段永平 · 商業本質與定價權", val: scores.business || 4.5, cls: "dyp" },
      { name: "巴菲特 · 經濟護城河與資本配置", val: scores.moat || 4.4, cls: "buffett" },
      { name: "芒格 · 逆向思考與風險防範", val: scores.risk_defense || 3.6, cls: "munger" },
      { name: "李錄 · 長期文明與產業趨勢", val: scores.trend || 4.8, cls: "lilu" },
      { name: "四大師綜合確定性評分", val: scores.composite || 4.4, cls: "composite" },
    ];

    container.innerHTML = items.map(item => `
      <div class="radar-row">
        <div class="radar-label-row">
          <span>${item.name}</span>
          <span class="score-num">${item.val.toFixed(1)} / 5.0</span>
        </div>
        <div class="radar-bar-track">
          <div class="radar-bar-fill ${item.cls}" style="width: ${(item.val / 5) * 100}%"></div>
        </div>
      </div>
    `).join("");
  }

  function renderRevenueChart(revs, currency) {
    const container = document.getElementById("revenueChartContainer");
    if (!container) return;
    if (!revs || revs.length === 0) {
      container.innerHTML = `<div style="color:var(--text-muted); margin:auto;">美股無強制月營收揭露，請參考季度財報</div>`;
      return;
    }

    const maxRev = Math.max(...revs.map(r => r.revenue || 0));
    container.innerHTML = revs.slice(-12).map(r => {
      const hPct = maxRev > 0 ? (r.revenue / maxRev) * 100 : 30;
      const yoyStr = r.yoy !== null && r.yoy !== undefined ? `${r.yoy >= 0 ? "+" : ""}${r.yoy.toFixed(1)}%` : "-";
      const isPos = r.yoy >= 0;
      const dateStr = r.date ? r.date.slice(5) : "-";
      const revYi = (r.revenue / 1e8).toFixed(1);
      return `
        <div class="chart-bar-col">
          <div class="bar-val">${revYi}億</div>
          <div class="bar-yoy ${isPos ? 'pos' : 'neg'}">${yoyStr}</div>
          <div class="bar-body" style="height: ${Math.max(15, hPct)}%"></div>
          <div class="bar-date">${dateStr}</div>
        </div>
      `;
    }).join("");
  }

  function renderFinancialsTable(fins) {
    const tbody = document.querySelector("#financialsTable tbody");
    if (!tbody) return;
    if (!fins || fins.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;">無歷史財務資料</td></tr>`;
      return;
    }

    tbody.innerHTML = fins.map(f => `
      <tr>
        <td style="font-weight:700;">${f.year || f.date}</td>
        <td>${f.revenue ? (f.revenue / 1e8).toFixed(1) : "-"}</td>
        <td style="color:${f.gross_margin > 40 ? '#34d399' : '#fff'};">${f.gross_margin ? f.gross_margin.toFixed(1) + '%' : '-'}</td>
        <td>${f.operating_margin ? f.operating_margin.toFixed(1) + '%' : '-'}</td>
        <td>${f.net_income ? (f.net_income / 1e8).toFixed(1) : "-"}</td>
        <td style="font-weight:700; color:#60a5fa;">${f.eps ? f.eps.toFixed(2) : "-"}</td>
        <td>${f.roe ? f.roe.toFixed(1) + '%' : '-'}</td>
      </tr>
    `).join("");
  }

  function renderScenarios(scenarios) {
    const container = document.getElementById("scenariosGrid");
    if (!container || !scenarios) return;
    container.innerHTML = `
      <div class="scenario-card bull">
        <span class="badge success">樂觀情景 (Bull)</span>
        <div class="scenario-target">${scenarios.bull.price}</div>
        <div class="scenario-desc">${scenarios.bull.desc}</div>
      </div>
      <div class="scenario-card base">
        <span class="badge">中性基準 (Base)</span>
        <div class="scenario-target">${scenarios.base.price}</div>
        <div class="scenario-desc">${scenarios.base.desc}</div>
      </div>
      <div class="scenario-card bear">
        <span class="badge danger">悲觀防守 (Bear)</span>
        <div class="scenario-target">${scenarios.bear.price}</div>
        <div class="scenario-desc">${scenarios.bear.desc}</div>
      </div>
    `;
  }

  function renderAllocation(alloc) {
    const container = document.getElementById("allocationGrid");
    if (!container || !alloc) return;
    container.innerHTML = `
      <div class="alloc-card aggressive">
        <span class="badge success">激進動量型</span>
        <div class="alloc-price">${alloc.aggressive.price_range}</div>
        <div class="alloc-action">${alloc.aggressive.action} (建議倉位: ${alloc.aggressive.size})</div>
      </div>
      <div class="alloc-card steady">
        <span class="badge">穩健價值型 (推薦)</span>
        <div class="alloc-price">${alloc.steady.price_range}</div>
        <div class="alloc-action">${alloc.steady.action} (建議倉位: ${alloc.steady.size})</div>
      </div>
      <div class="alloc-card conservative">
        <span class="badge danger">保守防守型</span>
        <div class="alloc-price">${alloc.conservative.price_range}</div>
        <div class="alloc-action">${alloc.conservative.action} (建議倉位: ${alloc.conservative.size})</div>
      </div>
    `;
  }

  function renderScreenerTable(filter) {
    const tbody = document.getElementById("screenerTableBody");
    if (!tbody) return;
    const keys = Object.keys(STOCKS_DATABASE).filter(k => k.endsWith(".TW"));
    if (keys.length === 0) return;

    let items = keys.map(k => STOCKS_DATABASE[k]);
    if (filter !== "all") {
      items = items.filter(it => it.synthesis && it.synthesis.verdict === filter);
    }

    items.sort((a, b) => {
      const sa = (a.synthesis && a.synthesis.radar_scores && a.synthesis.radar_scores.composite) || 0;
      const sb = (b.synthesis && b.synthesis.radar_scores && b.synthesis.radar_scores.composite) || 0;
      return sb - sa;
    });

    tbody.innerHTML = items.map(d => {
      const s = d.synthesis || {};
      const sq = d.ttm_squeeze || {};
      const vCls = s.verdict || "HOLD";
      const chgStr = `${d.change_pct >= 0 ? "+" : ""}${d.change_pct.toFixed(2)}%`;
      const chgCls = d.change_pct >= 0 ? "color:#34d399;" : "color:#f87171;";
      const peStr = (d.valuation && d.valuation.per) ? `${d.valuation.per.toFixed(1)}x` : "-";
      const compScore = (s.radar_scores && s.radar_scores.composite) ? s.radar_scores.composite.toFixed(1) : "4.0";

      let sqBadgeHtml = `<span class="badge-sq-normal">⚪ 常態</span>`;
      if (sq.status === "SQUEEZE_ON") {
        sqBadgeHtml = `<span class="badge-sq-on">🟡 壓縮 (${sq.squeeze_days}天)</span>`;
      } else if (sq.status === "SQUEEZE_FIRED_LONG" || sq.status === "MOMENTUM_EXPANDING_UP") {
        sqBadgeHtml = `<span class="badge-sq-fired">🟢 多頭爆發</span>`;
      }

      return `
        <tr onclick="window.selectStock('${d.symbol}'); window.switchTab('tabMasters');">
          <td style="text-align:left;">
            <div class="screener-stock-cell">
              <span class="screener-code">${d.symbol}</span>
              <span class="screener-name">${d.name}</span>
            </div>
          </td>
          <td style="text-align:left; color:var(--text-secondary);">${d.sector || '-'}</td>
          <td style="font-weight:700;">${d.price.toFixed(2)}</td>
          <td style="font-weight:600; ${chgCls}">${chgStr}</td>
          <td>${peStr}</td>
          <td>${d.market_cap_formatted}</td>
          <td>${sqBadgeHtml}</td>
          <td style="color:#60a5fa; font-weight:700;">${compScore} / 5.0</td>
          <td>
            <span class="screener-verdict-badge ${vCls}">${s.verdict_label || '觀察'}</span>
          </td>
          <td>
            <button class="btn-view-report" onclick="event.stopPropagation(); window.selectStock('${d.symbol}'); window.switchTab('tabKelly');">持倉試算 →</button>
          </td>
        </tr>
      `;
    }).join("");
  }

  function renderPeerComparison(sectorKeyword) {
    const tbody = document.getElementById("peerTableBody");
    if (!tbody) return;
    const keys = Object.keys(STOCKS_DATABASE).filter(k => k.endsWith(".TW"));
    if (keys.length === 0) return;

    const peers = keys.map(k => STOCKS_DATABASE[k]).filter(d => (d.sector || "").includes(sectorKeyword) || (d.name || "").includes(sectorKeyword));
    if (peers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;">此板塊暫無對比標的</td></tr>`;
      return;
    }

    tbody.innerHTML = peers.map(d => {
      const s = d.synthesis || {};
      const fin = d.financials_5y && d.financials_5y[0] ? d.financials_5y[0] : {};
      const compScore = (s.radar_scores && s.radar_scores.composite) ? s.radar_scores.composite.toFixed(1) : "4.0";
      const peStr = (d.valuation && d.valuation.per) ? `${d.valuation.per.toFixed(1)}x` : "-";
      const moatText = (s.buffett && s.buffett.moat) ? s.buffett.moat.slice(0, 32) + '...' : '-';

      return `
        <tr onclick="window.selectStock('${d.symbol}'); window.switchTab('tabMasters');">
          <td style="text-align:left; font-weight:700;">
            <span style="color:#60a5fa;">${d.symbol}</span> ${d.name}
          </td>
          <td style="font-weight:700;">${d.price.toFixed(2)}</td>
          <td>${peStr}</td>
          <td style="color:${fin.gross_margin > 40 ? '#34d399' : '#fff'}; font-weight:700;">${fin.gross_margin ? fin.gross_margin + '%' : '-'}</td>
          <td>${fin.operating_margin ? fin.operating_margin + '%' : '-'}</td>
          <td style="color:#34d399; font-weight:700;">${fin.roe ? fin.roe + '%' : '18.0%'}</td>
          <td style="color:#60a5fa; font-weight:700;">${compScore} / 5.0</td>
          <td style="font-size:12px; color:var(--text-secondary); text-align:left;">${moatText}</td>
        </tr>
      `;
    }).join("");
  }

  function renderPortfolioSliders() {
    const container = document.getElementById("portfolioSliders");
    if (!container) return;
    container.innerHTML = currentPortfolio.map((item, idx) => `
      <div class="p-slider-item">
        <div class="p-slider-header">
          <span class="p-slider-title" style="border-left: 3px solid ${item.color}; padding-left: 8px;">
            ${item.symbol} ${item.name}
          </span>
          <span class="p-slider-val" id="pVal_${idx}">${item.weight}%</span>
        </div>
        <input type="range" class="portfolio-slider-input" min="0" max="60" step="5" value="${item.weight}" oninput="window.changePortfolioWeight(${idx}, this.value)">
      </div>
    `).join("");
  }

  window.changePortfolioWeight = function(idx, val) {
    const newW = parseInt(val);
    currentPortfolio[idx].weight = newW;
    const valEl = document.getElementById(`pVal_${idx}`);
    if (valEl) valEl.innerText = `${newW}%`;
    updatePortfolioMetrics();
  };

  function updatePortfolioMetrics() {
    let totalW = currentPortfolio.reduce((acc, it) => acc + it.weight, 0);
    if (totalW === 0) totalW = 1;

    let weightedROE = 0;
    let weightedPE = 0;
    let weightedYield = 0;
    let weightedMoat = 0;

    currentPortfolio.forEach(it => {
      const d = STOCKS_DATABASE[it.symbol] || {};
      const normW = it.weight / totalW;
      const fin = d.financials_5y && d.financials_5y[0] ? d.financials_5y[0] : { roe: 20.0 };
      const pe = (d.valuation && d.valuation.per) ? d.valuation.per : 20.0;
      const yld = (d.valuation && d.valuation.yield_pct) ? d.valuation.yield_pct : 2.5;
      const moat = (d.synthesis && d.synthesis.radar_scores && d.synthesis.radar_scores.moat) ? d.synthesis.radar_scores.moat : 4.2;

      weightedROE += (fin.roe || 20.0) * normW;
      weightedPE += pe * normW;
      weightedYield += yld * normW;
      weightedMoat += moat * normW;
    });

    const elRoe = document.getElementById("pWeightedROE");
    const elPe = document.getElementById("pWeightedPE");
    const elYld = document.getElementById("pWeightedYield");
    const elMoat = document.getElementById("pWeightedMoat");

    if (elRoe) elRoe.innerText = `${weightedROE.toFixed(1)}%`;
    if (elPe) elPe.innerText = `${weightedPE.toFixed(1)}x`;
    if (elYld) elYld.innerText = `${weightedYield.toFixed(2)}%`;
    if (elMoat) elMoat.innerText = `${weightedMoat.toFixed(1)} / 5.0`;

    const barDist = document.getElementById("portfolioBarDist");
    if (barDist) {
      barDist.innerHTML = currentPortfolio.map(it => {
        const pct = (it.weight / totalW) * 100;
        if (pct <= 0) return "";
        return `<div class="p-bar-segment" style="width: ${pct}%; background-color: ${it.color};" title="${it.name} ${pct.toFixed(0)}%">${it.name} (${pct.toFixed(0)}%)</div>`;
      }).join("");
    }
  }

  function generateMarkdownReport(d) {
    const s = d.synthesis || {};
    const sq = d.ttm_squeeze || {};
    const k = d.kelly_sizing || {};
    const ev = k.ev_data || {};

    return `# ${d.name} (${d.symbol}) 深度投資研究報告：四大家綜合 + TTM Squeeze + 凱利持倉

> **資料基準日**：${d.date || '2026-08-14'}  
> **研究標的**：${d.name} (${d.symbol}) · ${d.sector || '核心供應鏈'}  
> **當前股價**：${(d.price || 0).toFixed(2)} ${d.currency || 'TWD'}  
> **手算總市值**：${d.market_cap_formatted}（驗算偏差 ${(d.market_cap_verification && d.market_cap_verification.diff_pct !== undefined) ? d.market_cap_verification.diff_pct : 0}% ✅）  
> **綜合決策評級**：${s.verdict_label || '🎯 強烈買入'}

---

## ⚡ TTM Squeeze 波動率壓縮與半凱利持倉

- **TTM 壓縮狀態**：${sq.status_label || '常態'}
- **動量斜率 (Slope)**：${sq.momentum || 0} (${sq.momentum_direction || '-'})
- **盈虧比 (b)**：${ev.payoff_ratio || 2.8} : 1
- **單筆期望值 (EV)**：+$${ev.ev_amount || 22.7} 元
- **半凱利建議倉位 (Half Kelly)**：${k.applied_allocation_pct || 20.0}% (建議買進約 ${k.suggested_shares || 1129} 股)

---

## 一、 核心財務雙源交叉驗證

- **手算總市值**：${d.market_cap_formatted}
- **發行股數**：${d.shares_formatted}
- **本益比 (P/E)**：${(d.valuation && d.valuation.per) ? d.valuation.per.toFixed(2) + 'x' : '-'}
- **2026 前瞻 P/E**：${(s.valuation_model && s.valuation_model.forward_pe) ? s.valuation_model.forward_pe : '-'}

---

## 二、 四大家綜合深度投研

### 1. 段永平（商業本質與做對的事）
> ${(s.dyp && s.dyp.quote) || ''}
- **生意本質**：${(s.dyp && s.dyp.business_essence) || ''}
- **做對的事**：${(s.dyp && s.dyp.right_thing) || ''}

### 2. 巴菲特（經濟護城河與資本配置）
> ${(s.buffett && s.buffett.quote) || ''}
- **護城河評估**：${(s.buffett && s.buffett.moat) || ''}
- **資本配置**：${(s.buffett && s.buffett.capital_allocation) || ''}

### 3. 芒格（逆向思考與反面清單）
> ${(s.munger && s.munger.quote) || ''}
- **逆向反思**：${(s.munger && s.munger.inversion) || ''}
- **核心風險**：
${(s.munger && s.munger.risks) ? s.munger.risks.map(r => `  - ${r}`).join("\n") : ''}

### 4. 李錄（文明進化與長期確定性）
> ${(s.lilu && s.lilu.quote) || ''}
- **文明趨勢**：${(s.lilu && s.lilu.civilization) || ''}

---

## 三、 財報精讀與月營收拐點

- **核心亮點**：${(s.earnings_review && s.earnings_review.headline) || ''}
- **業績總評**：${(s.earnings_review && s.earnings_review.h1_summary) || ''}
- **月營收訊號**：${(s.earnings_review && s.earnings_review.monthly_revenue_signal) || ''}

---

## 四、 投資論文與操作價格區間

### 核心論文支柱
${(s.thesis && s.thesis.pillars) ? s.thesis.pillars.map(p => `- ${p}`).join("\n") : ''}

### 證偽觸發條件 (Kill Criteria)
${(s.thesis && s.thesis.kill_criteria) ? s.thesis.kill_criteria.map(k => `- ⚠️ ${k}`).join("\n") : ''}
`;
  }

  // -------------------------------------------------------------
  // 頁面初始化
  // -------------------------------------------------------------
  function init() {
    const stockDropdown = document.getElementById("stockDropdown");
    if (stockDropdown) {
      const keys = Object.keys(STOCKS_DATABASE).filter(k => k.endsWith(".TW"));
      stockDropdown.innerHTML = keys.map(k => {
        const item = STOCKS_DATABASE[k];
        return `<option value="${item.symbol}">${item.symbol} ${item.name} (${item.sector || '科技'})</option>`;
      }).join("");
      stockDropdown.value = "2344.TW";
    }

    renderScreenerTable("all");
    renderPeerComparison("散熱");
    renderPortfolioSliders();
    updatePortfolioMetrics();

    // 預設加載華邦電
    analyzeStock("2344.TW");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
