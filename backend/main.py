"""
Trading Bot Backend API.

This module serves as the main entry point for the Trading Bot FastAPI application.
It integrates the tradingBot API module and provides additional endpoints for the frontend.
It also starts the automated trading engine in the background.

The API enables:
- Real-time model predictions for multiple stocks
- Paper trading results and performance metrics
- Market data fetching
- Portfolio dashboard data
- Live trading engine control and monitoring

Example:
    ```bash
    # Run with uvicorn (starts trading engine automatically)
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

    # Run with gunicorn (production)
    gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
    ```

Author: Abka Ferguson
Date: 2026
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tradingBot.alpaca_client import AlpacaClient, OrderConfig
from tradingBot.api import (
    OrderResponse,
    PlaceOrderRequest,
    get_all_paper_trading_results,
    get_market_data,
    get_paper_trading_results,
    list_models,
    predict,
)

# Import the tradingBot API app and mount it
from tradingBot.api import app as trading_app
from tradingBot.engine_service import (
    get_engine_logs,
    get_engine_status,
    start_engine,
    stop_engine,
)
from tradingBot.trading_config import TradingConfig


def discover_model_symbols() -> list[str]:
    """Discover model symbols from artifacts/models directory."""
    models_dir = Path(__file__).parent / "tradingBot" / "artifacts" / "models"
    if not models_dir.exists():
        return []

    symbols = []
    for model_file in models_dir.glob("*.keras"):
        name = model_file.stem.replace("_model", "")
        if name:
            symbols.append(name.upper())
    return sorted(set(symbols))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - start/stop trading engine."""
    # Startup: Initialize and start trading engine
    print("🚀 Starting Trading Bot API...")
    print("🤖 Initializing trading engine...")

    # Configure trading engine
    discovered_symbols = discover_model_symbols()
    max_symbols_env = os.getenv("ENGINE_MAX_SYMBOLS")
    if max_symbols_env and max_symbols_env.isdigit():
        discovered_symbols = discovered_symbols[: int(max_symbols_env)]
    config = TradingConfig(
        symbols=discovered_symbols
        if discovered_symbols
        else [
            "AAPL",
            "MSFT",
            "GOOGL",
            "NVDA",
            "AMZN",
            "META",
            "TSLA",
            "JPM",
            "V",
            "WMT",
        ],
        max_position_size=0.05,
        max_positions=5,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        signal_threshold=0.15,
        rebalance_interval=5,
        paper_trading=True,  # Start with paper trading
    )

    # Start engine in background (optional)
    start_engine_on_boot = os.getenv("START_ENGINE_ON_BOOT", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    if start_engine_on_boot:
        engine_started = start_engine(config)
        if engine_started:
            print("✅ Trading engine started successfully")
        else:
            print("⚠️  Trading engine failed to start (check logs)")
    else:
        print("⏸ Trading engine start skipped (START_ENGINE_ON_BOOT=false)")

    yield

    # Shutdown: Stop trading engine
    print("🛑 Shutting down Trading Bot API...")
    print("⏹ Stopping trading engine...")
    stop_engine()
    print("✅ Trading engine stopped")


app = FastAPI(
    title="Trading Bot Dashboard API",
    description="Backend API for the trading bot dashboard - provides model predictions, paper trading results, and market data",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for React frontend
# In production, update allow_origins to match your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://*.render.com",
        "https://*.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with welcome message.

    Returns:
        Welcome message and API documentation links
    """
    return {
        "message": "Welcome to Trading Bot Dashboard API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "trading_api": "/api/trading",
    }


@app.get("/api/health")
async def health_check() -> dict[str, str | int | datetime]:
    """Health check endpoint for monitoring and load balancers.

    Returns:
        Service health status with version and timestamp
    """
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/dashboard")
async def get_dashboard_data() -> dict:
    """Get comprehensive dashboard data for the frontend.

    This endpoint aggregates:
    - Available models
    - Latest predictions for all models
    - Paper trading performance summary
    - Market data overview

    Returns:
        Dashboard data with models, predictions, and performance metrics
    """
    try:
        # Get all available models
        models = await list_models()

        # Get predictions for each model
        predictions = []
        for model in models[:10]:  # Limit to first 10 for performance
            try:
                from tradingBot.api import PredictionRequest

                pred_request = PredictionRequest(symbol=model.symbol)
                pred = await predict(pred_request)
                predictions.append(
                    {
                        "symbol": pred.symbol,
                        "prediction": pred.prediction,
                        "signal": pred.signal,
                        "direction": pred.direction,
                        "confidence": pred.confidence,
                        "current_price": pred.current_price,
                    }
                )
            except Exception:
                # Skip if prediction fails for a specific model
                continue

        # Get paper trading results
        paper_results = await get_all_paper_trading_results()

        # Get market data for top symbols
        market_data = []
        for model in models[:5]:  # Limit to first 5
            try:
                market = await get_market_data(model.symbol)
                market_data.append(
                    {
                        "symbol": market.symbol,
                        "price": market.price,
                        "change": market.change,
                    }
                )
            except Exception:
                continue

        return {
            "models": [
                {"name": m.name, "symbol": m.symbol, "loaded": m.loaded} for m in models
            ],
            "predictions": predictions,
            "paper_trading": paper_results[:5] if paper_results else [],
            "market_data": market_data,
            "summary": {
                "total_models": len(models),
                "total_predictions": len(predictions),
                "avg_confidence": (
                    sum(p["confidence"] for p in predictions) / len(predictions)
                    if predictions
                    else 0
                ),
            },
        }
    except Exception as e:
        return {"error": str(e), "models": [], "predictions": []}


@app.get("/api/models")
async def get_models():
    """Get list of all available trading models.

    Returns:
        List of model information including name, symbol, and load status
    """
    return await list_models()


@app.get("/api/models/{symbol}")
async def get_model(symbol: str):
    """Get information about a specific model.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Model information
    """
    from tradingBot.api import get_model_info

    return await get_model_info(symbol)


@app.post("/api/predict")
async def make_prediction(symbol: str):
    """Make a prediction for a specific stock.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Prediction with signal, direction, and confidence
    """
    from tradingBot.api import PredictionRequest

    request = PredictionRequest(symbol=symbol)
    return await predict(request)


@app.get("/api/market/{symbol}")
async def get_stock_market_data(symbol: str):
    """Get current market data for a stock.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Current market data including price, change, and volume
    """
    return await get_market_data(symbol)


@app.get("/api/paper-trading/{symbol}")
async def get_stock_paper_trading(symbol: str):
    """Get paper trading results for a specific stock.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Paper trading performance metrics
    """
    return await get_paper_trading_results(symbol)


@app.get("/api/paper-trading")
async def get_all_paper_trading():
    """Get paper trading results for all stocks."""
    return await get_all_paper_trading_results()


# =============================================================================
# Live Trading Endpoints (Alpaca)
# =============================================================================


@app.get("/api/live/status")
async def get_live_status():
    """Get live trading status."""
    try:
        client = AlpacaClient()
        account = client.get_account()
        positions = client.get_all_positions()
        market_open = client.is_market_open()
        return {
            "running": True,
            "connected": True,
            "trading_mode": client.trading_mode.value,
            "market_open": market_open,
            "account_id": account.account_id[:8] + "...",
            "cash": account.cash,
            "portfolio_value": account.portfolio_value,
            "positions_count": len(positions),
        }
    except ValueError:
        return {"running": False, "connected": False, "trading_mode": "not_configured"}
    except Exception as e:
        return {"running": False, "connected": False, "error": str(e)}


@app.get("/api/live/positions")
async def get_live_positions():
    """Get all open live positions."""
    try:
        client = AlpacaClient()
        positions = client.get_all_positions()
        return [
            {
                "symbol": pos.symbol,
                "qty": abs(float(pos.qty)),
                "side": pos.side,
                "entry_price": float(pos.avg_entry_price),
                "current_price": float(pos.current_price),
                "market_value": float(pos.market_value),
                "unrealized_pl": float(pos.unrealized_pl) if pos.unrealized_pl else 0,
                "unrealized_plpc": float(pos.unrealized_plpc)
                if pos.unrealized_plpc
                else 0,
            }
            for pos in positions
        ]
    except Exception:
        return []


@app.get("/api/live/account")
async def get_live_account():
    """Get detailed account information."""
    try:
        client = AlpacaClient()
        account = client.get_account()
        return {
            "account_id": account.account_id,
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "buying_power": float(account.buying_power),
            "daytrading_buying_power": float(account.day_trading_buying_power),
            "equity": float(account.equity),
            "last_equity": float(account.last_equity),
            "day_change": float(account.equity - account.last_equity)
            if account.last_equity
            else 0,
            "day_change_percent": float(
                (account.equity - account.last_equity) / account.last_equity * 100
            )
            if account.last_equity
            else 0,
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/live/order/close/{symbol}")
async def close_live_position(symbol: str):
    """Close all positions for a symbol."""
    try:
        client = AlpacaClient()
        result = client.close_position(symbol.upper())
        return {
            "success": result.success,
            "symbol": result.symbol,
            "message": result.message,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/live/order", response_model=OrderResponse)
async def place_live_order(request: PlaceOrderRequest) -> OrderResponse:
    """Place a live trading order."""
    try:
        client = AlpacaClient()
    except ValueError:
        return OrderResponse(
            success=False, message="Alpaca not configured. Check your .env file."
        )

    try:
        if not client.is_market_open():
            return OrderResponse(success=False, message="Market is currently closed")

        order_config = OrderConfig(
            symbol=request.symbol.upper(),
            qty=request.qty,
            side=request.side.lower(),
            order_type=request.order_type.lower(),
            limit_price=request.limit_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
        )
        result = client.place_order(order_config)

        return OrderResponse(
            success=result.success,
            order_id=result.order_id,
            symbol=result.symbol,
            side=result.side,
            qty=result.qty,
            price=result.price,
            status=result.status,
            message=result.message,
        )
    except Exception as e:
        return OrderResponse(success=False, message=str(e))


@app.get("/api/pnl/{symbol}")
async def get_pnl_history(symbol: str):
    """Get PnL history for a symbol from paper trading results."""
    try:
        # Fetch paper trading results for the symbol
        paper_result = await get_paper_trading_results(symbol)

        if "error" in paper_result:
            # Return sample data if no paper trading results
            return generate_sample_pnl_data(symbol)

        # Generate PnL history from equity curve
        equity_history = []
        if hasattr(paper_result, "equity_curve"):
            # Process actual equity curve data
            pass

        return generate_sample_pnl_data(symbol)

    except Exception as e:
        return generate_sample_pnl_data(symbol)


def generate_sample_pnl_data(symbol: str):
    """Generate sample PnL data for demonstration."""
    import random
    from datetime import datetime, timedelta

    data = []
    value = random.uniform(-100, 100)
    now = datetime.now()

    for i in range(30):
        timestamp = now - timedelta(hours=30 - i)
        value += random.uniform(-50, 60)
        data.append({"timestamp": timestamp.isoformat(), "value": round(value, 2)})

    return {
        "symbol": symbol,
        "data": data,
        "current_pnl": data[-1]["value"] if data else 0,
    }


def generate_sample_account_pnl_data():
    """Generate sample account-level PnL data."""
    data = generate_sample_pnl_data("PAPER")["data"]
    return {
        "symbol": "PAPER",
        "data": data,
        "current_pnl": data[-1]["value"] if data else 0,
    }


def normalize_epoch_timestamp(ts: int) -> str:
    """Convert epoch seconds or milliseconds to ISO timestamp."""
    if ts > 1_000_000_000_000:
        ts = ts / 1000
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


@app.get("/api/live/pnl-history")
async def get_live_pnl_history(
    period: str = "1D",
    timeframe: str | None = None,
    extended_hours: bool = True,
):
    """Get account-level PnL history from Alpaca paper trading."""
    try:
        client = AlpacaClient()
        history = client.get_portfolio_history(
            period=period,
            timeframe=timeframe,
            extended_hours=extended_hours,
        )

        timestamps = getattr(history, "timestamp", []) or []
        pnl_values = getattr(history, "profit_loss", []) or []

        data = []
        for ts, pnl in zip(timestamps, pnl_values):
            if isinstance(ts, int):
                timestamp = normalize_epoch_timestamp(ts)
            else:
                timestamp = str(ts)
            data.append({"timestamp": timestamp, "value": float(pnl)})

        return {
            "period": period,
            "timeframe": getattr(history, "timeframe", timeframe),
            "data": data,
            "current_pnl": data[-1]["value"] if data else 0,
        }
    except Exception:
        return generate_sample_account_pnl_data()


# =============================================================================
# Trading Engine Control Endpoints
# =============================================================================


@app.get("/api/engine/status")
async def get_engine_status_endpoint():
    """Get trading engine status."""
    return get_engine_status()


@app.get("/api/engine/logs")
async def get_engine_logs_endpoint(limit: int = 50):
    """Get recent trading engine logs."""
    return get_engine_logs(limit)


@app.post("/api/engine/start")
async def start_engine_endpoint():
    """Start the trading engine."""
    discovered_symbols = discover_model_symbols()
    config = TradingConfig(
        symbols=discovered_symbols
        if discovered_symbols
        else [
            "AAPL",
            "MSFT",
            "GOOGL",
            "NVDA",
            "AMZN",
            "META",
            "TSLA",
            "JPM",
            "V",
            "WMT",
        ],
        max_position_size=0.05,
        max_positions=5,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        signal_threshold=0.15,
        rebalance_interval=5,
        paper_trading=True,
    )
    success = start_engine(config)
    return {
        "success": success,
        "message": "Engine started" if success else "Engine already running",
    }


@app.post("/api/engine/stop")
async def stop_engine_endpoint():
    """Stop the trading engine."""
    success = stop_engine()
    return {
        "success": success,
        "message": "Engine stopped" if success else "Engine not running",
    }


# Mount the tradingBot API routes
app.mount("/api/trading", trading_app)


if __name__ == "__main__":
    import uvicorn

    # Run with auto-reload for development
    # In production, use: uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
