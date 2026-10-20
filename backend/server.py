import asyncio
import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from backend.engine import MarketEngine

app = FastAPI(title="ApexDeriv - International Derivatives Trading Terminal")

engine = MarketEngine()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def get_index():
    return FileResponse(str(STATIC_DIR / "index.html"))

class OrderRequest(BaseModel):
    symbol: str
    side: str
    order_type: str
    price: float
    quantity: int

class ScenarioRequest(BaseModel):
    scenario_id: str

class SymbolRequest(BaseModel):
    symbol: str

@app.get("/api/state")
def get_state():
    return engine.get_market_state()

@app.post("/api/order")
def place_order(req: OrderRequest):
    res = engine.submit_order(
        symbol=req.symbol,
        side=req.side,
        order_type=req.order_type,
        price=req.price,
        quantity=req.quantity
    )
    return res

@app.post("/api/cancel/{order_id}")
def cancel_order(order_id: str):
    success = engine.cancel_order(order_id)
    return {"success": success}

@app.post("/api/cancel_all")
def cancel_all():
    engine.cancel_all_orders(engine.active_symbol)
    return {"status": "ALL_CANCELLED"}

@app.post("/api/flatten")
def flatten():
    engine.flatten_position(engine.active_symbol)
    return {"status": "FLATTENED"}

@app.post("/api/flatten_all")
def flatten_all_desks():
    engine.flatten_all()
    return {"status": "ALL_FLATTENED"}

@app.post("/api/select_symbol")
def select_symbol(req: SymbolRequest):
    engine.set_active_symbol(req.symbol)
    return {"active_symbol": engine.active_symbol}

@app.post("/api/scenario")
def trigger_scenario(req: ScenarioRequest):
    engine.start_scenario(req.scenario_id)
    return {"status": "SCENARIO_STARTED", "scenario": req.scenario_id}

@app.post("/api/reset_risk")
def reset_risk():
    engine.reset_risk()
    return {"status": "RISK_RESET"}

# WebSocket streaming loop
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Advance simulation tick
            engine.tick()
            state = engine.get_market_state()
            await websocket.send_json(state)
            await asyncio.sleep(0.25)  # 4 updates per second for snappy DOM feel
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS error: {e}")
