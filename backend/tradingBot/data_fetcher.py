"""
Data fetcher utilities.

Separated from paper_trading.py to avoid importing TensorFlow on API startup.
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import pandas as pd


class DataFetcher:
    """Fetches and processes market data using yfinance."""

    def __init__(self, symbol: str = "AAPL", window_size: int = 60):
        self.symbol = symbol
        self.window_size = window_size
        self.n_features = 33
        self._data_buffer: pd.DataFrame | None = None
        self._feature_buffer: np.ndarray | None = None
        self.csv_path: str | None = None

    def fetch_historical_data(
        self, period: str = "1mo", interval: str = "1m"
    ) -> pd.DataFrame:
        if self.csv_path and os.path.exists(self.csv_path):
            return self._load_from_csv(self.csv_path)

        import yfinance as yf

        ticker = yf.Ticker(self.symbol)

        try:
            df = ticker.history(period="1mo", interval="1d")
            if df.empty:
                df = ticker.history(period="3mo", interval="1d")
            if df.empty:
                df = yf.download(
                    self.symbol, period="1mo", interval="1d", progress=False
                )
        except Exception:
            df = pd.DataFrame()

        if df.empty:
            raise ValueError(f"No data received for symbol {self.symbol}.")

        df = df.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )

        df["symbol"] = self.symbol
        df["date"] = df.index

        return df.reset_index(drop=True)

    def _load_from_csv(self, csv_path: str) -> pd.DataFrame:
        with open(csv_path, "r") as f:
            first_line = f.readline().strip()

        delimiter = "\t" if "\t" in first_line else ","
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

        df["date"] = pd.to_datetime(df["date"], format="mixed")
        if "symbol" not in df.columns:
            df["symbol"] = self.symbol
        return df

    def _compute_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
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
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _compute_bollinger_bands(
        self, series: pd.Series, window: int = 20, num_std: float = 2.0
    ) -> pd.Series:
        middle = series.rolling(window=window).mean()
        std = series.rolling(window=window).std()
        upper = middle + num_std * std
        lower = middle - num_std * std
        return (series - lower) / (upper - lower + 1e-10)

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        required_cols = ["open", "high", "low", "close", "volume"]
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Missing required columns: {required_cols}")

        df["close_lr"] = np.log(df["close"] / df["close"].shift(1))
        prev_close = df["close"].shift(1)
        df["open_gap"] = np.log(df["open"]) - np.log(prev_close)
        df["close_open"] = np.log(df["close"]) - np.log(df["open"])
        df["hl_range"] = np.log(df["high"]) - np.log(df["low"])
        df["mom_5"] = df["close_lr"].rolling(5).sum()
        df["vol_20"] = df["close_lr"].rolling(20).std()

        for lag in [1, 3, 5]:
            df[f"close_lr_lag{lag}"] = df["close_lr"].shift(lag)

        df["rsi_14"] = self._compute_rsi(df["close"], 14)
        _, _, histogram = self._compute_macd(df["close"])
        df["macd_hist"] = histogram
        df["bb_pct"] = self._compute_bollinger_bands(df["close"])
        df["vol_ma_ratio"] = df["volume"] / df["volume"].rolling(20).mean()
        df["mom_21"] = df["close_lr"].rolling(21).sum()
        df["vol_21"] = df["close_lr"].rolling(21).std()
        df["trend_strength"] = df["mom_21"].abs() / (df["vol_21"] + 1e-10)

        return df

    def get_feature_columns(self) -> list[str]:
        return [
            "close_lr",
            "open_gap",
            "close_open",
            "hl_range",
            "close_lr_lag1",
            "close_lr_lag3",
            "close_lr_lag5",
            "mom_5",
            "vol_20",
            "rsi_14",
            "macd_hist",
            "bb_pct",
            "vol_ma_ratio",
            "trend_strength",
        ]

    def prepare_input(self, df: pd.DataFrame) -> np.ndarray:
        feature_cols = self.get_feature_columns()
        features = df[feature_cols].iloc[-self.window_size :]
        if len(features) < self.window_size:
            padding = np.zeros(
                (self.window_size - len(features), len(feature_cols)), dtype=np.float32
            )
            features = np.vstack([padding, features.values])
        else:
            features = features.values
        return features.reshape(1, self.window_size, len(feature_cols)).astype(
            np.float32
        )

    def update_data(self) -> pd.DataFrame:
        df = self.fetch_historical_data(period="3mo", interval="1d")
        df = self.compute_features(df)
        self._data_buffer = df
        return df
