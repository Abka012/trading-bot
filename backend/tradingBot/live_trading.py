"""
Live Trading Engine with Alpaca Integration.

This module implements an automated live trading system that:
1. Loads trained models for multiple stocks
2. Fetches real-time market data
3. Generates predictions using ML models
4. Executes trades via Alpaca API based on predictions
5. Manages positions with stop-loss and take-profit
6. Tracks performance and logs all trades

The engine supports:
- Multi-symbol trading with individual models
- Configurable risk management
- Position sizing based on signal strength
- Real-time monitoring and logging

Example:
    ```python
    from tradingBot.live_trading import LiveTradingEngine, TradingConfig

    config = TradingConfig(
        symbols=["AAPL", "MSFT", "GOOGL"],
        max_position_size=0.1,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
    )

    engine = LiveTradingEngine(config)
    engine.start()
    ```

Author: Abka Ferguson
Date: 2026
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import tensorflow as tf

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tradingBot.alpaca_client import (
    AccountInfo,
    AlpacaClient,
    OrderConfig,
    TradeResult,
    TradingMode,
)
from tradingBot.data_fetcher import DataFetcher
from tradingBot.model import ModelConfig, build_model
from tradingBot.trading_config import TradingConfig

# Suppress TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"


# TradingConfig moved to trading_config.py to avoid heavy imports on startup.


@dataclass
class PositionInfo:
    """Information about an open position.

    Attributes:
        symbol: Stock ticker symbol
        entry_price: Price at entry
        entry_time: When position was opened
        qty: Number of shares
        side: Long or short
        model_prediction: Prediction at entry
        stop_loss: Stop loss price level
        take_profit: Take profit price level
        order_id: Alpaca order ID
    """

    symbol: str
    entry_price: float
    entry_time: datetime
    qty: float
    side: str
    model_prediction: float
    stop_loss: float
    take_profit: float
    order_id: str | None = None


@dataclass
class TradeLog:
    """Log entry for a completed trade.

    Attributes:
        timestamp: When the trade occurred
        symbol: Stock ticker symbol
        side: Buy or sell
        qty: Number of shares
        price: Execution price
        order_id: Alpaca order ID
        pnl: Profit and loss (for closing trades)
        reason: Why the trade was executed
        model_prediction: Model prediction at time of trade
    """

    timestamp: datetime
    symbol: str
    side: str
    qty: float
    price: float
    order_id: str
    pnl: float = 0.0
    reason: str = ""
    model_prediction: float = 0.0


class LiveTradingEngine:
    """Automated live trading engine using Alpaca API.

    This engine orchestrates the entire trading process:
    1. Initializes Alpaca client and loads models
    2. Continuously fetches market data
    3. Generates predictions using ML models
    4. Opens/closes positions based on signals
    5. Manages risk with stop-loss and take-profit
    6. Logs all trades and performance metrics

    The engine runs in a loop, checking for trading opportunities
    at configurable intervals. It respects market hours and can
    be configured for paper trading or live trading.

    Attributes:
        config: Trading configuration
        alpaca_client: Alpaca API client instance
        models: Dictionary of loaded models by symbol
        data_fetchers: Dictionary of data fetchers by symbol
        positions: Currently open positions
        trade_history: History of executed trades
    """

    def __init__(self, config: TradingConfig):
        """Initialize the live trading engine.

        Args:
            config: Trading configuration parameters
        """
        self.config = config
        self.alpaca_client: AlpacaClient | None = None
        self.models: dict[str, tf.keras.Model] = {}
        self.data_fetchers: dict[str, DataFetcher] = {}
        self.positions: dict[str, PositionInfo] = {}
        self.trade_history: list[TradeLog] = []
        self._running = False
        self._stop_event = threading.Event()
        self._trade_counts: dict[str, int] = {}  # Trades per symbol today
        self._last_rebalance: datetime | None = None

        # Create output directories
        Path(self.config.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.data_dir, "logs").mkdir(exist_ok=True)
        Path(self.config.data_dir, "trades").mkdir(exist_ok=True)
        Path(self.config.data_dir, "equity").mkdir(exist_ok=True)

        # Setup logging
        self._log_file = Path(
            self.config.data_dir,
            "logs",
            f"trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        )

        self._log("LiveTradingEngine initialized")
        self._log(f"Trading mode: {'PAPER' if config.paper_trading else 'LIVE'}")
        self._log(f"Symbols: {config.symbols}")

    def _log(self, message: str, level: str = "INFO") -> None:
        """Log a message to file and console.

        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR)
        """
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)

        try:
            with open(self._log_file, "a") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Error writing to log file: {e}")

    def initialize(self) -> bool:
        """Initialize the trading engine.

        Loads Alpaca client, models, and data fetchers.

        Returns:
            True if initialization successful
        """
        try:
            # Initialize Alpaca client
            self._log("Initializing Alpaca client...")
            self.alpaca_client = AlpacaClient()
            account = self.alpaca_client.get_account()
            self._log(f"Account connected: {str(account.account_id)[:8]}...")
            self._log(f"Cash: ${account.cash:,.2f}")
            self._log(f"Portfolio value: ${account.portfolio_value:,.2f}")

            # Load models for each symbol
            for symbol in self.config.symbols:
                if self._load_model(symbol):
                    self.data_fetchers[symbol] = DataFetcher(
                        symbol=symbol, window_size=60
                    )
                    self._trade_counts[symbol] = 0

            self._log(
                f"Initialized {len(self.models)} models for symbols: {list(self.models.keys())}"
            )
            return True

        except Exception as e:
            self._log(f"Initialization failed: {e}", "ERROR")
            return False

    def _load_model(self, symbol: str) -> bool:
        """Load a trained model for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            True if model loaded successfully
        """
        try:
            model_path = Path(self.config.models_dir) / f"{symbol.lower()}_model.keras"

            if not model_path.exists():
                self._log(f"Model not found for {symbol}: {model_path}", "WARNING")
                return False

            self._log(f"Loading model for {symbol}...")
            model = tf.keras.models.load_model(str(model_path))
            self.models[symbol] = model
            self._log(f"Model loaded successfully for {symbol}")
            return True

        except Exception as e:
            self._log(f"Error loading model for {symbol}: {e}", "ERROR")
            return False

    def _get_prediction(self, symbol: str) -> tuple[float, float] | None:
        """Get model prediction for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Tuple of (prediction, current_price) or None
        """
        if symbol not in self.models:
            return None

        try:
            # Fetch latest data
            data_fetcher = self.data_fetchers[symbol]
            df = data_fetcher.update_data()

            if df.empty or len(df) < 60:
                self._log(f"Insufficient data for {symbol}", "WARNING")
                return None

            # Get current price
            current_price = float(df["close"].iloc[-1])

            # Prepare model input
            model_input = data_fetcher.prepare_input(df)

            # Make prediction
            model = self.models[symbol]
            prediction = model.predict(model_input, verbose=0)[0, 0]

            return float(prediction), current_price

        except Exception as e:
            self._log(f"Error getting prediction for {symbol}: {e}", "ERROR")
            return None

    def _calculate_position_size(
        self, signal: float, current_price: float, portfolio_value: float
    ) -> float:
        """Calculate position size based on signal strength.

        Uses tanh scaling for smooth position sizing.

        Args:
            signal: Trading signal (-1 to 1)
            current_price: Current stock price
            portfolio_value: Total portfolio value

        Returns:
            Number of shares to trade
        """
        # Scale signal to position size (0 to max_position_size)
        position_fraction = abs(signal) * self.config.max_position_size

        # Calculate dollar amount
        position_value = portfolio_value * position_fraction

        # Convert to shares
        qty = position_value / current_price

        # Round to whole shares
        return max(1, int(qty))

    def _should_open_position(self, symbol: str, signal: float) -> bool:
        """Determine if a new position should be opened.

        Args:
            symbol: Stock ticker symbol
            signal: Trading signal

        Returns:
            True if position should be opened
        """
        # Check signal strength
        if abs(signal) < self.config.signal_threshold:
            return False

        # Check if already have position
        if symbol in self.positions:
            return False

        # Check max positions
        if len(self.positions) >= self.config.max_positions:
            return False

        # Check daily trade limit
        if self._trade_counts.get(symbol, 0) >= self.config.max_trade_per_symbol:
            self._log(f"Daily trade limit reached for {symbol}", "WARNING")
            return False

        # Check market is open
        if not self.alpaca_client or not self.alpaca_client.is_market_open():
            return False

        return True

    def _open_position(
        self, symbol: str, signal: float, current_price: float
    ) -> TradeResult | None:
        """Open a new position.

        Args:
            symbol: Stock ticker symbol
            signal: Trading signal
            current_price: Current price

        Returns:
            TradeResult or None
        """
        if not self.alpaca_client:
            return None

        # Get account info for position sizing
        account = self.alpaca_client.get_account()

        # Calculate position size
        qty = self._calculate_position_size(
            signal, current_price, account.portfolio_value
        )

        if qty <= 0:
            self._log(f"Invalid quantity for {symbol}", "WARNING")
            return None

        # Determine side
        side = "buy" if signal > 0 else "sell"

        # Calculate stop loss and take profit levels
        if side == "buy":
            stop_loss = current_price * (1 - self.config.stop_loss_pct)
            take_profit = current_price * (1 + self.config.take_profit_pct)
        else:
            stop_loss = current_price * (1 + self.config.stop_loss_pct)
            take_profit = current_price * (1 - self.config.take_profit_pct)

        # Create order config
        order_config = OrderConfig(
            symbol=symbol,
            qty=qty,
            side=side,
            order_type="market",
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        # Place order
        self._log(
            f"Opening {side.upper()} position: {symbol} x{qty} @ ${current_price:.2f}"
        )
        result = self.alpaca_client.place_order(order_config)

        if result.success:
            # Record position
            self.positions[symbol] = PositionInfo(
                symbol=symbol,
                entry_price=current_price,
                entry_time=datetime.now(),
                qty=qty,
                side=side,
                model_prediction=signal,
                stop_loss=stop_loss,
                take_profit=take_profit,
                order_id=result.order_id,
            )

            # Increment trade count
            self._trade_counts[symbol] = self._trade_counts.get(symbol, 0) + 1

            # Log trade
            self.trade_history.append(
                TradeLog(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    price=current_price,
                    order_id=result.order_id or "",
                    reason="signal_entry",
                    model_prediction=signal,
                )
            )

            self._log(f"Position opened successfully: {symbol}")
        else:
            self._log(f"Failed to open position: {result.message}", "ERROR")

        return result

    def _check_exit_conditions(self, symbol: str) -> bool:
        """Check if a position should be closed.

        Args:
            symbol: Stock ticker symbol

        Returns:
            True if position was closed
        """
        if symbol not in self.positions:
            return False

        position = self.positions[symbol]
        if not self.alpaca_client:
            return False

        # Get current price
        current_price = self.alpaca_client.get_latest_price(symbol)
        if current_price is None:
            return False

        # Calculate PnL percentage
        if position.side == "buy":
            pnl_pct = (current_price - position.entry_price) / position.entry_price
        else:
            pnl_pct = (position.entry_price - current_price) / position.entry_price

        # Check stop loss
        if pnl_pct <= -self.config.stop_loss_pct:
            self._log(f"Stop loss triggered for {symbol}: {pnl_pct * 100:.2f}%")
            self._close_position(symbol, "stop_loss")
            return True

        # Check take profit
        if pnl_pct >= self.config.take_profit_pct:
            self._log(f"Take profit triggered for {symbol}: {pnl_pct * 100:.2f}%")
            self._close_position(symbol, "take_profit")
            return True

        # Check signal reversal
        prediction_data = self._get_prediction(symbol)
        if prediction_data:
            prediction, _ = prediction_data
            if position.side == "buy" and prediction < -self.config.signal_threshold:
                self._log(f"Signal reversal for {symbol}: closing long")
                self._close_position(symbol, "signal_reversal")
                return True
            if position.side == "sell" and prediction > self.config.signal_threshold:
                self._log(f"Signal reversal for {symbol}: closing short")
                self._close_position(symbol, "signal_reversal")
                return True

        return False

    def _close_position(self, symbol: str, reason: str) -> TradeResult | None:
        """Close an existing position.

        Args:
            symbol: Stock ticker symbol
            reason: Reason for closing

        Returns:
            TradeResult or None
        """
        if symbol not in self.positions:
            return None

        if not self.alpaca_client:
            return None

        position = self.positions[symbol]

        # Get current price
        current_price = self.alpaca_client.get_latest_price(symbol)
        if current_price is None:
            current_price = position.entry_price

        # Calculate PnL
        if position.side == "buy":
            pnl = (current_price - position.entry_price) * position.qty
        else:
            pnl = (position.entry_price - current_price) * position.qty

        # Close position via Alpaca
        self._log(f"Closing position: {symbol} ({reason})")
        result = self.alpaca_client.close_position(symbol)

        if result.success:
            # Log trade
            self.trade_history.append(
                TradeLog(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    side="sell" if position.side == "buy" else "buy",
                    qty=position.qty,
                    price=current_price,
                    order_id=result.order_id or "",
                    pnl=pnl,
                    reason=reason,
                    model_prediction=position.model_prediction,
                )
            )

            # Remove from positions
            del self.positions[symbol]

            self._log(f"Position closed: {symbol} | PnL: ${pnl:.2f}")
        else:
            self._log(f"Failed to close position: {result.message}", "ERROR")

        return result

    def _rebalance(self) -> None:
        """Rebalance portfolio based on current signals.

        Reviews all positions and adjusts based on latest predictions.
        """
        self._log("Rebalancing portfolio...")

        for symbol in list(self.positions.keys()):
            self._check_exit_conditions(symbol)

        for symbol in self.config.symbols:
            if symbol not in self.positions:
                prediction_data = self._get_prediction(symbol)
                if prediction_data:
                    prediction, price = prediction_data
                    signal = np.tanh(5.0 * prediction)  # Tanh scaling

                    if self._should_open_position(symbol, signal):
                        self._open_position(symbol, signal, price)

        self._last_rebalance = datetime.now()

    def _save_equity_snapshot(self) -> None:
        """Save current equity snapshot to file."""
        if not self.alpaca_client:
            return

        try:
            account = self.alpaca_client.get_account()
            timestamp = datetime.now()

            equity_file = Path(
                self.config.data_dir,
                "equity",
                f"equity_{timestamp.strftime('%Y%m%d')}.csv",
            )

            # Append to file
            file_exists = equity_file.exists()
            with open(equity_file, "a") as f:
                if not file_exists:
                    f.write("timestamp,equity,cash,portfolio_value\n")
                f.write(
                    f"{timestamp.isoformat()},{account.equity},{account.cash},{account.portfolio_value}\n"
                )

        except Exception as e:
            self._log(f"Error saving equity snapshot: {e}", "ERROR")

    def _save_trades(self) -> None:
        """Save trade history to file."""
        if not self.trade_history:
            return

        try:
            trades_file = Path(
                self.config.data_dir,
                "trades",
                f"trades_{datetime.now().strftime('%Y%m%d')}.csv",
            )

            with open(trades_file, "w") as f:
                f.write(
                    "timestamp,symbol,side,qty,price,pnl,reason,order_id,prediction\n"
                )
                for trade in self.trade_history:
                    f.write(
                        f"{trade.timestamp.isoformat()},{trade.symbol},{trade.side},{trade.qty},{trade.price},{trade.pnl},{trade.reason},{trade.order_id},{trade.model_prediction}\n"
                    )

        except Exception as e:
            self._log(f"Error saving trades: {e}", "ERROR")

    def start(self) -> None:
        """Start the live trading engine.

        Runs the main trading loop until stopped.
        """
        if not self.initialize():
            self._log("Failed to initialize engine", "ERROR")
            return

        self._running = True
        self._log("Starting live trading engine...")

        # Setup signal handlers
        def signal_handler(sig, frame):
            self._log("Stop signal received")
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            while self._running and not self._stop_event.is_set():
                try:
                    # Check if market is open
                    if self.alpaca_client and self.alpaca_client.is_market_open():
                        # Rebalance at intervals
                        if (
                            self._last_rebalance is None
                            or datetime.now() - self._last_rebalance
                            >= timedelta(minutes=self.config.rebalance_interval)
                        ):
                            self._rebalance()

                        # Save equity snapshot
                        self._save_equity_snapshot()

                    else:
                        self._log("Market is closed, waiting...")

                    # Save trades periodically
                    self._save_trades()

                    # Wait for next cycle
                    time.sleep(60)  # Check every minute

                except Exception as e:
                    self._log(f"Error in trading loop: {e}", "ERROR")
                    time.sleep(30)

        except Exception as e:
            self._log(f"Trading engine error: {e}", "ERROR")

        finally:
            self._shutdown()

    def stop(self) -> None:
        """Stop the live trading engine."""
        self._log("Stopping trading engine...")
        self._running = False
        self._stop_event.set()

    def _shutdown(self) -> None:
        """Shutdown the engine gracefully."""
        self._log("Shutting down...")

        # Save final state
        self._save_trades()

        # Optionally close all positions
        # Uncomment to close positions on shutdown:
        # if self.alpaca_client:
        #     self.alpaca_client.close_all_positions()

        self._log("Engine stopped")


def run_live_trading(config: TradingConfig | None = None) -> None:
    """Run the live trading engine.

    Args:
        config: Optional trading configuration
    """
    if config is None:
        config = TradingConfig()

    engine = LiveTradingEngine(config)
    engine.start()


if __name__ == "__main__":
    # Example usage
    config = TradingConfig(
        symbols=["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
        max_position_size=0.05,  # 5% per position
        max_positions=5,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        signal_threshold=0.15,
        paper_trading=True,  # Start with paper trading!
    )

    run_live_trading(config)
