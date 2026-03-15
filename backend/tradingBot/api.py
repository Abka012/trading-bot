"""
Trading Bot FastAPI Wrapper.

This module provides a FastAPI-based REST API for the trading bot models.
It enables:
- Loading and managing multiple trained models
- Making predictions via API calls
- Retrieving paper trading results and performance metrics
- Real-time market data integration

Example:
    ```python
    from tradingBot.api import app, ModelManager

    # The app can be run with:
    # uvicorn tradingBot.api:app --host 0.0.0.0 --port 8000
    ```

Author: Abka Ferguson
Date: 2026
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Suppress TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# Import model architecture and data fetcher
from dataclasses import dataclass

from tradingBot.data_fetcher import DataFetcher

if TYPE_CHECKING:
    import tensorflow as tf

# =============================================================================
# Pydantic Models for Request/Response
# =============================================================================


class PredictionRequest(BaseModel):
    """Request model for making predictions.

    Attributes:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        model_name: Optional specific model name (defaults to symbol-based model)
        use_custom_model: Whether to use a custom model file path
    """

    symbol: str = Field(..., description="Stock ticker symbol (e.g., 'AAPL', 'MSFT')")
    model_name: str | None = Field(
        default=None, description="Optional specific model name"
    )
    use_custom_model: bool = Field(
        default=False, description="Whether to use a custom model file path"
    )


class PredictionResponse(BaseModel):
    """Response model for predictions.

    Attributes:
        symbol: Stock ticker symbol
        model_name: Name of the model used
        prediction: Raw model prediction value
        signal: Trading signal (-1 to 1, from tanh activation)
        direction: Predicted direction ('UP', 'DOWN', or 'NEUTRAL')
        confidence: Confidence level (0-100%)
        timestamp: When the prediction was made
        current_price: Current market price
    """

    symbol: str
    model_name: str
    prediction: float
    signal: float
    direction: str
    confidence: float
    timestamp: datetime
    current_price: float | None = None


class ModelInfo(BaseModel):
    """Information about a loaded model.

    Attributes:
        name: Model name
        path: File path to the model
        loaded: Whether the model is currently loaded in memory
        symbol: Associated stock symbol
        loaded_at: When the model was loaded
    """

    name: str
    path: str
    loaded: bool
    symbol: str
    loaded_at: datetime | None = None


class PaperTradingResult(BaseModel):
    """Paper trading performance results.

    Attributes:
        symbol: Stock ticker symbol
        total_return: Total return percentage
        total_pnl: Total profit and loss in USD
        win_rate: Win rate percentage
        profit_factor: Profit factor ratio
        sharpe_ratio: Annualized Sharpe ratio
        max_drawdown: Maximum drawdown percentage
        total_trades: Number of trades executed
        start_date: Start date of the trading period
        end_date: End date of the trading period
    """

    symbol: str
    total_return: float
    total_pnl: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    start_date: datetime
    end_date: datetime


class MarketDataResponse(BaseModel):
    """Market data response.

    Attributes:
        symbol: Stock ticker symbol
        price: Current price
        change: Price change percentage
        volume: Trading volume
        high: Day high
        low: Day low
        open: Day open
        previous_close: Previous day's close
        timestamp: Data timestamp
    """

    symbol: str
    price: float
    change: float
    volume: int
    high: float
    low: float
    open: float
    previous_close: float
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check response.

    Attributes:
        status: Service status
        version: API version
        models_loaded: Number of models currently loaded
        timestamp: Current timestamp
    """

    status: str
    version: str
    models_loaded: int
    timestamp: datetime


# =============================================================================
# Model Manager
# =============================================================================


@dataclass
class LoadedModel:
    """Represents a loaded model in memory.

    Attributes:
        model: The Keras model instance
        config: Model configuration
        symbol: Associated stock symbol
        loaded_at: When the model was loaded
        last_used: When the model was last used
    """

    model: Any
    config: "ModelConfigLite"
    symbol: str
    loaded_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class ModelConfigLite:
    window_size: int
    n_features: int


class ModelManager:
    """Manages loading and caching of multiple trading models.

    This class handles:
    - Discovering available models in the artifacts/models directory
    - Loading models on-demand with caching
    - Memory management (unloading unused models)
    - Thread-safe model access

    Attributes:
        models_dir: Directory containing model files
        cache: Dictionary of loaded models
        max_cache_size: Maximum number of models to keep in memory
    """

    def __init__(
        self,
        models_dir: str = str(Path(__file__).parent / "artifacts" / "models"),
        max_cache_size: int = 10,
    ):
        """Initialize the model manager.

        Args:
            models_dir: Directory containing .keras model files
            max_cache_size: Maximum models to cache in memory
        """
        self.models_dir = Path(models_dir)
        self.max_cache_size = max_cache_size
        self._cache: dict[str, LoadedModel] = {}
        self._data_fetchers: dict[str, DataFetcher] = {}

    def discover_models(self) -> list[ModelInfo]:
        """Discover all available model files.

        Returns:
            List of ModelInfo for each discovered model file
        """
        if not self.models_dir.exists():
            return []

        models = []
        for model_file in self.models_dir.glob("*.keras"):
            # Extract symbol from filename (e.g., 'aapl_model.keras' -> 'AAPL')
            name = model_file.stem.replace("_model", "")
            symbol = name.upper()

            models.append(
                ModelInfo(
                    name=name,
                    path=str(model_file),
                    loaded=name in self._cache,
                    symbol=symbol,
                    loaded_at=self._cache.get(name, None)
                    and self._cache[name].loaded_at,
                )
            )

        return models

    def get_model(self, symbol: str) -> LoadedModel | None:
        """Get a model by symbol, loading it if necessary.

        Args:
            symbol: Stock ticker symbol

        Returns:
            LoadedModel instance or None if not found
        """
        symbol_lower = symbol.lower()
        model_name = f"{symbol_lower}_model"

        # Check if already in cache
        if model_name in self._cache:
            self._cache[model_name].last_used = datetime.now()
            return self._cache[model_name]

        # Find model file
        model_path = self.models_dir / f"{symbol_lower}_model.keras"
        if not model_path.exists():
            return None

        # Load the model
        try:
            print(f"Loading model for {symbol} from {model_path}...")
            import os

            if os.getenv("DISABLE_TENSORFLOW", "false").lower() in (
                "1",
                "true",
                "yes",
            ):
                raise RuntimeError("TensorFlow disabled by DISABLE_TENSORFLOW")

            import tensorflow as tf

            keras_model = tf.keras.models.load_model(str(model_path))

            # Create default config
            config = ModelConfigLite(window_size=60, n_features=15)

            loaded_model = LoadedModel(model=keras_model, config=config, symbol=symbol)
            self._cache[model_name] = loaded_model

            # Evict oldest if cache is full
            if len(self._cache) > self.max_cache_size:
                self._evict_oldest()

            print(f"Model for {symbol} loaded successfully.")
            return loaded_model

        except Exception as e:
            print(f"Error loading model for {symbol}: {e}")
            return None

    def _evict_oldest(self) -> None:
        """Evict the oldest model from cache."""
        if not self._cache:
            return

        oldest_name = min(self._cache.keys(), key=lambda k: self._cache[k].last_used)
        del self._cache[oldest_name]
        print(f"Evicted model {oldest_name} from cache.")

    def get_data_fetcher(self, symbol: str) -> DataFetcher:
        """Get or create a data fetcher for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            DataFetcher instance
        """
        if symbol not in self._data_fetchers:
            self._data_fetchers[symbol] = DataFetcher(symbol=symbol, window_size=60)

        return self._data_fetchers[symbol]

    def unload_model(self, symbol: str) -> bool:
        """Unload a specific model from cache.

        Args:
            symbol: Stock ticker symbol

        Returns:
            True if model was unloaded, False if not found
        """
        model_name = f"{symbol.lower()}_model"
        if model_name in self._cache:
            del self._cache[model_name]
            return True
        return False

    def clear_cache(self) -> None:
        """Clear all models from cache."""
        self._cache.clear()
        self._data_fetchers.clear()


# =============================================================================
# FastAPI Application
# =============================================================================


app = FastAPI(
    title="Trading Bot API",
    description="REST API for trading bot model predictions and paper trading results",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://*.render.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize model manager
model_manager = ModelManager(
    models_dir=Path(__file__).parent / "artifacts" / "models", max_cache_size=10
)


# =============================================================================
# API Endpoints
# =============================================================================


@app.get("/", response_model=dict[str, str])
async def root() -> dict[str, str]:
    """Root endpoint with welcome message.

    Returns:
        Welcome message and API info
    """
    return {
        "message": "Welcome to Trading Bot API v2",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        Service health status
    """
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        models_loaded=len(model_manager._cache),
        timestamp=datetime.now(),
    )


@app.get("/api/models", response_model=list[ModelInfo])
async def list_models() -> list[ModelInfo]:
    """List all available models.

    Returns:
        List of all discovered models with their status
    """
    return model_manager.discover_models()


@app.get("/api/models/{symbol}", response_model=ModelInfo | dict)
async def get_model_info(symbol: str) -> ModelInfo | dict:
    """Get information about a specific model.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Model information or error if not found
    """
    models = model_manager.discover_models()
    symbol_lower = symbol.lower()

    for model in models:
        if model.name.lower() == symbol_lower or model.symbol.lower() == symbol_lower:
            return model

    raise HTTPException(status_code=404, detail=f"Model not found for symbol: {symbol}")


@app.post("/api/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest) -> PredictionResponse:
    """Make a prediction for a given symbol.

    This endpoint:
    1. Loads the appropriate model (or uses cached version)
    2. Fetches current market data
    3. Prepares input features
    4. Runs model inference
    5. Returns prediction with trading signal

    Args:
        request: Prediction request with symbol and options

    Returns:
        Prediction response with signal and confidence
    """
    symbol = request.symbol.upper()

    # Get or load the model
    loaded_model = model_manager.get_model(symbol)
    if loaded_model is None:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found for symbol: {symbol}. Available models: {[m.name for m in model_manager.discover_models()]}",
        )

    try:
        # Fetch market data
        data_fetcher = model_manager.get_data_fetcher(symbol)
        df = data_fetcher.update_data()

        # Get current price
        current_price = float(df["close"].iloc[-1]) if not df.empty else None

        # Prepare model input
        model_input = data_fetcher.prepare_input(df)

        # Make prediction
        prediction = loaded_model.model.predict(model_input, verbose=0)[0, 0]
        prediction_float = float(prediction)

        # Convert to trading signal using tanh
        alpha = 5.0  # Scaling factor
        signal = float(np.tanh(alpha * prediction_float))

        # Determine direction and confidence
        if signal > 0.1:
            direction = "UP"
            confidence = min(abs(signal) * 100, 100)
        elif signal < -0.1:
            direction = "DOWN"
            confidence = min(abs(signal) * 100, 100)
        else:
            direction = "NEUTRAL"
            confidence = (1 - abs(signal)) * 100

        return PredictionResponse(
            symbol=symbol,
            model_name=loaded_model.symbol,
            prediction=prediction_float,
            signal=signal,
            direction=direction,
            confidence=confidence,
            timestamp=datetime.now(),
            current_price=current_price,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.get("/api/market/{symbol}", response_model=MarketDataResponse)
async def get_market_data(symbol: str) -> MarketDataResponse:
    """Get current market data for a symbol.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Current market data
    """
    symbol = symbol.upper()

    try:
        data_fetcher = model_manager.get_data_fetcher(symbol)
        df = data_fetcher.update_data()

        if df.empty:
            raise HTTPException(
                status_code=404, detail=f"No data available for symbol: {symbol}"
            )

        # Get latest row
        latest = df.iloc[-1]
        prev_close = df["close"].iloc[-2] if len(df) > 1 else latest["close"]

        change = ((latest["close"] - prev_close) / prev_close) * 100

        return MarketDataResponse(
            symbol=symbol,
            price=float(latest["close"]),
            change=float(change),
            volume=int(latest["volume"]),
            high=float(latest["high"]),
            low=float(latest["low"]),
            open=float(latest["open"]),
            previous_close=float(prev_close),
            timestamp=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market data error: {str(e)}")


@app.get(
    "/api/paper-trading/{symbol}/results", response_model=PaperTradingResult | dict
)
async def get_paper_trading_results(
    symbol: str,
) -> PaperTradingResult | dict:
    """Get paper trading results for a symbol.

    This endpoint reads historical paper trading results from the outputs folder.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Paper trading performance metrics
    """
    symbol_lower = symbol.lower()
    outputs_dir = Path(__file__).parent / "outputs"
    trades_dir = outputs_dir / "trades"
    equity_dir = outputs_dir / "equity"

    # Find the most recent trades file for this symbol
    if not trades_dir.exists():
        return {"error": "No paper trading results available"}

    trade_files = sorted(
        trades_dir.glob(f"paper_trading_trades_{symbol_lower}_*.csv"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )

    if not trade_files:
        # Try generic pattern
        trade_files = sorted(
            trades_dir.glob("paper_trading_trades_*.csv"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

    if not trade_files:
        return {"error": "No paper trading results found"}

    try:
        # Read trades file
        trades_df = pd.read_csv(trade_files[0])

        # Calculate metrics
        if trades_df.empty or "pnl" not in trades_df.columns:
            return {"error": "Invalid trades data format"}

        total_pnl = float(trades_df["pnl"].sum())
        winning_trades = trades_df[trades_df["pnl"] > 0]
        losing_trades = trades_df[trades_df["pnl"] < 0]

        win_rate = (
            len(winning_trades) / len(trades_df) * 100 if len(trades_df) > 0 else 0
        )

        gross_profit = winning_trades["pnl"].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades["pnl"].sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Read equity curve for Sharpe ratio and drawdown
        equity_files = sorted(
            equity_dir.glob("paper_trading_equity_*.csv"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        sharpe_ratio = 0.0
        max_drawdown = 0.0
        total_return = 0.0
        start_date = datetime.now()
        end_date = datetime.now()

        if equity_files:
            equity_df = pd.read_csv(equity_files[0])
            if "equity" in equity_df.columns and len(equity_df) > 1:
                # Calculate returns
                returns = equity_df["equity"].pct_change().dropna()

                # Annualized Sharpe ratio (assuming daily returns)
                if returns.std() > 0:
                    sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)

                # Maximum drawdown
                cumulative = (1 + returns).cumprod()
                running_max = cumulative.cummax()
                drawdown = (cumulative - running_max) / running_max
                max_drawdown = float(drawdown.min()) * 100

                # Total return
                total_return = (
                    (equity_df["equity"].iloc[-1] / equity_df["equity"].iloc[0]) - 1
                ) * 100

                # Dates
                if "timestamp" in equity_df.columns:
                    start_date = pd.to_datetime(equity_df["timestamp"].iloc[0])
                    end_date = pd.to_datetime(equity_df["timestamp"].iloc[-1])

        return PaperTradingResult(
            symbol=symbol,
            total_return=total_return,
            total_pnl=total_pnl,
            win_rate=win_rate,
            profit_factor=profit_factor if profit_factor != float("inf") else 999.99,
            sharpe_ratio=float(sharpe_ratio),
            max_drawdown=max_drawdown,
            total_trades=len(trades_df),
            start_date=start_date,
            end_date=end_date,
        )

    except Exception as e:
        return {"error": f"Error reading results: {str(e)}"}


@app.get("/api/paper-trading/results", response_model=list[dict])
async def get_all_paper_trading_results() -> list[dict]:
    """Get paper trading results for all symbols.

    Returns:
        List of results for each symbol with available data
    """
    models = model_manager.discover_models()
    results = []

    for model in models:
        symbol = model.symbol
        result = await get_paper_trading_results(symbol)
        if "error" not in result:
            result["model_name"] = model.name
            results.append(result)

    return results


@app.delete("/api/models/{symbol}/unload")
async def unload_model(symbol: str) -> dict:
    """Unload a model from cache.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Status message
    """
    if model_manager.unload_model(symbol):
        return {"status": "success", "message": f"Model for {symbol} unloaded"}
    raise HTTPException(status_code=404, detail=f"Model not found for symbol: {symbol}")


@app.delete("/api/models/cache/clear")
async def clear_model_cache() -> dict:
    """Clear all models from cache.

    Returns:
        Status message
    """
    model_manager.clear_cache()
    return {"status": "success", "message": "All models unloaded from cache"}


# =============================================================================
# Live Trading Endpoints (Alpaca)
# =============================================================================


class LiveTradingStatus(BaseModel):
    """Live trading status response.

    Attributes:
        connected: Whether Alpaca is connected
        trading_mode: Paper or live trading
        market_open: Whether market is currently open
        account_id: Account ID (masked)
        cash: Available cash
        portfolio_value: Total portfolio value
        positions_count: Number of open positions
        timestamp: Current timestamp
    """

    connected: bool
    trading_mode: str
    market_open: bool
    account_id: str | None
    cash: float | None
    portfolio_value: float | None
    positions_count: int
    timestamp: datetime


class LivePosition(BaseModel):
    """Live position information.

    Attributes:
        symbol: Stock ticker symbol
        qty: Number of shares
        side: Long or short
        entry_price: Entry price
        current_price: Current price
        market_value: Current market value
        unrealized_pl: Unrealized profit/loss
        unrealized_plpc: Unrealized P&L percentage
    """

    symbol: str
    qty: float
    side: str
    entry_price: float
    current_price: float
    market_value: float
    unrealized_pl: float
    unrealized_plpc: float


class PlaceOrderRequest(BaseModel):
    """Request to place a live order.

    Attributes:
        symbol: Stock ticker symbol
        qty: Number of shares
        side: Buy or sell
        order_type: Market, limit, stop, etc.
        limit_price: Limit price for limit orders
        stop_loss: Stop loss price
        take_profit: Take profit price
    """

    symbol: str
    qty: float = 1
    side: str = "buy"
    order_type: str = "market"
    limit_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None


class OrderResponse(BaseModel):
    """Response from placing an order.

    Attributes:
        success: Whether order was successful
        order_id: Alpaca order ID
        symbol: Stock symbol
        side: Buy or sell
        qty: Number of shares
        price: Execution price
        status: Order status
        message: Error message if failed
    """

    success: bool
    order_id: str | None = None
    symbol: str | None = None
    side: str | None = None
    qty: float | None = None
    price: float | None = None
    status: str | None = None
    message: str | None = None


def _get_alpaca_client() -> AlpacaClient | None:
    """Get or create Alpaca client instance.

    Returns:
        AlpacaClient instance or None if not configured
    """
    try:
        return AlpacaClient()
    except ValueError:
        return None


@app.get("/api/live/status", response_model=LiveTradingStatus)
async def get_live_trading_status() -> LiveTradingStatus:
    """Get live trading status and account info.

    Returns:
        Current trading status and account summary
    """
    client = _get_alpaca_client()

    if client is None:
        return LiveTradingStatus(
            connected=False,
            trading_mode="not_configured",
            market_open=False,
            account_id=None,
            cash=None,
            portfolio_value=None,
            positions_count=0,
            timestamp=datetime.now(),
        )

    try:
        account = client.get_account()
        positions = client.get_all_positions()
        market_open = client.is_market_open()

        return LiveTradingStatus(
            connected=True,
            trading_mode=client.trading_mode.value,
            market_open=market_open,
            account_id=str(account.account_id)[:8] + "..."
            if account.account_id
            else None,
            cash=account.cash,
            portfolio_value=account.portfolio_value,
            positions_count=len(positions),
            timestamp=datetime.now(),
        )
    except Exception as e:
        return LiveTradingStatus(
            connected=False,
            trading_mode="error",
            market_open=False,
            account_id=None,
            cash=None,
            portfolio_value=None,
            positions_count=0,
            timestamp=datetime.now(),
        )


@app.get("/api/live/positions", response_model=list[LivePosition])
async def get_live_positions() -> list[LivePosition]:
    """Get all open live positions.

    Returns:
        List of current positions
    """
    client = _get_alpaca_client()

    if client is None:
        raise HTTPException(status_code=503, detail="Alpaca not configured")

    try:
        positions = client.get_all_positions()
        return [
            LivePosition(
                symbol=pos.symbol,
                qty=abs(float(pos.qty)),
                side=pos.side,
                entry_price=float(pos.avg_entry_price),
                current_price=float(pos.current_price),
                market_value=float(pos.market_value),
                unrealized_pl=float(pos.unrealized_pl) if pos.unrealized_pl else 0,
                unrealized_plpc=float(pos.unrealized_plpc)
                if pos.unrealized_plpc
                else 0,
            )
            for pos in positions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/live/account")
async def get_live_account() -> dict:
    """Get detailed account information.

    Returns:
        Full account details from Alpaca
    """
    client = _get_alpaca_client()

    if client is None:
        raise HTTPException(status_code=503, detail="Alpaca not configured")

    try:
        account = client.get_account()
        return {
            "account_id": account.account_id,
            "account_number": account.account_number,
            "status": account.status,
            "crypto_status": account.crypto_status,
            "currency": account.currency,
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "buying_power": float(account.buying_power),
            "daytrading_buying_power": float(account.daytrading_buying_power),
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
            "pattern_day_trader": account.pattern_day_trader,
            "trade_suspended": account.trade_suspended_by_user,
            "sma": float(account.sma) if account.sma else 0,
            "multiplier": account.multiplier,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/live/order", response_model=OrderResponse)
async def place_live_order(request: PlaceOrderRequest) -> OrderResponse:
    """Place a live trading order.

    Args:
        request: Order request with symbol, qty, side, etc.

    Returns:
        Order response with execution details
    """
    client = _get_alpaca_client()

    if client is None:
        return OrderResponse(
            success=False, message="Alpaca not configured. Check your .env file."
        )

    try:
        # Check market status
        if not client.is_market_open():
            return OrderResponse(success=False, message="Market is currently closed")

        # Create order config
        order_config = OrderConfig(
            symbol=request.symbol.upper(),
            qty=request.qty,
            side=request.side.lower(),
            order_type=request.order_type.lower(),
            limit_price=request.limit_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
        )

        # Place order
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


@app.post("/api/live/order/close/{symbol}")
async def close_live_position(symbol: str) -> OrderResponse:
    """Close all positions for a symbol.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Order response
    """
    client = _get_alpaca_client()

    if client is None:
        return OrderResponse(
            success=False, message="Alpaca not configured. Check your .env file."
        )

    try:
        result = client.close_position(symbol.upper())

        return OrderResponse(
            success=result.success,
            order_id=result.order_id,
            symbol=result.symbol,
            side=result.side,
            status=result.status,
            message=result.message,
        )

    except Exception as e:
        return OrderResponse(success=False, message=str(e))


@app.post("/api/live/orders/close-all")
async def close_all_live_positions() -> dict:
    """Close all open positions.

    Returns:
        Summary of closed positions
    """
    client = _get_alpaca_client()

    if client is None:
        raise HTTPException(status_code=503, detail="Alpaca not configured")

    try:
        results = client.close_all_positions()
        return {
            "success": True,
            "positions_closed": len(results),
            "results": [
                {"symbol": r.symbol, "success": r.success, "message": r.message}
                for r in results
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/live/orders")
async def get_live_orders(status: str = "open") -> list[dict]:
    """Get live orders by status.

    Args:
        status: Order status (open, closed, all)

    Returns:
        List of orders
    """
    client = _get_alpaca_client()

    if client is None:
        raise HTTPException(status_code=503, detail="Alpaca not configured")

    try:
        orders = client.get_orders(status=status.lower())
        return [
            {
                "id": order.id,
                "symbol": order.symbol,
                "side": order.side.value,
                "qty": float(order.qty),
                "type": order.type.value,
                "status": order.status.value,
                "submitted_at": order.submitted_at.isoformat()
                if order.submitted_at
                else None,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price)
                if order.filled_avg_price
                else 0,
            }
            for order in orders
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/live/order/{order_id}")
async def cancel_live_order(order_id: str) -> dict:
    """Cancel a live order.

    Args:
        order_id: Alpaca order ID

    Returns:
        Cancellation status
    """
    client = _get_alpaca_client()

    if client is None:
        raise HTTPException(status_code=503, detail="Alpaca not configured")

    try:
        success = client.cancel_order(order_id)
        return {"success": success, "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/live/portfolio")
async def get_live_portfolio() -> dict:
    """Get comprehensive portfolio summary.

    Returns:
        Portfolio summary with account and positions
    """
    client = _get_alpaca_client()

    if client is None:
        raise HTTPException(status_code=503, detail="Alpaca not configured")

    try:
        return client.get_portfolio_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
