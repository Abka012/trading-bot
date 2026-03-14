from typing import Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Trading Bot API",
    description="Backend API for the trading bot application",
    version="1.0.0",
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Trading Bot API", "status": "running"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/data")
async def get_data():
    """Sample data endpoint"""
    return {
        "message": "Hello from Python!",
        "data": [1, 2, 3],
        "trading_pairs": ["BTC/USD", "ETH/USD", "SOL/USD"],
    }


@app.get("/api/market")
async def get_market_data():
    """Get market data"""
    return {
        "BTC/USD": {"price": 45000, "change": 2.5},
        "ETH/USD": {"price": 2500, "change": -1.2},
        "SOL/USD": {"price": 100, "change": 5.3},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
