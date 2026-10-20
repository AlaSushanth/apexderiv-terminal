// ApexDeriv - Core Workstation Application Logic
let ws = null;
let currentSymbol = "ZN";
let selectedLot = 1;
let soundEnabled = true;
let audioCtx = null;
let latestState = null;

// Initialize Web Audio API for prop desk fill & trade ticks
function getAudioContext() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

function playBeep(freq, type = 'sine', duration = 0.08, gainVal = 0.05) {
  if (!soundEnabled) return;
  try {
    const ctx = getAudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    gain.gain.setValueAtTime(gainVal, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  } catch (e) {
    // Audio might be blocked before first user gesture
  }
}

// Connect to WebSocket Server
function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("ApexDeriv WebSocket Connected");
    document.getElementById("connection-status").textContent = "CONNECTED (LIVE)";
    document.getElementById("connection-status").style.color = "#10b981";
  };

  ws.onmessage = (event) => {
    try {
      const state = JSON.parse(event.data);
      latestState = state;
      renderWorkstation(state);
    } catch (err) {
      console.error("Error parsing WS state:", err);
    }
  };

  ws.onclose = () => {
    console.warn("WebSocket closed. Reconnecting in 1s...");
    document.getElementById("connection-status").textContent = "RECONNECTING...";
    document.getElementById("connection-status").style.color = "#f59e0b";
    setTimeout(connectWebSocket, 1000);
  };
}

// Primary Workstation Render
function renderWorkstation(state) {
  updateHeader(state);
  renderWatchlist(state.tickers, state.active_symbol);
  renderSpreads(state.spreads);
  renderDOMLadder(state);
  renderChart(state);
  renderTape(state.tape);
  renderRiskPanel(state.risk);
  renderScenarioPanel(state.scenario);
}

// Update Top HUD
function updateHeader(state) {
  const contract = state.contract;
  document.getElementById("header-contract-name").textContent = `${contract.symbol} - ${contract.name}`;
  document.getElementById("header-last-price").textContent = contract.price.toFixed(contract.symbol.startsWith("Z") ? 4 : 2);
  
  // Position
  const pos = state.position;
  const posEl = document.getElementById("hud-position");
  if (pos.quantity === 0) {
    posEl.textContent = "FLAT";
    posEl.style.color = "#94a3b8";
  } else if (pos.quantity > 0) {
    posEl.textContent = `LONG ${pos.quantity} @ ${pos.avg_entry_price}`;
    posEl.style.color = "#10b981";
  } else {
    posEl.textContent = `SHORT ${Math.abs(pos.quantity)} @ ${pos.avg_entry_price}`;
    posEl.style.color = "#ef4444";
  }

  // P&L
  const pnlEl = document.getElementById("hud-net-pnl");
  const netPnl = state.risk.total_net_pnl;
  pnlEl.textContent = `$${netPnl >= 0 ? '+' : ''}${netPnl.toFixed(2)}`;
  pnlEl.style.color = netPnl >= 0 ? "#10b981" : "#ef4444";

  // Account Balance
  document.getElementById("hud-balance").textContent = `$${state.risk.account_balance.toLocaleString(undefined, {minimumFractionDigits: 2})}`;

  // Trimester Tier
  document.getElementById("hud-trimester-tier").textContent = state.risk.trimester_tier;

  // Circuit Breaker Alert Banner
  const alertBanner = document.getElementById("circuit-breaker-banner");
  if (state.risk.circuit_breaker_tripped) {
    alertBanner.style.display = "flex";
    document.getElementById("breaker-reason-text").textContent = state.risk.circuit_breaker_reason;
    playBeep(220, 'square', 0.2, 0.1); // Alert buzzer
  } else {
    alertBanner.style.display = "none";
  }
}

// Watchlist Render
function renderWatchlist(tickers, activeSymbol) {
  const container = document.getElementById("watchlist-items");
  container.innerHTML = "";
  
  tickers.forEach(t => {
    const card = document.createElement("div");
    card.className = `ticker-card ${t.symbol === activeSymbol ? 'active' : ''}`;
    card.onclick = () => selectSymbol(t.symbol);
    
    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span class="mono" style="font-weight:700; font-size:13px; color:#f1f5f9;">${t.symbol}</span>
        <span class="mono" style="font-size:13px; font-weight:700; color:#38bdf8;">${t.price}</span>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:10px; color:#64748b; margin-top:3px;">
        <span>${t.name}</span>
        <span>${t.category}</span>
      </div>
    `;
    container.appendChild(card);
  });
}

// Spreads Render
function renderSpreads(spreads) {
  document.getElementById("spread-2y10y-val").textContent = `${spreads.spread_2y10y_bps >= 0 ? '+' : ''}${spreads.spread_2y10y_bps} bps`;
  document.getElementById("spread-clbz-val").textContent = `$${spreads.spread_cl_bz.toFixed(2)}`;
}

// DOM Price Ladder Rendering
function renderDOMLadder(state) {
  const listEl = document.getElementById("ladder-rows");
  const contract = state.contract;
  const bids = state.bids;
  const asks = state.asks;
  const openOrders = state.open_orders || [];
  
  const currentPrice = contract.price;
  const decimals = contract.symbol.startsWith("Z") ? 4 : 2;

  // Find max size for bar scaling
  let maxSize = 80;
  bids.forEach(b => { if (b.size > maxSize) maxSize = b.size; });
  asks.forEach(a => { if (a.size > maxSize) maxSize = a.size; });

  // Merge price levels (top asks descending, top bids descending)
  let rowsHtml = "";

  // Render Asks (from highest down to lowest ask)
  for (let i = asks.length - 1; i >= 0; i--) {
    const lvl = asks[i];
    const widthPct = Math.min(100, Math.round((lvl.size / maxSize) * 100));
    const isLast = Math.abs(lvl.price - currentPrice) < 0.00001;
    const myOrder = openOrders.find(o => Math.abs(o.price - lvl.price) < 0.0001 && o.side === 'SELL');

    rowsHtml += `
      <div class="ladder-row" data-price="${lvl.price}">
        <div class="ladder-cell ladder-bid" onclick="placeLimitOrder('BUY', ${lvl.price})">
          <!-- Empty for Ask rows -->
        </div>
        <div class="ladder-cell ladder-price mono ${isLast ? 'last-traded' : ''}">
          ${lvl.price.toFixed(decimals)}
        </div>
        <div class="ladder-cell ladder-ask mono" onclick="placeLimitOrder('SELL', ${lvl.price})">
          <div class="depth-bar-ask" style="width: ${widthPct}%;"></div>
          <span style="position:relative; z-index:2;">${lvl.size}</span>
          ${myOrder ? `<span class="my-order-pill" onclick="cancelOrder('${myOrder.order_id}', event)">${myOrder.quantity}x [✕]</span>` : ''}
        </div>
      </div>
    `;
  }

  // Render Bids (from highest down to lowest bid)
  for (let i = 0; i < bids.length; i++) {
    const lvl = bids[i];
    const widthPct = Math.min(100, Math.round((lvl.size / maxSize) * 100));
    const isLast = Math.abs(lvl.price - currentPrice) < 0.00001;
    const myOrder = openOrders.find(o => Math.abs(o.price - lvl.price) < 0.0001 && o.side === 'BUY');

    rowsHtml += `
      <div class="ladder-row" data-price="${lvl.price}">
        <div class="ladder-cell ladder-bid mono" onclick="placeLimitOrder('BUY', ${lvl.price})">
          <div class="depth-bar-bid" style="width: ${widthPct}%;"></div>
          <span style="position:relative; z-index:2;">${lvl.size}</span>
          ${myOrder ? `<span class="my-order-pill" onclick="cancelOrder('${myOrder.order_id}', event)">${myOrder.quantity}x [✕]</span>` : ''}
        </div>
        <div class="ladder-cell ladder-price mono ${isLast ? 'last-traded' : ''}">
          ${lvl.price.toFixed(decimals)}
        </div>
        <div class="ladder-cell ladder-ask" onclick="placeLimitOrder('SELL', ${lvl.price})">
          <!-- Empty for Bid rows -->
        </div>
      </div>
    `;
  }

  listEl.innerHTML = rowsHtml;
}

// Canvas Candlestick & CVD Chart
function renderChart(state) {
  const canvas = document.getElementById("chart-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  
  // Set resolution
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }

  ctx.clearRect(0, 0, width, height);

  const candles = state.candles || [];
  if (candles.length === 0) return;

  const chartHeight = height * 0.70;
  const cvdHeight = height * 0.25;
  const cvdTop = height * 0.75;

  // Find min/max prices
  let minP = Infinity;
  let maxP = -Infinity;
  candles.forEach(c => {
    if (c.low < minP) minP = c.low;
    if (c.high > maxP) maxP = c.high;
  });
  const currentP = state.contract.price;
  minP = Math.min(minP, currentP) * 0.9995;
  maxP = Math.max(maxP, currentP) * 1.0005;
  const range = maxP - minP || 1;

  // Grid lines
  ctx.strokeStyle = "#172033";
  ctx.lineWidth = 1;
  for (let i = 0; i < 5; i++) {
    const y = 10 + (chartHeight - 20) * (i / 4);
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();

    const priceLabel = (maxP - (range * (i / 4))).toFixed(state.contract.symbol.startsWith("Z") ? 4 : 2);
    ctx.fillStyle = "#475569";
    ctx.font = "10px monospace";
    ctx.fillText(priceLabel, width - 65, y - 4);
  }

  // Draw Volume Profile bars on right side
  const prof = state.volume_profile.levels || [];
  let maxVol = 1;
  prof.forEach(p => { if (p[1] > maxVol) maxVol = p[1]; });
  
  prof.forEach(([p, vol]) => {
    const y = chartHeight - ((p - minP) / range) * chartHeight;
    const barW = (vol / maxVol) * 80;
    ctx.fillStyle = "rgba(56, 189, 248, 0.12)";
    ctx.fillRect(width - 80, y - 2, barW, 4);
  });

  // POC line
  const pocY = chartHeight - ((state.volume_profile.poc - minP) / range) * chartHeight;
  ctx.strokeStyle = "#f59e0b";
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(0, pocY);
  ctx.lineTo(width, pocY);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = "#f59e0b";
  ctx.fillText(`POC: ${state.volume_profile.poc}`, 10, pocY - 4);

  // Draw Candlesticks
  const candleW = Math.max(4, Math.floor((width - 90) / candles.length) - 3);
  candles.forEach((c, idx) => {
    const x = 20 + idx * (candleW + 3);
    const openY = chartHeight - ((c.open - minP) / range) * chartHeight;
    const closeY = chartHeight - ((c.close - minP) / range) * chartHeight;
    const highY = chartHeight - ((c.high - minP) / range) * chartHeight;
    const lowY = chartHeight - ((c.low - minP) / range) * chartHeight;

    const isBull = c.close >= c.open;
    ctx.strokeStyle = isBull ? "#10b981" : "#ef4444";
    ctx.fillStyle = isBull ? "#10b981" : "#ef4444";

    // Wick
    ctx.beginPath();
    ctx.moveTo(x + candleW / 2, highY);
    ctx.lineTo(x + candleW / 2, lowY);
    ctx.stroke();

    // Body
    const topY = Math.min(openY, closeY);
    const bodyH = Math.max(2, Math.abs(openY - closeY));
    ctx.fillRect(x, topY, candleW, bodyH);
  });

  // CVD Sub-panel
  ctx.fillStyle = "#0a0f1c";
  ctx.fillRect(0, cvdTop, width, cvdHeight);
  ctx.strokeStyle = "#1e293b";
  ctx.strokeRect(0, cvdTop, width, cvdHeight);

  ctx.fillStyle = "#64748b";
  ctx.font = "10px monospace";
  ctx.fillText(`CVD (Cumulative Volume Delta): ${state.cvd >= 0 ? '+' : ''}${state.cvd}`, 10, cvdTop + 16);

  // CVD Bar indicator
  const cvdMidX = width / 2;
  const barLen = Math.min(width * 0.45, Math.abs(state.cvd) * 0.5);
  ctx.fillStyle = state.cvd >= 0 ? "#10b981" : "#ef4444";
  if (state.cvd >= 0) {
    ctx.fillRect(cvdMidX, cvdTop + 24, barLen, 12);
  } else {
    ctx.fillRect(cvdMidX - barLen, cvdTop + 24, barLen, 12);
  }
}

// Time & Sales Tape
function renderTape(tape) {
  const container = document.getElementById("tape-items");
  if (!container) return;
  container.innerHTML = "";

  tape.slice(0, 16).forEach(t => {
    const row = document.createElement("div");
    row.className = "tape-row mono";
    const sideClass = t.side === "BUY" ? "tape-buy" : "tape-sell";
    row.innerHTML = `
      <span style="color:#64748b;">${t.time}</span>
      <span style="color:#f1f5f9; font-weight:700;">${t.price}</span>
      <span class="${sideClass}" style="font-weight:700;">${t.size}</span>
      <span class="${sideClass}">${t.side}</span>
    `;
    container.appendChild(row);
  });
}

// Risk & Desk Performance Scorecard
function renderRiskPanel(risk) {
  document.getElementById("risk-realized-pnl").textContent = `$${risk.daily_pnl.toFixed(2)}`;
  document.getElementById("risk-win-rate").textContent = `${risk.win_rate}% (${risk.total_trades} trades)`;
  document.getElementById("risk-projected-bonus").textContent = risk.projected_bonus_inr;

  // Max Drawdown Gauge
  const maxLoss = Math.abs(risk.max_daily_loss);
  const currentDrawdown = Math.max(0, -risk.total_net_pnl);
  const pct = Math.min(100, Math.round((currentDrawdown / maxLoss) * 100));
  
  const gaugeBar = document.getElementById("drawdown-gauge-bar");
  gaugeBar.style.width = `${pct}%`;
  gaugeBar.style.backgroundColor = pct > 80 ? "#ef4444" : pct > 50 ? "#f59e0b" : "#3b82f6";
  document.getElementById("drawdown-label").textContent = `${pct}% of Limit ($${currentDrawdown.toFixed(0)} / $${maxLoss})`;
}

// Trainee Scenario Drills Panel
function renderScenarioPanel(scenario) {
  const logsContainer = document.getElementById("scenario-logs");
  if (logsContainer) {
    logsContainer.innerHTML = (scenario.logs || []).map(l => `<div style="margin-bottom:3px; color:#cbd5e1;">${l}</div>`).join("");
  }

  const buttons = document.querySelectorAll(".scenario-btn");
  buttons.forEach(btn => {
    const scId = btn.getAttribute("data-scenario");
    if (scenario.active === scId) {
      btn.classList.add("running");
      btn.querySelector(".sc-badge").textContent = `LIVE (${scenario.remaining_seconds}s)`;
    } else {
      btn.classList.remove("running");
      btn.querySelector(".sc-badge").textContent = "IDLE";
    }
  });
}

// User Actions
async function selectSymbol(symbol) {
  currentSymbol = symbol;
  await fetch("/api/select_symbol", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol })
  });
  playBeep(440, 'triangle', 0.05);
}

function setLot(qty) {
  selectedLot = qty;
  document.querySelectorAll(".lot-btn").forEach(b => {
    b.classList.toggle("active", parseInt(b.getAttribute("data-lot")) === qty);
  });
}

async function placeOrder(orderType, side, price = 0.0) {
  if (!latestState) return;
  const symbol = latestState.active_symbol;
  
  const res = await fetch("/api/order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symbol: symbol,
      side: side,
      order_type: orderType,
      price: price,
      quantity: selectedLot
    })
  });
  const data = await res.json();
  if (data.status === "REJECTED") {
    alert(data.message);
    playBeep(200, 'sawtooth', 0.15);
  } else {
    playBeep(side === 'BUY' ? 660 : 520, 'sine', 0.08);
  }
}

function placeLimitOrder(side, price) {
  placeOrder("LIMIT", side, price);
}

async function cancelOrder(orderId, event) {
  if (event) event.stopPropagation();
  await fetch(`/api/cancel/${orderId}`, { method: "POST" });
  playBeep(350, 'sine', 0.04);
}

async function cancelAllOrders() {
  await fetch("/api/cancel_all", { method: "POST" });
  playBeep(300, 'sine', 0.06);
}

async function flattenActive() {
  await fetch("/api/flatten", { method: "POST" });
  playBeep(700, 'square', 0.1);
}

async function flattenAllDesks() {
  await fetch("/api/flatten_all", { method: "POST" });
  playBeep(700, 'square', 0.1);
}

async function triggerScenario(scenarioId) {
  await fetch("/api/scenario", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario_id: scenarioId })
  });
  playBeep(880, 'sine', 0.15);
}

async function resetRisk() {
  await fetch("/api/reset_risk", { method: "POST" });
  playBeep(550, 'sine', 0.1);
}

function toggleAudio() {
  soundEnabled = !soundEnabled;
  document.getElementById("audio-toggle-btn").textContent = soundEnabled ? "🔊 SOUND: ON" : "🔇 SOUND: OFF";
}

// Hotkey Bindings
window.addEventListener("keydown", (e) => {
  if (e.target.tagName === 'INPUT') return;
  if (e.code === "Space") {
    e.preventDefault();
    flattenActive();
  } else if (e.code === "Escape") {
    e.preventDefault();
    cancelAllOrders();
  } else if (e.key === "1") {
    setLot(1);
  } else if (e.key === "2") {
    setLot(2);
  } else if (e.key === "5") {
    setLot(5);
  }
});

// Boot up
window.addEventListener("DOMContentLoaded", () => {
  connectWebSocket();
});
