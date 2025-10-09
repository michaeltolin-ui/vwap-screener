from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import json
import time
import asyncio

app = FastAPI()

# Redis connection
redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)

# Sample data for Demo Mode
sample_data = [
    {"ticker": "AAPL", "avgVol30d": 12000000, "last": 150.25, "vwap": 149.00, "sma8Slope": 0.02},
    {"ticker": "MSFT", "avgVol30d": 15000000, "last": 305.10, "vwap": 302.50, "sma8Slope": 0.01},
]

class ScanRequest(BaseModel):
    tickers: list[str]
    min_volume: int
    interval: str
    demo_mode: bool
    pacing_delay: int

async def fetch_stock_data(ticker: str, delay: int, demo_mode: bool):
    """Fetch stock data, using Redis cache if available."""
    cache_key = f"stock:{ticker}"
    cached_data = redis_client.get(cache_key)
    
    if cached_data and not demo_mode:
        return json.loads(cached_data)
    
    if demo_mode:
        data = next((item for item in sample_data if item["ticker"] == ticker), None)
    else:
        # Placeholder for real API call (e.g., to Yahoo Finance or another provider)
        await asyncio.sleep(delay / 1000)  # Simulate API delay
        data = None  # Replace with actual API call
    
    if data and not demo_mode:
        redis_client.setex(cache_key, 3600, json.dumps(data))  # Cache for 1 hour
    return data

@app.post("/scan")
async def run_scan(request: ScanRequest):
    """Run VWAP snapback scan."""
    results = []
    
    for i, ticker in enumerate(request.tickers):
        try:
            data = await fetch_stock_data(ticker, request.pacing_delay, request.demo_mode)
            if data and data["avgVol30d"] >= request.min_volume and data["last"] >= 1.005 * data["vwap"] and abs(data["sma8Slope"]) <= 0.05:
                data["priceVwapPct"] = (data["last"] - data["vwap"]) / data["vwap"] * 100
                results.append(data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing {ticker}: {str(e)}")
    
    return {"results": results}
