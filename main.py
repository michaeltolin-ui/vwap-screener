from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import json
import time
import asyncio
import finnhub
import pandas as pd

app = FastAPI()

# Redis connection
redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)

# Finnhub client (replace with your API key)
finnhub_client = finnhub.Client(api_key="YOUR_API_KEY")

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

async def fetch_stock_data(ticker: str, delay: int, demo_mode: bool, interval: str):
    """Fetch stock data using Finnhub, with Redis caching."""
    cache_key = f"stock:{ticker}:{interval}"
    cached_data = redis_client.get(cache_key)
    
    if cached_data and not demo_mode:
        return json.loads(cached_data)
    
    if demo_mode:
        return next((item for item in sample_data if item["ticker"] == ticker), None)
    
    await asyncio.sleep(delay / 1000)  # Apply pacing delay
    try:
        # Fetch 30 days of candles (adjust as needed)
        from_ts = int(time.time() - 86400 * 30)
        to_ts = int(time.time())
        res = finnhub_client.stock_candles(ticker, interval, from_ts, to_ts)
        
        if res['s'] != 'ok' or not res['t']:
            return None
        
        # Convert to DataFrame for processing
        df = pd.DataFrame({
            't': res['t'],
            'o': res['o'],
            'h': res['h'],
            'l': res['l'],
            'c': res['c'],
            'v': res['v']
        })
        df['t'] = pd.to_datetime(df['t'], unit='s')
        
        # Calculate metrics
        last = df['c'].iloc[-1]
        vwap = (df['c'] * df['v']).sum() / df['v'].sum() if df['v'].sum() > 0 else last
        sma8 = df['c'].rolling(8).mean().iloc[-1]
        sma8_slope = (sma8 - df['c'].rolling(8).mean().iloc[-2]) / sma8 * 100 if len(df) >= 8 else 0
        avg_volume = int(df['v'].tail(390).mean() * 30)  # Approx 30d avg (390 min/day * 30 days)
        
        data = {
            "ticker": ticker,
            "avgVol30d": avg_volume,
            "last": last,
            "vwap": vwap,
            "sma8Slope": sma8_slope
        }
        
        # Cache for 1 hour
        redis_client.setex(cache_key, 3600, json.dumps(data))
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Finnhub API error for {ticker}: {str(e)}")

@app.post("/scan")
async def run_scan(request: ScanRequest):
    """Run VWAP snapback scan."""
    results = []
    
    for ticker in request.tickers:
        try:
            data = await fetch_stock_data(ticker, request.pacing_delay, request.demo_mode, request.interval)
            if data and data["avgVol30d"] >= request.min_volume and data["last"] >= 1.005 * data["vwap"] and abs(data["sma8Slope"]) <= 0.05:
                data["priceVwapPct"] = (data["last"] - data["vwap"]) / data["vwap"] * 100
                results.append(data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing {ticker}: {str(e)}")
    
    return {"results": results}
