# 🌐 ApexDeriv — International Derivatives & Order Flow Execution Terminal


ApexDeriv is an institutional-grade derivatives trading terminal and market microstructure simulator. Unlike standard retail charting apps that rely on lagging technical indicators, ApexDeriv mirrors the high-speed execution software used on proprietary derivatives trading desks (such as *Trading Technologies (TT)*, *Stellar*, and *CQG*).

---



---

## 🚀 Key Modules & Capabilities

### 1. Interactive Level 2 DOM (Depth of Market) Price Ladder
- **Click-to-Trade:** Click any price in the Bid column to place a Buy Limit, or Ask column to place a Sell Limit.
- **Visual Liquidity Depth:** Real-time horizontal bar indicators reflecting order book queue depth across 12 levels.
- **Speed Controls:** Instant Market Execution (`BUY MKT` / `SELL MKT`), `CANCEL ALL [ESC]`, and `FLATTEN POSITION [SPACE]`.
- **Working Order Markers:** Visual badges on active price rows with one-click order cancellation.

### 2. Global Macro Derivatives & Inter-Market Spread Desk
- **Yield Curve Desk:** Computes synthetic **2Y/10Y Treasury Yield Curve Spread** (in basis points) for curve steepener and flattener analysis.
- **Commodity Arbitrage:** Computes the **WTI vs Brent Crude Crack Spread** differential in real time.

### 3. Market Microstructure & Order Flow Analytics
- **Cumulative Volume Delta (CVD):** Tracks whether aggressive market orders are lifting offers or hitting bids to detect institutional absorption.
- **Volume Profile (POC):** Identifies the **Point of Control (POC)** and dynamic value area distribution.
- **Real-time Candlesticks:** High-performance HTML5 Canvas rendering at 4 updates per second.

### 4. Prop Desk Risk & Trimester Performance Engine
- **Circuit Breaker:** Automatic emergency liquidation and trading halt if total daily losses breach the -$1,500 threshold.
- **Desk Position Limits:** Enforces a maximum position size of 5 lots per contract to prevent rogue overleveraging.
- **Trimester Bonus Calculator:** Computes performance tiers and projected incentive compensation based on the Futures First trimester reward model.

### 5. Trainee Flight Simulator (Macro News Drills)
Interactive training scenarios designed to test candidate reflexes under volatility:
- **FOMC Rate Shock (+50 bps):** Sudden liquidity shock and aggressive bond selling.
- **US Core CPI Print (+0.5% Surprise):** High-beta equity gap and volatility expansion.
- **OPEC+ Emergency Supply Cut:** Severe aggressive buy sweeps across energy futures.
- **Flash Liquidity Vacuum:** Thin order book simulation testing order discipline and slippage tolerance.

---

## 🛠️ Quick Start

### Prerequisites
- Python 3.10+ (Dependencies `fastapi` and `uvicorn` are required)

### Launching the Workstation
Run the one-click launcher from the project directory:
```bash
python run.py
```
This automatically boots the FastAPI backend, initiates WebSocket data feeds, and opens the workstation UI at `http://127.0.0.1:8000`.

---


