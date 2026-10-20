import time
import math
import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

@dataclass
class ContractSpec:
    symbol: str
    name: str
    category: str
    tick_size: float
    tick_value: float
    point_value: float
    base_price: float
    decimals: int

CONTRACTS: Dict[str, ContractSpec] = {
    "ZN": ContractSpec(
        symbol="ZN",
        name="10-Year US Treasury Note",
        category="Fixed Income",
        tick_size=0.015625,  # 1/64
        tick_value=15.625,
        point_value=1000.0,
        base_price=109.5000,
        decimals=4
    ),
    "ZT": ContractSpec(
        symbol="ZT",
        name="2-Year US Treasury Note",
        category="Fixed Income",
        tick_size=0.0078125, # 1/128
        tick_value=15.625,
        point_value=2000.0,
        base_price=102.2500,
        decimals=4
    ),
    "CL": ContractSpec(
        symbol="CL",
        name="Crude Oil WTI",
        category="Commodities",
        tick_size=0.01,
        tick_value=10.0,
        point_value=1000.0,
        base_price=78.45,
        decimals=2
    ),
    "BZ": ContractSpec(
        symbol="BZ",
        name="Brent Crude Oil",
        category="Commodities",
        tick_size=0.01,
        tick_value=10.0,
        point_value=1000.0,
        base_price=82.30,
        decimals=2
    ),
    "ES": ContractSpec(
        symbol="ES",
        name="E-mini S&P 500",
        category="Indices",
        tick_size=0.25,
        tick_value=12.50,
        point_value=50.0,
        base_price=5824.50,
        decimals=2
    )
}

@dataclass
class Order:
    order_id: str
    symbol: str
    side: str        # 'BUY' or 'SELL'
    order_type: str  # 'LIMIT', 'MARKET', 'STOP'
    price: float
    quantity: int
    filled_quantity: int = 0
    status: str = "OPEN" # 'OPEN', 'FILLED', 'CANCELLED'
    created_at: float = field(default_factory=time.time)
    queue_ahead: int = 0

@dataclass
class Position:
    symbol: str
    quantity: int = 0     # positive for long, negative for short
    avg_entry_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

class MarketEngine:
    def __init__(self):
        self.specs = CONTRACTS
        self.active_symbol = "ZN"
        self.prices: Dict[str, float] = {s: spec.base_price for s, spec in self.specs.items()}
        
        # Order books for each contract: list of {price, size, my_orders}
        self.bids: Dict[str, List[Dict[str, Any]]] = {}
        self.asks: Dict[str, List[Dict[str, Any]]] = {}
        
        # Order flow & analytics
        self.tape: Dict[str, List[Dict[str, Any]]] = {s: [] for s in self.specs}
        self.cvd: Dict[str, float] = {s: 0.0 for s in self.specs}
        self.volume_profile: Dict[str, Dict[float, int]] = {s: {} for s in self.specs}
        self.candle_history: Dict[str, List[Dict[str, Any]]] = {s: [] for s in self.specs}
        
        # User orders and position
        self.user_orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {s: Position(symbol=s) for s in self.specs}
        self.starting_balance = 100000.0
        self.account_balance = 100000.0
        self.daily_pnl = 0.0
        self.max_daily_loss = -1500.0  # Futures First Prop Desk circuit breaker
        self.max_position_limit = 5   # Max 5 lots per contract
        self.circuit_breaker_tripped = False
        self.circuit_breaker_reason = ""
        
        # Performance Tracking
        self.trade_history: List[Dict[str, Any]] = []
        self.pnl_snapshots: List[float] = [0.0]
        self.last_candle_time = time.time()
        self.current_candle: Dict[str, Dict[str, Any]] = {}
        
        # Trainee Flight Simulator Scenarios
        self.active_scenario: Optional[str] = None
        self.scenario_timer: int = 0
        self.scenario_duration: int = 60
        self.scenario_logs: List[str] = []
        
        # Initialize order books
        for s in self.specs:
            self._init_book(s)
            self._init_candles(s)

    def _init_candles(self, symbol: str):
        price = self.prices[symbol]
        now = time.time()
        candles = []
        for i in range(25, 0, -1):
            t = now - (i * 10)
            noise = (random.random() - 0.5) * self.specs[symbol].tick_size * 4
            open_p = price + noise
            close_p = open_p + (random.random() - 0.5) * self.specs[symbol].tick_size * 3
            high_p = max(open_p, close_p) + abs((random.random()) * self.specs[symbol].tick_size * 2)
            low_p = min(open_p, close_p) - abs((random.random()) * self.specs[symbol].tick_size * 2)
            vol = random.randint(40, 300)
            candles.append({
                "time": int(t),
                "open": round(open_p, self.specs[symbol].decimals),
                "high": round(high_p, self.specs[symbol].decimals),
                "low": round(low_p, self.specs[symbol].decimals),
                "close": round(close_p, self.specs[symbol].decimals),
                "volume": vol
            })
        self.candle_history[symbol] = candles
        self.current_candle[symbol] = {
            "time": int(now),
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": 0
        }

    def _init_book(self, symbol: str):
        spec = self.specs[symbol]
        center_price = self.prices[symbol]
        tick = spec.tick_size
        
        bids = []
        asks = []
        for i in range(1, 15):
            b_price = round(center_price - (i * tick), spec.decimals)
            a_price = round(center_price + (i * tick), spec.decimals)
            
            # Realistic depth distribution (higher size further out, random distribution)
            b_size = int(random.randint(15, 60) + (i * 8))
            a_size = int(random.randint(15, 60) + (i * 8))
            
            bids.append({"price": b_price, "size": b_size, "orders": random.randint(3, 12), "user_size": 0})
            asks.append({"price": a_price, "size": a_size, "orders": random.randint(3, 12), "user_size": 0})
            
            # seed volume profile
            self.volume_profile[symbol][b_price] = random.randint(100, 500)
            self.volume_profile[symbol][a_price] = random.randint(100, 500)
            
        self.bids[symbol] = bids
        self.asks[symbol] = asks

    def set_active_symbol(self, symbol: str):
        if symbol in self.specs:
            self.active_symbol = symbol

    def tick(self):
        """Advances market simulation by 1 tick (~200ms - 500ms intervals)"""
        now = time.time()
        
        # Handle scenario progression if active
        if self.active_scenario:
            self._progress_scenario()

        for symbol in self.specs:
            spec = self.specs[symbol]
            tick = spec.tick_size
            curr_price = self.prices[symbol]
            
            # Scenario bias
            bias = 0.0
            volatility_mult = 1.0
            if self.active_scenario == "FOMC_SHOCK" and symbol in ["ZN", "ZT"]:
                bias = -0.75  # Heavy selling in bonds
                volatility_mult = 3.5
            elif self.active_scenario == "CPI_SURPRISE" and symbol in ["ES", "ZN"]:
                bias = -0.6
                volatility_mult = 2.8
            elif self.active_scenario == "OPEC_CUT" and symbol in ["CL", "BZ"]:
                bias = 0.8   # Massive buying in oil
                volatility_mult = 3.0
            elif self.active_scenario == "FLASH_VACUUM":
                volatility_mult = 4.0
            
            # Random market participant flow
            p_roll = random.random()
            num_trades = random.randint(1, 4)
            
            for _ in range(num_trades):
                # Decide trade direction
                side = "BUY" if (random.random() + bias) > 0.5 else "SELL"
                trade_size = random.randint(1, 15) * (2 if self.active_scenario else 1)
                
                if side == "BUY" and self.asks[symbol]:
                    best_ask = self.asks[symbol][0]
                    trade_price = best_ask["price"]
                    best_ask["size"] -= trade_size
                    self.cvd[symbol] += trade_size
                    
                    # If top of book cleared, price moves up
                    if best_ask["size"] <= 0:
                        cleared = self.asks[symbol].pop(0)
                        self.prices[symbol] = cleared["price"]
                        # Push top bid up
                        new_bid_price = cleared["price"]
                        self.bids[symbol].insert(0, {"price": new_bid_price, "size": random.randint(10, 40), "orders": random.randint(2, 6), "user_size": 0})
                        # Add new ask at top
                        highest_ask = self.asks[symbol][-1]["price"] if self.asks[symbol] else cleared["price"] + tick
                        self.asks[symbol].append({"price": round(highest_ask + tick, spec.decimals), "size": random.randint(30, 90), "orders": random.randint(3, 10), "user_size": 0})
                
                elif side == "SELL" and self.bids[symbol]:
                    best_bid = self.bids[symbol][0]
                    trade_price = best_bid["price"]
                    best_bid["size"] -= trade_size
                    self.cvd[symbol] -= trade_size
                    
                    # If top bid cleared, price moves down
                    if best_bid["size"] <= 0:
                        cleared = self.bids[symbol].pop(0)
                        self.prices[symbol] = cleared["price"]
                        # Push top ask down
                        new_ask_price = cleared["price"]
                        self.asks[symbol].insert(0, {"price": new_ask_price, "size": random.randint(10, 40), "orders": random.randint(2, 6), "user_size": 0})
                        # Add new bid at bottom
                        lowest_bid = self.bids[symbol][-1]["price"] if self.bids[symbol] else cleared["price"] - tick
                        self.bids[symbol].append({"price": round(lowest_bid - tick, spec.decimals), "size": random.randint(30, 90), "orders": random.randint(3, 10), "user_size": 0})
                else:
                    trade_price = self.prices[symbol]

                # Update volume profile
                trade_price = round(trade_price, spec.decimals)
                self.volume_profile[symbol][trade_price] = self.volume_profile[symbol].get(trade_price, 0) + trade_size
                
                # Add to tape (last 25 trades)
                self.tape[symbol].insert(0, {
                    "time": time.strftime("%H:%M:%S"),
                    "price": trade_price,
                    "size": trade_size,
                    "side": side
                })
                if len(self.tape[symbol]) > 25:
                    self.tape[symbol].pop()

                # Update candle
                c = self.current_candle[symbol]
                c["high"] = max(c["high"], trade_price)
                c["low"] = min(c["low"], trade_price)
                c["close"] = trade_price
                c["volume"] += trade_size

                # Match user limit / stop orders
                self._match_user_orders(symbol, trade_price, side, trade_size)

            # Candle rollover every 10 seconds
            if now - self.last_candle_time >= 10:
                for sym in self.specs:
                    cur = self.current_candle[sym]
                    self.candle_history[sym].append(dict(cur))
                    if len(self.candle_history[sym]) > 40:
                        self.candle_history[sym].pop(0)
                    self.current_candle[sym] = {
                        "time": int(now),
                        "open": self.prices[sym],
                        "high": self.prices[sym],
                        "low": self.prices[sym],
                        "close": self.prices[sym],
                        "volume": 0
                    }
                self.last_candle_time = now

            # Refresh book order sizes slightly (fluid liquidity replenishment)
            self._replenish_liquidity(symbol)

        # Update P&L and evaluate Risk Circuit Breakers
        self._update_pnl_and_risk()

    def _replenish_liquidity(self, symbol: str):
        for b in self.bids[symbol]:
            if b["size"] < 15:
                b["size"] += random.randint(3, 12)
        for a in self.asks[symbol]:
            if a["size"] < 15:
                a["size"] += random.randint(3, 12)

    def _match_user_orders(self, symbol: str, trade_price: float, side: str, trade_size: int):
        spec = self.specs[symbol]
        for order_id, order in list(self.user_orders.items()):
            if order.status != "OPEN" or order.symbol != symbol:
                continue
            
            fill = False
            fill_price = order.price
            
            if order.order_type == "LIMIT":
                if order.side == "BUY" and trade_price <= order.price:
                    if order.queue_ahead <= 0:
                        fill = True
                    else:
                        order.queue_ahead -= trade_size
                elif order.side == "SELL" and trade_price >= order.price:
                    if order.queue_ahead <= 0:
                        fill = True
                    else:
                        order.queue_ahead -= trade_size
            elif order.order_type == "STOP":
                if order.side == "BUY" and trade_price >= order.price:
                    fill = True
                    fill_price = trade_price  # Slippage simulated
                elif order.side == "SELL" and trade_price <= order.price:
                    fill = True
                    fill_price = trade_price
            
            if fill:
                order.filled_quantity = order.quantity
                order.status = "FILLED"
                self._execute_fill(order.symbol, order.side, order.quantity, fill_price)

    def _execute_fill(self, symbol: str, side: str, qty: int, price: float):
        spec = self.specs[symbol]
        pos = self.positions[symbol]
        signed_qty = qty if side == "BUY" else -qty
        
        # Log to trade history
        self.trade_history.insert(0, {
            "time": time.strftime("%H:%M:%S"),
            "symbol": symbol,
            "side": side,
            "quantity": qty,
            "price": price,
            "pnl": 0.0
        })

        if pos.quantity == 0:
            pos.quantity = signed_qty
            pos.avg_entry_price = price
        elif (pos.quantity > 0 and signed_qty > 0) or (pos.quantity < 0 and signed_qty < 0):
            # Adding to existing position
            total_qty = pos.quantity + signed_qty
            pos.avg_entry_price = ((pos.quantity * pos.avg_entry_price) + (signed_qty * price)) / total_qty
            pos.quantity = total_qty
        else:
            # Closing or reversing position
            closing_qty = min(abs(pos.quantity), abs(signed_qty))
            direction = 1 if pos.quantity > 0 else -1
            price_diff = (price - pos.avg_entry_price) * direction
            realized = (price_diff / spec.tick_size) * spec.tick_value * closing_qty
            
            pos.realized_pnl += realized
            self.daily_pnl += realized
            self.account_balance += realized
            self.trade_history[0]["pnl"] = round(realized, 2)
            
            remaining_qty = pos.quantity + signed_qty
            if remaining_qty == 0:
                pos.quantity = 0
                pos.avg_entry_price = 0.0
            else:
                pos.quantity = remaining_qty
                if (pos.quantity > 0 and signed_qty > 0) or (pos.quantity < 0 and signed_qty < 0):
                    pos.avg_entry_price = price

    def submit_order(self, symbol: str, side: str, order_type: str, price: float, quantity: int) -> Dict[str, Any]:
        """Submits an order from the user DOM ladder or hotkey panel"""
        if self.circuit_breaker_tripped:
            return {"status": "REJECTED", "message": "Circuit breaker active! Risk limits violated."}
        
        pos = self.positions[symbol]
        future_qty = abs(pos.quantity + (quantity if side == "BUY" else -quantity))
        if future_qty > self.max_position_limit:
            return {
                "status": "REJECTED",
                "message": f"Position limit exceeded! Desk limit: {self.max_position_limit} lots."
            }

        spec = self.specs[symbol]
        order_id = f"ORD-{int(time.time()*1000)%1000000:06d}"
        
        if order_type == "MARKET":
            # Immediate fill at best ask/bid
            fill_price = self.asks[symbol][0]["price"] if side == "BUY" else self.bids[symbol][0]["price"]
            self._execute_fill(symbol, side, quantity, fill_price)
            return {"status": "FILLED", "order_id": order_id, "price": fill_price, "side": side, "quantity": quantity}
        
        # Limit or Stop order
        queue_ahead = random.randint(10, 45) # simulated queue ahead
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            price=round(price, spec.decimals),
            quantity=quantity,
            queue_ahead=queue_ahead
        )
        self.user_orders[order_id] = order
        
        # Update user size marker in book
        book = self.bids[symbol] if side == "BUY" else self.asks[symbol]
        for lvl in book:
            if abs(lvl["price"] - order.price) < (spec.tick_size / 2):
                lvl["user_size"] += quantity
                break

        return {"status": "ACCEPTED", "order_id": order_id, "price": order.price, "side": side, "quantity": quantity}

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.user_orders:
            order = self.user_orders[order_id]
            if order.status == "OPEN":
                order.status = "CANCELLED"
                # Remove user_size in book
                book = self.bids[order.symbol] if order.side == "BUY" else self.asks[order.symbol]
                for lvl in book:
                    if abs(lvl["price"] - order.price) < (self.specs[order.symbol].tick_size / 2):
                        lvl["user_size"] = max(0, lvl["user_size"] - order.quantity)
                        break
                return True
        return False

    def cancel_all_orders(self, symbol: Optional[str] = None):
        for o_id, order in self.user_orders.items():
            if order.status == "OPEN":
                if symbol is None or order.symbol == symbol:
                    self.cancel_order(o_id)

    def flatten_position(self, symbol: str):
        pos = self.positions[symbol]
        if pos.quantity != 0:
            side = "SELL" if pos.quantity > 0 else "BUY"
            qty = abs(pos.quantity)
            self.submit_order(symbol, side, "MARKET", 0.0, qty)
        self.cancel_all_orders(symbol)

    def flatten_all(self):
        for sym in self.specs:
            self.flatten_position(sym)

    def _update_pnl_and_risk(self):
        total_unrealized = 0.0
        for symbol, pos in self.positions.items():
            if pos.quantity != 0:
                spec = self.specs[symbol]
                curr_price = self.prices[symbol]
                direction = 1 if pos.quantity > 0 else -1
                price_diff = (curr_price - pos.avg_entry_price) * direction
                ticks = price_diff / spec.tick_size
                pos.unrealized_pnl = round(ticks * spec.tick_value * abs(pos.quantity), 2)
            else:
                pos.unrealized_pnl = 0.0
            total_unrealized += pos.unrealized_pnl

        net_equity = self.starting_balance + self.daily_pnl + total_unrealized
        current_total_pnl = self.daily_pnl + total_unrealized
        
        # Check Futures First Desk Circuit Breaker (-$1,500 daily drawdown limit)
        if current_total_pnl <= self.max_daily_loss and not self.circuit_breaker_tripped:
            self.circuit_breaker_tripped = True
            self.circuit_breaker_reason = f"MAX DAILY DRAWDOWN BREACHED (${current_total_pnl:.2f} <= ${self.max_daily_loss:.2f})! RISK MANAGER AUTO-LIQUIDATION TRIGGERED."
            # Force auto-liquidation of all desks
            self.flatten_all()
        
        # Track P&L equity curve
        self.pnl_snapshots.append(current_total_pnl)
        if len(self.pnl_snapshots) > 100:
            self.pnl_snapshots.pop(0)

    def start_scenario(self, scenario_id: str):
        """Launches a high-intensity Trainee Flight Simulator scenario"""
        self.active_scenario = scenario_id
        self.scenario_timer = self.scenario_duration
        desc = {
            "FOMC_SHOCK": "ALERT: Federal Reserve unexpectedly hikes rates by 50 bps! Bond markets facing immediate liquidity shock.",
            "CPI_SURPRISE": "ALERT: US Core CPI prints +0.5% (Exp: +0.2%). High-beta equities and index futures plummeting.",
            "OPEC_CUT": "ALERT: OPEC+ announces surprise 1.5M bpd crude oil output cut! Energy futures breaking resistance.",
            "FLASH_VACUUM": "ALERT: Order book depth evaporating! Wide spreads, extreme slippage test for order discipline."
        }.get(scenario_id, "Scenario Started.")
        self.scenario_logs.insert(0, f"[{time.strftime('%H:%M:%S')}] {desc}")

    def _progress_scenario(self):
        self.scenario_timer -= 1
        if self.scenario_timer <= 0:
            self.scenario_logs.insert(0, f"[{time.strftime('%H:%M:%S')}] Scenario completed. Reviewing trainee risk & execution metrics.")
            self.active_scenario = None

    def reset_risk(self):
        """Resets risk circuit breaker and restarts session"""
        self.circuit_breaker_tripped = False
        self.circuit_breaker_reason = ""
        self.daily_pnl = 0.0
        self.account_balance = self.starting_balance
        self.flatten_all()
        self.trade_history.clear()
        self.pnl_snapshots = [0.0]

    def get_market_state(self) -> Dict[str, Any]:
        """Returns the full real-time snapshot for the workstation UI"""
        sym = self.active_symbol
        spec = self.specs[sym]
        pos = self.positions[sym]
        
        # Calculate Volume Profile POC (Point of Control) & Value Area
        prof = self.volume_profile[sym]
        poc_price = max(prof, key=prof.get) if prof else self.prices[sym]
        sorted_levels = sorted(prof.items(), key=lambda x: x[0])
        total_vol = sum(prof.values())
        
        # Spreads
        zn_price = self.prices["ZN"]
        zt_price = self.prices["ZT"]
        cl_price = self.prices["CL"]
        bz_price = self.prices["BZ"]
        
        # Synthetic 10Y-2Y spread in basis points
        spread_2y10y = round((zn_price - zt_price) * 100, 2)
        # WTI - Brent crack spread
        spread_cl_bz = round(cl_price - bz_price, 2)
        
        # Performance metrics
        trades_won = len([t for t in self.trade_history if t.get("pnl", 0) > 0])
        trades_lost = len([t for t in self.trade_history if t.get("pnl", 0) < 0])
        total_trades = max(1, len(self.trade_history))
        win_rate = round((trades_won / total_trades) * 100, 1) if self.trade_history else 0.0
        
        total_unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        total_net_pnl = round(self.daily_pnl + total_unrealized, 2)
        
        # Trimester bonus projection (per Futures First brochure incentive structure)
        trimester_tier = "Probationary"
        projected_bonus_inr = "₹ 0"
        if total_net_pnl > 3000:
            trimester_tier = "Tier 1: High Alpha Trainee"
            projected_bonus_inr = "₹ 5,90,000+ (Target Achieved)"
        elif total_net_pnl > 1200:
            trimester_tier = "Tier 2: Consistent Maker"
            projected_bonus_inr = "₹ 3,50,000 (Indicative)"
        elif total_net_pnl > 400:
            trimester_tier = "Tier 3: Standard Performer"
            projected_bonus_inr = "₹ 1,50,000 (Base Incentive)"

        return {
            "active_symbol": sym,
            "contract": {
                "symbol": spec.symbol,
                "name": spec.name,
                "category": spec.category,
                "tick_size": spec.tick_size,
                "tick_value": spec.tick_value,
                "point_value": spec.point_value,
                "price": round(self.prices[sym], spec.decimals)
            },
            "tickers": [
                {
                    "symbol": s,
                    "name": self.specs[s].name,
                    "price": round(self.prices[s], self.specs[s].decimals),
                    "category": self.specs[s].category
                }
                for s in self.specs
            ],
            "bids": self.bids[sym][:12],
            "asks": self.asks[sym][:12],
            "tape": self.tape[sym],
            "cvd": round(self.cvd[sym], 2),
            "candles": self.candle_history[sym],
            "current_candle": self.current_candle[sym],
            "volume_profile": {
                "poc": round(poc_price, spec.decimals),
                "total_volume": total_vol,
                "levels": sorted_levels[-15:] if len(sorted_levels) > 15 else sorted_levels
            },
            "spreads": {
                "spread_2y10y_bps": spread_2y10y,
                "spread_cl_bz": spread_cl_bz
            },
            "position": {
                "symbol": sym,
                "quantity": pos.quantity,
                "avg_entry_price": round(pos.avg_entry_price, spec.decimals),
                "unrealized_pnl": pos.unrealized_pnl,
                "realized_pnl": round(pos.realized_pnl, 2)
            },
            "risk": {
                "account_balance": round(self.account_balance, 2),
                "daily_pnl": round(self.daily_pnl, 2),
                "total_net_pnl": total_net_pnl,
                "max_daily_loss": self.max_daily_loss,
                "circuit_breaker_tripped": self.circuit_breaker_tripped,
                "circuit_breaker_reason": self.circuit_breaker_reason,
                "max_position_limit": self.max_position_limit,
                "win_rate": win_rate,
                "total_trades": len(self.trade_history),
                "trimester_tier": trimester_tier,
                "projected_bonus_inr": projected_bonus_inr
            },
            "open_orders": [
                {
                    "order_id": o.order_id,
                    "symbol": o.symbol,
                    "side": o.side,
                    "order_type": o.order_type,
                    "price": o.price,
                    "quantity": o.quantity,
                    "queue_ahead": o.queue_ahead
                }
                for o in self.user_orders.values() if o.status == "OPEN" and o.symbol == sym
            ],
            "scenario": {
                "active": self.active_scenario,
                "remaining_seconds": self.scenario_timer,
                "logs": self.scenario_logs[:5]
            }
        }
