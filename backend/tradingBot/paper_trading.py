#!/usr/bin/env python3
"""
Paper Trading Module for EUR/USD Trading Bot.

This module implements a paper trading system that:
1. Fetches real-time EUR/USD data using yfinance
2. Loads a trained Keras model for predictions
3. Executes simulated trades based on model predictions
4. Tracks portfolio performance and metrics in real-time

Author: Abka Ferguson
Date: 2026
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import tensorflow as tf

# Suppress TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"


@dataclass
class TradeConfig:
    """Configuration for paper trading parameters.

    Conservative defaults based on lessons learned from overfitting issues:
    - Lower position size (5% vs 10%)
    - Fewer max positions (3 vs 5)
    - Tighter stop loss (1.5% vs 2%)
    - Higher transaction cost estimate (2 bps vs 1 bps)

    Attributes:
        initial_capital: Starting capital for paper trading (USD)
        position_size: Fraction of capital to use per trade (0.0-1.0)
        max_positions: Maximum number of concurrent positions
        stop_loss_pct: Stop loss percentage (e.g., 0.02 for 2%)
        take_profit_pct: Take profit percentage (e.g., 0.04 for 4%)
        cost_bps: Transaction cost in basis points (e.g., 1.0 = 0.01%)
        model_path: Path to the trained Keras model file
        symbol: Trading symbol (e.g., 'AAPL', 'MSFT', 'TSLA')
        window_size: Number of time steps for model input
        csv_path: Optional path to local CSV file for offline testing
    """

    initial_capital: float = 10000.0
    position_size: float = 0.05  # Reduced from 0.1 (5% instead of 10%)
    max_positions: int = 3  # Reduced from 5
    stop_loss_pct: float = 0.015  # Tighter: 1.5% instead of 2%
    take_profit_pct: float = 0.03  # Reduced: 3% instead of 4%
    cost_bps: float = 2.0  # More realistic: 2 bps instead of 1
    model_path: str = "artifacts/model.keras"
    symbol: str = "AAPL"
    window_size: int = 60
    csv_path: str | None = None


@dataclass
class Position:
    """Represents an active trading position.

    Attributes:
        entry_price: Price at which the position was opened
        entry_time: Timestamp when position was opened
        size: Position size (positive for long, negative for short)
        symbol: Trading symbol
        entry_pred: Model prediction at entry
    """

    entry_price: float
    entry_time: datetime
    size: float
    symbol: str
    entry_pred: float
    stop_loss: float = 0.0
    take_profit: float = 0.0


@dataclass
class TradeRecord:
    """Record of a completed trade.

    Attributes:
        entry_time: When the trade was opened
        exit_time: When the trade was closed
        symbol: Trading symbol
        entry_price: Entry price
        exit_price: Exit price
        size: Position size
        pnl: Profit and loss in USD
        exit_reason: Why the trade was closed
        entry_pred: Model prediction at entry
        exit_pred: Model prediction at exit
    """

    entry_time: datetime
    exit_time: datetime
    symbol: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    exit_reason: str
    entry_pred: float
    exit_pred: float


@dataclass
class Portfolio:
    """Tracks portfolio state and performance metrics.

    Attributes:
        initial_capital: Starting capital
        cash: Current cash balance
        positions: Active positions dictionary
        trade_history: List of completed trades
        equity_curve: List of (timestamp, equity) tuples
        config: Trade configuration
    """

    initial_capital: float
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    trade_history: list[TradeRecord] = field(default_factory=list)
    equity_curve: list[tuple[datetime, float]] = field(default_factory=list)
    config: TradeConfig = field(default_factory=TradeConfig)

    @property
    def total_equity(self) -> float:
        """Calculate total portfolio equity (cash + positions)."""
        return self.cash

    @property
    def num_positions(self) -> int:
        """Return number of active positions."""
        return len(self.positions)

    @property
    def total_pnl(self) -> float:
        """Calculate total realized PnL from closed trades."""
        return sum(trade.pnl for trade in self.trade_history)

    @property
    def win_rate(self) -> float:
        """Calculate win rate from closed trades."""
        if not self.trade_history:
            return 0.0
        wins = sum(1 for t in self.trade_history if t.pnl > 0)
        return wins / len(self.trade_history)

    @property
    def profit_factor(self) -> float:
        """Calculate profit factor (gross profit / gross loss)."""
        gross_profit = sum(t.pnl for t in self.trade_history if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trade_history if t.pnl < 0))
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    def add_position(self, position_id: str, position: Position) -> None:
        """Add a new position to the portfolio."""
        self.positions[position_id] = position

    def remove_position(self, position_id: str) -> None:
        """Remove a position from the portfolio."""
        if position_id in self.positions:
            del self.positions[position_id]

    def add_trade(self, trade: TradeRecord) -> None:
        """Record a completed trade."""
        self.trade_history.append(trade)
        self.cash += trade.pnl

    def update_equity(self, timestamp: datetime) -> None:
        """Record current equity in equity curve."""
        self.equity_curve.append((timestamp, self.total_equity))


class DataFetcher:
    """Fetches and processes market data using yfinance.

    This class handles:
    - Downloading historical data from Yahoo Finance
    - Computing technical indicators for model input
    - Maintaining a rolling window of features for predictions

    Attributes:
        symbol: Yahoo Finance symbol for US stocks (e.g., 'AAPL', 'MSFT')
        window_size: Number of time steps for model input
        n_features: Number of features expected by the model
    """

    def __init__(self, symbol: str = "AAPL", window_size: int = 60):
        """Initialize the data fetcher.

        Args:
            symbol: Yahoo Finance symbol for the trading instrument
            window_size: Number of historical data points to maintain
        """
        self.symbol = symbol
        self.window_size = window_size
        self.n_features = 33  # Number of features the model expects
        self._data_buffer: pd.DataFrame | None = None
        self._feature_buffer: np.ndarray | None = None

    def fetch_historical_data(
        self, period: str = "1mo", interval: str = "1m"
    ) -> pd.DataFrame:
        """Fetch historical data from Yahoo Finance or load from local CSV.

        Args:
            period: Time period for historical data (e.g., '1mo', '3mo', '1y')
            interval: Data interval (e.g., '1m', '5m', '1h', '1d')

        Returns:
            DataFrame with OHLCV data indexed by datetime

        Raises:
            ValueError: If no data is available from either source
        """
        # Try local CSV first if provided
        if self.csv_path and os.path.exists(self.csv_path):
            return self._load_from_csv(self.csv_path)

        # Otherwise fetch from yfinance
        import yfinance as yf

        print(f"  Fetching data from Yahoo Finance...")
        ticker = yf.Ticker(self.symbol)

        # Try multiple periods and intervals for better reliability
        try:
            # Try daily data first (more reliable)
            df = ticker.history(period="1mo", interval="1d")

            # If no data, try longer period
            if df.empty:
                df = ticker.history(period="3mo", interval="1d")

            # If still no data, try with different approach
            if df.empty:
                df = yf.download(
                    self.symbol, period="1mo", interval="1d", progress=False
                )

        except Exception as e:
            print(f"  Warning: yfinance error: {e}")
            df = pd.DataFrame()

        if df.empty:
            print(f"\n  ⚠️  yfinance failed to fetch data for {self.symbol}")
            print(f"  Please provide a CSV file with --csv parameter")
            print(
                f"  Example: python paper_trading.py --model artifacts/model.keras --symbol AAPL --csv us_stock_market.csv"
            )
            raise ValueError(
                f"No data received for symbol {self.symbol}. The symbol may be delisted, yfinance is having issues, or you need to provide a CSV file."
            )

        # Standardize column names
        df = df.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )

        # Add symbol column for compatibility
        df["symbol"] = self.symbol
        df["date"] = df.index

        return df.reset_index(drop=True)

    def _load_from_csv(self, csv_path: str) -> pd.DataFrame:
        """Load data from local CSV file.

        Args:
            csv_path: Path to CSV file

        Returns:
            DataFrame with OHLCV data
        """
        # Detect delimiter
        with open(csv_path, "r") as f:
            first_line = f.readline().strip()

        delimiter = "\t" if "\t" in first_line else ","

        # Check if has header
        has_header = first_line.split(delimiter)[0].lower() in [
            "date",
            "symbol",
            "time",
            "timestamp",
        ]

        if has_header:
            df = pd.read_csv(csv_path)
        else:
            df = pd.read_csv(
                csv_path,
                header=None,
                names=["date", "open", "high", "low", "close", "volume"],
                sep=delimiter,
                engine="python",
            )

        # Parse datetime
        df["date"] = pd.to_datetime(df["date"], format="mixed")

        # Add symbol if missing
        if "symbol" not in df.columns:
            df["symbol"] = self.symbol

        return df

    def _compute_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index.

        Args:
            series: Price series
            period: RSI calculation period

        Returns:
            RSI values
        """
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        return 100 - (100 / (1 + rs))

    def _compute_macd(
        self, series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator.

        Args:
            series: Price series
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period

        Returns:
            Tuple of (MACD line, signal line, histogram)
        """
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _compute_bollinger_bands(
        self, series: pd.Series, window: int = 20, num_std: float = 2.0
    ) -> pd.Series:
        """Calculate Bollinger Bands %B.

        Args:
            series: Price series
            window: Moving average window
            num_std: Number of standard deviations

        Returns:
            Bollinger Bands %B values
        """
        middle = series.rolling(window=window).mean()
        std = series.rolling(window=window).std()
        upper = middle + num_std * std
        lower = middle - num_std * std
        bb_pct = (series - lower) / (upper - lower + 1e-10)
        return bb_pct

    def _compute_atr(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
    ) -> pd.Series:
        """Calculate Average True Range.

        Args:
            high: High price series
            low: Low price series
            close: Close price series
            period: ATR calculation period

        Returns:
            ATR values
        """
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def _compute_obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Calculate On-Balance Volume.

        Args:
            close: Close price series
            volume: Volume series

        Returns:
            OBV values
        """
        direction = np.sign(close.diff())
        return (direction * volume).cumsum()

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all features required by the model.

        This method replicates the feature engineering from train.py
        to ensure consistency between training and inference.

        Uses a REDUCED FEATURE SET (15 features) to prevent overfitting.

        Args:
            df: DataFrame with OHLCV columns

        Returns:
            DataFrame with all computed features
        """
        # Ensure we have required columns
        required_cols = ["open", "high", "low", "close", "volume"]
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Missing required columns: {required_cols}")

        # Log returns
        df["close_lr"] = np.log(df["close"] / df["close"].shift(1))

        # Price gaps and ranges
        prev_close = df["close"].shift(1)
        df["open_gap"] = np.log(df["open"]) - np.log(prev_close)
        df["close_open"] = np.log(df["close"]) - np.log(df["open"])
        df["hl_range"] = np.log(df["high"]) - np.log(df["low"])

        # Rolling features
        df["mom_5"] = df["close_lr"].rolling(5).sum()
        df["vol_20"] = df["close_lr"].rolling(20).std()

        # Lagged returns (only 3 most important)
        for lag in [1, 3, 5]:
            df[f"close_lr_lag{lag}"] = df["close_lr"].shift(lag)

        # Technical indicators
        df["rsi_14"] = self._compute_rsi(df["close"], 14)

        macd_line, signal_line, histogram = self._compute_macd(df["close"])
        df["macd_hist"] = histogram  # Only histogram (most informative)

        df["bb_pct"] = self._compute_bollinger_bands(df["close"])

        # Volume features
        df["vol_ma_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

        # Trend strength (requires mom_21 and vol_21)
        df["mom_21"] = df["close_lr"].rolling(21).sum()
        df["vol_21"] = df["close_lr"].rolling(21).std()
        df["trend_strength"] = df["mom_21"].abs() / (df["vol_21"] + 1e-10)

        return df

    def get_feature_columns(self) -> list[str]:
        """Return the list of feature column names.

        Returns:
            List of 15 feature column names (reduced from 33)
        """
        return [
            # Core price features (5)
            "close_lr",
            "open_gap",
            "close_open",
            "hl_range",
            # Lagged returns (3)
            "close_lr_lag1",
            "close_lr_lag3",
            "close_lr_lag5",
            # Single momentum and volatility (2)
            "mom_5",
            "vol_20",
            # Key technical indicators (3)
            "rsi_14",
            "macd_hist",
            "bb_pct",
            # Volume and regime (2)
            "vol_ma_ratio",
            "trend_strength",
        ]

    def prepare_input(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare model input from feature DataFrame.

        Args:
            df: DataFrame with computed features

        Returns:
            Numpy array of shape (1, window_size, n_features)
        """
        feature_cols = self.get_feature_columns()

        # Get the last window_size rows
        features = df[feature_cols].iloc[-self.window_size :]

        if len(features) < self.window_size:
            # Pad with zeros if not enough history
            padding = np.zeros(
                (self.window_size - len(features), len(feature_cols)), dtype=np.float32
            )
            features = np.vstack([padding, features.values])
        else:
            features = features.values

        # Reshape to (1, window_size, n_features)
        return features.reshape(1, self.window_size, len(feature_cols)).astype(
            np.float32
        )

    def update_data(self) -> pd.DataFrame:
        """Fetch latest data and update internal buffers.

        Returns:
            Updated DataFrame with features
        """
        df = self.fetch_historical_data(period="3mo", interval="1d")
        df = self.compute_features(df)
        self._data_buffer = df
        return df


class PaperTrader:
    """Main paper trading engine.

    This class orchestrates the paper trading process:
    1. Loads the trained model
    2. Fetches market data
    3. Generates predictions
    4. Executes simulated trades
    5. Tracks performance

    Attributes:
        config: Trading configuration
        model: Loaded Keras model
        data_fetcher: Data fetching instance
        portfolio: Current portfolio state
    """

    def __init__(self, config: TradeConfig):
        """Initialize the paper trader.

        Args:
            config: Trading configuration parameters
        """
        self.config = config
        self.model: tf.keras.Model | None = None
        self.data_fetcher = DataFetcher(
            symbol=config.symbol, window_size=config.window_size
        )
        # Set CSV path for offline testing
        self.data_fetcher.csv_path = config.csv_path
        self.portfolio = Portfolio(
            initial_capital=config.initial_capital,
            cash=config.initial_capital,
            config=config,
        )
        self._running = False
        self._last_prediction: float | None = None
        self._last_price: float | None = None

    def load_model(self) -> None:
        """Load the trained Keras model from disk.

        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        if not os.path.exists(self.config.model_path):
            raise FileNotFoundError(
                f"Model file not found: {self.config.model_path}\n"
                "Please train a model first using: python train.py --save-model artifacts/model.keras"
            )

        print(f"Loading model from {self.config.model_path}...")
        self.model = tf.keras.models.load_model(self.config.model_path)
        print("Model loaded successfully.")

    def predict(self, features: np.ndarray) -> float:
        """Generate prediction from the model.

        Args:
            features: Input features array of shape (1, window_size, n_features)

        Returns:
            Predicted return value
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")

        prediction = self.model.predict(features, verbose=0)[0, 0]
        return float(prediction)

    def generate_signal(self, prediction: float) -> float:
        """Convert model prediction to trading signal.

        Uses tanh activation for smooth position sizing in [-1, 1].

        Args:
            prediction: Raw model prediction

        Returns:
            Position size signal (-1 to 1)
        """
        alpha = 10.0  # Scaling factor
        return float(np.tanh(alpha * prediction))

    def should_open_position(
        self, signal: float, current_price: float
    ) -> tuple[bool, float]:
        """Determine if a new position should be opened.

        Args:
            signal: Trading signal (-1 to 1)
            current_price: Current market price

        Returns:
            Tuple of (should_open, position_size)
        """
        # Check if we have capacity for more positions
        if self.portfolio.num_positions >= self.config.max_positions:
            return False, 0.0

        # Threshold for opening position
        threshold = 0.1
        if abs(signal) < threshold:
            return False, 0.0

        # Calculate position size
        position_value = self.config.initial_capital * self.config.position_size
        position_size = position_value / current_price

        # Negative for short, positive for long
        if signal < 0:
            position_size = -position_size

        return True, position_size

    def check_exit_conditions(
        self, position: Position, current_price: float, current_time: datetime
    ) -> tuple[bool, str]:
        """Check if a position should be closed.

        Args:
            position: Active position to check
            current_price: Current market price
            current_time: Current timestamp

        Returns:
            Tuple of (should_exit, exit_reason)
        """
        # Calculate PnL
        if position.size > 0:  # Long position
            pnl_pct = (current_price - position.entry_price) / position.entry_price
        else:  # Short position
            pnl_pct = (position.entry_price - current_price) / position.entry_price

        # Check stop loss
        if pnl_pct <= -self.config.stop_loss_pct:
            return True, "stop_loss"

        # Check take profit
        if pnl_pct >= self.config.take_profit_pct:
            return True, "take_profit"

        # Check time-based exit (hold for max 4 hours)
        hold_duration = current_time - position.entry_time
        if hold_duration > timedelta(hours=4):
            return True, "time_exit"

        # Check signal reversal
        if self._last_prediction is not None:
            if position.size > 0 and self._last_prediction < -0.1:
                return True, "signal_reversal"
            if position.size < 0 and self._last_prediction > 0.1:
                return True, "signal_reversal"

        return False, ""

    def open_position(
        self, price: float, size: float, timestamp: datetime, prediction: float
    ) -> str:
        """Open a new trading position.

        Args:
            price: Entry price
            size: Position size (positive for long, negative for short)
            timestamp: Entry timestamp
            prediction: Model prediction at entry

        Returns:
            Position ID
        """
        position_id = f"POS_{len(self.portfolio.positions) + 1}"

        # Calculate stop loss and take profit levels
        if size > 0:  # Long
            stop_loss = price * (1 - self.config.stop_loss_pct)
            take_profit = price * (1 + self.config.take_profit_pct)
        else:  # Short
            stop_loss = price * (1 + self.config.stop_loss_pct)
            take_profit = price * (1 - self.config.take_profit_pct)

        position = Position(
            entry_price=price,
            entry_time=timestamp,
            size=abs(size),
            symbol=self.config.symbol,
            entry_pred=prediction,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        self.portfolio.add_position(position_id, position)

        # Deduct transaction cost
        cost = (abs(size) * price) * (self.config.cost_bps / 10_000)
        self.portfolio.cash -= cost

        print(
            f"  📈 OPEN {'LONG' if size > 0 else 'SHORT'} | "
            f"Price: {price:.5f} | Size: {abs(size):.2f} | "
            f"SL: {stop_loss:.5f} | TP: {take_profit:.5f}"
        )

        return position_id

    def close_position(
        self,
        position_id: str,
        price: float,
        timestamp: datetime,
        prediction: float,
        reason: str,
    ) -> None:
        """Close an existing position.

        Args:
            position_id: ID of position to close
            price: Exit price
            timestamp: Exit timestamp
            prediction: Model prediction at exit
            reason: Reason for closing
        """
        if position_id not in self.portfolio.positions:
            return

        position = self.portfolio.positions[position_id]

        # Calculate PnL
        if position.size > 0:  # Long
            pnl = (price - position.entry_price) * position.size
        else:  # Short
            pnl = (position.entry_price - price) * position.size

        # Deduct transaction cost
        cost = (position.size * price) * (self.config.cost_bps / 10_000)
        pnl -= cost

        # Create trade record
        trade = TradeRecord(
            entry_time=position.entry_time,
            exit_time=timestamp,
            symbol=position.symbol,
            entry_price=position.entry_price,
            exit_price=price,
            size=position.size,
            pnl=pnl,
            exit_reason=reason,
            entry_pred=position.entry_pred,
            exit_pred=prediction,
        )

        self.portfolio.add_trade(trade)
        self.portfolio.remove_position(position_id)

        # Update last prediction
        self._last_prediction = prediction

        pnl_icon = "💰" if pnl > 0 else "💸" if pnl < 0 else "➡️"
        print(
            f"  {pnl_icon} CLOSE | Price: {price:.5f} | "
            f"PnL: ${pnl:.2f} ({pnl / position.entry_price * 100:.2f}%) | Reason: {reason}"
        )

    def run_trading_cycle(self, df: pd.DataFrame, timestamp: datetime) -> None:
        """Execute one trading cycle.

        Args:
            df: DataFrame with price data and features
            timestamp: Current timestamp
        """
        if len(df) < self.config.window_size:
            print("⏳ Insufficient data for prediction...")
            return

        # Prepare input and get prediction
        try:
            features = self.data_fetcher.prepare_input(df)
            prediction = self.predict(features)
            signal = self.generate_signal(prediction)

            current_price = df["close"].iloc[-1]

            # Update last prediction for exit logic
            self._last_prediction = prediction
            self._last_price = current_price

            # Check existing positions for exit
            positions_to_close = []
            for pos_id, position in self.portfolio.positions.items():
                should_exit, exit_reason = self.check_exit_conditions(
                    position, current_price, timestamp
                )
                if should_exit:
                    positions_to_close.append((pos_id, exit_reason))

            # Close positions
            for pos_id, reason in positions_to_close:
                self.close_position(
                    pos_id, current_price, timestamp, prediction, reason
                )

            # Check for new entry
            should_open, position_size = self.should_open_position(
                signal, current_price
            )
            if should_open:
                self.open_position(current_price, position_size, timestamp, prediction)

            # Update portfolio equity
            self.portfolio.update_equity(timestamp)

        except Exception as e:
            print(f"⚠️  Error in trading cycle: {e}")

    def print_portfolio_summary(self) -> None:
        """Print current portfolio status and metrics."""
        print("\n" + "=" * 60)
        print("📊 PORTFOLIO SUMMARY")
        print("=" * 60)
        print(f"Initial Capital:    ${self.portfolio.initial_capital:,.2f}")
        print(f"Current Cash:       ${self.portfolio.cash:,.2f}")
        print(f"Total Equity:       ${self.portfolio.total_equity:,.2f}")
        print(f"Total PnL:          ${self.portfolio.total_pnl:,.2f}")
        print(
            f"Total Return:       {(self.portfolio.total_equity / self.portfolio.initial_capital - 1) * 100:.2f}%"
        )
        print(f"Active Positions:   {self.portfolio.num_positions}")
        print(f"Total Trades:       {len(self.portfolio.trade_history)}")
        print(f"Win Rate:           {self.portfolio.win_rate * 100:.1f}%")
        print(f"Profit Factor:      {self.portfolio.profit_factor:.2f}")
        print("=" * 60)

        if self.portfolio.positions:
            print("\n📈 ACTIVE POSITIONS:")
            for pos_id, pos in self.portfolio.positions.items():
                print(
                    f"  {pos_id}: {'LONG' if pos.size > 0 else 'SHORT'} | "
                    f"Entry: {pos.entry_price:.5f} | "
                    f"Size: {pos.size:.2f} | "
                    f"Time: {pos.entry_time.strftime('%H:%M')}"
                )

        if self.portfolio.trade_history:
            print("\n📜 RECENT TRADES:")
            for trade in self.portfolio.trade_history[-5:]:
                pnl_icon = "💰" if trade.pnl > 0 else "💸"
                print(
                    f"  {pnl_icon} {trade.symbol} | "
                    f"{'LONG' if trade.size > 0 else 'SHORT'} | "
                    f"PnL: ${trade.pnl:.2f} | "
                    f"Reason: {trade.exit_reason}"
                )

        print()

    def run(
        self,
        duration_minutes: int = 60,
        interval_seconds: int = 60,
        use_historical: bool = True,
    ) -> None:
        """Run the paper trading session.

        Args:
            duration_minutes: How long to run the simulation (minutes)
            interval_seconds: Time between trading cycles (seconds)
            use_historical: If True, replay historical data; if False, fetch live data
        """
        print("\n" + "=" * 60)
        print("🚀 STARTING PAPER TRADING SESSION")
        print("=" * 60)
        print(f"Symbol:           {self.config.symbol}")
        print(f"Initial Capital:  ${self.config.initial_capital:,.2f}")
        print(f"Position Size:    {self.config.position_size * 100:.1f}%")
        print(f"Max Positions:    {self.config.max_positions}")
        print(f"Stop Loss:        {self.config.stop_loss_pct * 100:.1f}%")
        print(f"Take Profit:      {self.config.take_profit_pct * 100:.1f}%")
        print(f"Duration:         {duration_minutes} minutes")
        print(f"Interval:         {interval_seconds} seconds")
        print("=" * 60 + "\n")

        # Load model
        self.load_model()

        # Fetch initial data
        print("\n📡 Fetching market data...")
        df = self.data_fetcher.update_data()
        print(f"Received {len(df)} data points")

        if use_historical:
            # Replay historical data in fast-forward
            print("\n⏩ Running historical replay...\n")
            self._run_historical_replay(df, duration_minutes, interval_seconds)
        else:
            # Run with live data updates
            print("\n🔴 Running with live data...\n")
            self._run_live_trading(duration_minutes, interval_seconds)

        # Final summary
        self.print_portfolio_summary()

        # Save results
        self._save_results()

    def _run_historical_replay(
        self, df: pd.DataFrame, duration_minutes: int, interval_seconds: int
    ) -> None:
        """Run trading by replaying historical data.

        Args:
            df: Historical data DataFrame
            duration_minutes: Simulation duration in minutes
            interval_seconds: Seconds between cycles
        """
        self._running = True
        start_idx = self.config.window_size
        end_idx = min(start_idx + duration_minutes, len(df))

        cycle = 0
        for idx in range(start_idx, end_idx):
            if not self._running:
                break

            cycle += 1
            subset_df = df.iloc[: idx + 1].copy()
            timestamp = subset_df["date"].iloc[-1]

            print(f"\n⏰ [{timestamp.strftime('%Y-%m-%d %H:%M')}] Cycle {cycle}")
            print(f"  Price: {subset_df['close'].iloc[-1]:.5f}")

            self.run_trading_cycle(subset_df, timestamp)

            # Small delay for realism
            time.sleep(interval_seconds / 10)  # Speed up for demo

    def _run_live_trading(self, duration_minutes: int, interval_seconds: int) -> None:
        """Run trading with live data updates.

        Args:
            duration_minutes: How long to run (minutes)
            interval_seconds: Seconds between cycles
        """
        self._running = True
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        cycle = 0

        try:
            while time.time() < end_time and self._running:
                cycle += 1
                timestamp = datetime.now()

                print(f"\n⏰ [{timestamp.strftime('%Y-%m-%d %H:%M')}] Cycle {cycle}")

                # Fetch fresh data
                try:
                    df = self.data_fetcher.update_data()
                    print(f"  Price: {df['close'].iloc[-1]:.5f}")
                    self.run_trading_cycle(df, timestamp)
                except Exception as e:
                    print(f"  ⚠️  Data fetch error: {e}")

                # Wait for next cycle
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n\n⚠️  Trading interrupted by user")
            self._running = False

    def _save_results(self) -> None:
        """Save trading results to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save trade history
        if self.portfolio.trade_history:
            trades_df = pd.DataFrame(
                [
                    {
                        "entry_time": t.entry_time,
                        "exit_time": t.exit_time,
                        "symbol": t.symbol,
                        "entry_price": t.entry_price,
                        "exit_price": t.exit_price,
                        "size": t.size,
                        "pnl": t.pnl,
                        "exit_reason": t.exit_reason,
                        "entry_pred": t.entry_pred,
                        "exit_pred": t.exit_pred,
                    }
                    for t in self.portfolio.trade_history
                ]
            )
            trades_file = f"paper_trading_trades_{timestamp}.csv"
            trades_df.to_csv(trades_file, index=False)
            print(f"📁 Trade history saved to: {trades_file}")

        # Save equity curve
        if self.portfolio.equity_curve:
            equity_df = pd.DataFrame(
                self.portfolio.equity_curve, columns=["timestamp", "equity"]
            )
            equity_file = f"paper_trading_equity_{timestamp}.csv"
            equity_df.to_csv(equity_file, index=False)
            print(f"📁 Equity curve saved to: {equity_file}")


def main() -> int:
    """Main entry point for paper trading script.

    Returns:
        Exit code (0 for success)
    """
    parser = argparse.ArgumentParser(
        description="Paper Trading Simulator for US Stock Market Trading Bot",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--model",
        type=str,
        default="artifacts/model.keras",
        help="Path to trained Keras model file",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="AAPL",
        help="US stock ticker symbol (e.g., AAPL, MSFT, TSLA)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=10000.0,
        help="Initial paper trading capital (USD)",
    )
    parser.add_argument(
        "--position-size",
        type=float,
        default=0.1,
        help="Fraction of capital per trade (0.0-1.0)",
    )
    parser.add_argument(
        "--max-positions",
        type=int,
        default=5,
        help="Maximum concurrent positions",
    )
    parser.add_argument(
        "--stop-loss",
        type=float,
        default=0.02,
        help="Stop loss percentage (e.g., 0.02 for 2%%)",
    )
    parser.add_argument(
        "--take-profit",
        type=float,
        default=0.04,
        help="Take profit percentage (e.g., 0.04 for 4%%)",
    )
    parser.add_argument(
        "--cost-bps",
        type=float,
        default=1.0,
        help="Transaction cost in basis points",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=60,
        help="Model input window size (time steps)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Trading session duration (minutes)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Time between trading cycles (seconds)",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Optional path to local CSV file for offline testing (instead of yfinance)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live data instead of historical replay",
    )

    args = parser.parse_args()

    # Create configuration
    config = TradeConfig(
        model_path=args.model,
        symbol=args.symbol,
        initial_capital=args.capital,
        position_size=args.position_size,
        max_positions=args.max_positions,
        stop_loss_pct=args.stop_loss,
        take_profit_pct=args.take_profit,
        cost_bps=args.cost_bps,
        window_size=args.window_size,
        csv_path=args.csv,
    )

    # Create and run trader
    trader = PaperTrader(config)

    try:
        trader.run(
            duration_minutes=args.duration,
            interval_seconds=args.interval,
            use_historical=not args.live,
        )
        return 0
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Paper trading stopped by user")
        return 0
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
