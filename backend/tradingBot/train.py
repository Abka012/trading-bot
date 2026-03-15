from __future__ import annotations

import argparse
import os
import random
from dataclasses import dataclass

import numpy as np
import pandas as pd
import tensorflow as tf

from model import ModelConfig, build_model


@dataclass(frozen=True)
class DataConfig:
    csv_path: str
    window_size: int
    test_frac: float
    val_frac: float
    cs_mode: str
    ret_clip: float
    y_demean: bool
    max_symbols: int | None
    seed: int


def _set_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100 - (100 / (1 + rs))


def _macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD line, signal line, and histogram."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bollinger_bands(
    series: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands (upper, middle, lower, %B)."""
    middle = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    # %B indicator: where price is relative to bands
    bb_pct = (series - lower) / (upper - lower + 1e-10)
    return upper, middle, lower, bb_pct


def _atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """Calculate Average True Range."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Calculate On-Balance Volume."""
    direction = np.sign(close.diff())
    return (direction * volume).cumsum()


def _load_and_engineer_features(cfg: DataConfig) -> pd.DataFrame:
    # Detect if CSV has header by checking first row
    with open(cfg.csv_path, "r") as f:
        first_line = f.readline().strip()

    # Detect delimiter (comma or tab)
    delimiter = "\t" if "\t" in first_line else ","

    # Check if first line looks like a header or data
    has_header = first_line.split(delimiter)[0].lower() in [
        "date",
        "symbol",
        "time",
        "timestamp",
    ]

    # EURUSD1.csv format: timestamp, open, high, low, close, volume (no header, no symbol)
    # forex_data.csv format: date, symbol, open, high, low, close, volume (with header)
    if "symbol" not in first_line.lower():
        # Load without header - assume EURUSD1 format (tab or comma separated)
        df = pd.read_csv(
            cfg.csv_path,
            header=None,
            names=["date", "open", "high", "low", "close", "volume"],
            sep=delimiter,
            engine="python",
        )
        # Add symbol column for single-symbol data
        df["symbol"] = "EURUSD"
    else:
        # Load with header - assume forex_data format
        df = pd.read_csv(cfg.csv_path)

    # Pandas 3 requires specifying how to parse these mixed formats.
    df["date"] = pd.to_datetime(df["date"], format="mixed")

    # Keep consistent ordering per symbol before feature engineering.
    df = df.sort_values(["symbol", "date"], kind="mergesort").reset_index(drop=True)

    if cfg.max_symbols is not None:
        # Keep it deterministic and stable.
        keep = sorted(df["symbol"].unique())[: cfg.max_symbols]
        df = df[df["symbol"].isin(keep)].copy()

    # Scale-invariant features (per symbol). Use log transforms for stability.
    g = df.groupby("symbol", sort=False)

    close_log = np.log(df["close"])
    open_log = np.log(df["open"])
    high_log = np.log(df["high"])
    low_log = np.log(df["low"])
    vol_log = np.log1p(df["volume"])

    df["close_lr"] = close_log.groupby(df["symbol"], sort=False).diff()
    df["vol_lr"] = vol_log.groupby(df["symbol"], sort=False).diff()

    prev_close_log = close_log.groupby(df["symbol"], sort=False).shift(1)
    df["open_gap"] = open_log - prev_close_log  # open vs prev close
    df["close_open"] = close_log - open_log  # intraday move
    df["hl_range"] = high_log - low_log  # intraday range

    # Simple rolling features: short-term momentum and volatility (per symbol).
    df["mom_5"] = g["close_lr"].rolling(5).sum().reset_index(level=0, drop=True)
    df["vol_20"] = g["close_lr"].rolling(20).std().reset_index(level=0, drop=True)

    # === Enhanced Technical Indicators ===

    # Lagged returns (multiple timeframes)
    for lag in [1, 3, 5, 10, 21]:
        df[f"close_lr_lag{lag}"] = g["close_lr"].shift(lag)

    # Rolling momentum at multiple horizons
    for window in [3, 5, 10, 21]:
        df[f"mom_{window}"] = (
            g["close_lr"].rolling(window).sum().reset_index(level=0, drop=True)
        )

    # Rolling volatility at multiple horizons
    for window in [5, 10, 21, 60]:
        df[f"vol_{window}"] = (
            g["close_lr"].rolling(window).std().reset_index(level=0, drop=True)
        )

    # RSI (Relative Strength Index) - per symbol
    df["rsi_14"] = g["close"].transform(_rsi, period=14)
    df["rsi_7"] = g["close"].transform(_rsi, period=7)

    # MACD - per symbol
    for sym, sub in df.groupby("symbol", sort=False):
        macd_line, signal_line, histogram = _macd(sub["close"])
        df.loc[sub.index, "macd"] = macd_line
        df.loc[sub.index, "macd_signal"] = signal_line
        df.loc[sub.index, "macd_hist"] = histogram

    # Bollinger Bands %B - per symbol
    for sym, sub in df.groupby("symbol", sort=False):
        _, _, _, bb_pct = _bollinger_bands(sub["close"])
        df.loc[sub.index, "bb_pct"] = bb_pct

    # ATR (Average True Range) - per symbol
    for sym, sub in df.groupby("symbol", sort=False):
        atr = _atr(sub["high"], sub["low"], sub["close"])
        df.loc[sub.index, "atr_14"] = atr

    # On-Balance Volume - per symbol
    for sym, sub in df.groupby("symbol", sort=False):
        obv = _obv(sub["close"], sub["volume"])
        df.loc[sub.index, "obv"] = obv
    df["obv_lr"] = g["obv"].transform(lambda x: x.pct_change())

    # Volume features
    df["vol_ma_ratio"] = df["volume"] / g["volume"].transform(
        lambda x: x.rolling(20).mean()
    )
    df["vol_std_20"] = g["volume"].rolling(20).std().reset_index(level=0, drop=True)

    # Price position features
    df["close_ma_20"] = g["close"].transform(lambda x: x.rolling(20).mean())
    df["close_ma_ratio"] = df["close"] / df["close_ma_20"]

    # High-low range normalized
    df["hl_range_pct"] = (df["high"] - df["low"]) / df["close"]

    # === Market Regime Features ===

    # Volatility regime (high/low based on rolling quantile)
    df["vol_regime"] = g["vol_20"].transform(
        lambda x: (
            (x - x.rolling(60).min())
            / (x.rolling(60).max() - x.rolling(60).min() + 1e-10)
        )
    )

    # Trend strength (based on ADX-like measure)
    df["trend_strength"] = df["mom_21"].abs() / (df["vol_21"] + 1e-10)

    # Target is next-day close log return (aligned at time t).
    # y_true is always the raw log return used for PnL/backtests.
    df["y_true"] = g["close_lr"].shift(-1)
    df["y"] = df["y_true"]

    # REDUCED FEATURE SET: 15 core features to prevent overfitting
    # Original had 33 features which caused severe overfitting on noisy forex data
    feat_cols = [
        # Core price features (5)
        "close_lr",
        "open_gap",
        "close_open",
        "hl_range",
        # Lagged returns - most predictive features (3)
        "close_lr_lag1",
        "close_lr_lag3",
        "close_lr_lag5",
        # Single momentum and volatility (2)
        "mom_5",
        "vol_20",
        # Key technical indicators (3)
        "rsi_14",
        "macd_hist",  # Use only histogram (most informative MACD component)
        "bb_pct",
        # Volume and regime (2)
        "vol_ma_ratio",
        "trend_strength",
    ]
    all_cols = ["symbol", "date"] + feat_cols + ["y", "y_true"]
    df = df[all_cols].dropna().reset_index(drop=True)

    if cfg.ret_clip > 0:
        clip = float(cfg.ret_clip)
        for c in feat_cols + ["y", "y_true"]:
            df[c] = df[c].clip(-clip, clip)

    if cfg.cs_mode not in ("none", "demean", "zscore"):
        raise ValueError("--cs-mode must be one of: none, demean, zscore")

    # Cross-sectional transforms should apply to features (available at decision time).
    # Do not z-score the target used for PnL.
    if cfg.cs_mode != "none":
        cols = feat_cols
        by_date = df.groupby("date", sort=False)[cols]
        mean = by_date.transform("mean")
        if cfg.cs_mode == "demean":
            df[cols] = df[cols] - mean
        else:
            std = by_date.transform("std").replace(0.0, np.nan)
            df[cols] = (df[cols] - mean) / (std + 1e-8)
            df[cols] = df[cols].fillna(0.0)

    if cfg.y_demean:
        y_mean = df.groupby("date", sort=False)["y"].transform("mean")
        df["y"] = df["y"] - y_mean

    return df


def _make_sequences_per_symbol(
    df: pd.DataFrame, window_size: int, test_frac: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    train_groups, _, test_groups, _, meta_test = _make_sequences_grouped(
        df, window_size=window_size, test_frac=test_frac, val_frac=0.1
    )

    X_train = np.concatenate([v[0] for v in train_groups.values()], axis=0)
    y_train = np.concatenate([v[1] for v in train_groups.values()], axis=0)
    X_test = np.concatenate([v[0] for v in test_groups.values()], axis=0)
    y_test = np.concatenate([v[1] for v in test_groups.values()], axis=0)
    return X_train, y_train, X_test, y_test, meta_test


def _make_sequences_grouped(
    df: pd.DataFrame, *, window_size: int, test_frac: float, val_frac: float
) -> tuple[
    dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],  # train
    dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],  # val
    dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],  # test
    pd.DataFrame,  # meta_val
    pd.DataFrame,  # meta_test
]:
    # REDUCED FEATURE SET: Must match the features computed in _load_and_engineer_features
    feat_cols = [
        # Core price features (5)
        "close_lr",
        "open_gap",
        "close_open",
        "hl_range",
        # Lagged returns - most predictive features (3)
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

    meta_val_parts: list[pd.DataFrame] = []
    meta_test_parts: list[pd.DataFrame] = []
    train_groups: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    val_groups: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    test_groups: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

    for sym, sub in df.groupby("symbol", sort=False):
        # Already sorted by date.
        feats = sub[feat_cols].to_numpy(dtype=np.float32, copy=False)
        y = sub["y"].to_numpy(dtype=np.float32, copy=False)
        y_true = sub["y_true"].to_numpy(dtype=np.float32, copy=False)
        dates = sub["date"].to_numpy(copy=False)

        if len(feats) <= window_size:
            continue

        X_list: list[np.ndarray] = []
        y_list: list[float] = []
        y_true_list: list[float] = []
        date_list: list[np.datetime64] = []
        for i in range(window_size, len(feats)):
            X_list.append(feats[i - window_size : i])
            y_list.append(float(y[i - 1]))
            y_true_list.append(float(y_true[i - 1]))
            date_list.append(dates[i - 1])

        X_sym = np.stack(X_list, axis=0)
        y_sym = np.asarray(y_list, dtype=np.float32)
        y_true_sym = np.asarray(y_true_list, dtype=np.float32)
        dates_sym = np.asarray(date_list)

        n = len(X_sym)
        n_test = max(1, int(round(n * test_frac)))
        n_rem = n - n_test
        if n_rem < 2:
            continue

        n_val = max(1, int(round(n_rem * val_frac)))
        n_train = n_rem - n_val
        if n_train < 1:
            continue

        train_groups[sym] = (X_sym[:n_train], y_sym[:n_train], dates_sym[:n_train])
        val_groups[sym] = (
            X_sym[n_train:n_rem],
            y_sym[n_train:n_rem],
            dates_sym[n_train:n_rem],
        )
        test_groups[sym] = (X_sym[n_rem:], y_sym[n_rem:], dates_sym[n_rem:])

        meta_val_parts.append(
            pd.DataFrame(
                {
                    "symbol": sym,
                    "date": dates_sym[n_train:n_rem],
                    "y_true": y_true_sym[n_train:n_rem],
                }
            )
        )
        meta_test_parts.append(
            pd.DataFrame(
                {"symbol": sym, "date": dates_sym[n_rem:], "y_true": y_true_sym[n_rem:]}
            )
        )

    if not train_groups:
        raise ValueError(
            "No sequences were created. Check window size and CSV contents."
        )

    meta_val = pd.concat(meta_val_parts, ignore_index=True)
    meta_test = pd.concat(meta_test_parts, ignore_index=True)
    return train_groups, val_groups, test_groups, meta_val, meta_test


def _directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    yt = np.sign(y_true)
    yp = np.sign(y_pred)
    return float((yt == yp).mean())


def _max_drawdown(equity: np.ndarray) -> float:
    peak = np.maximum.accumulate(equity)
    dd = (equity / peak) - 1.0
    return float(dd.min())


def _positions_from_predictions(
    df: pd.DataFrame,
    *,
    strategy: str,
    threshold: float,
    tanh_alpha: float,
    topq: float,
) -> np.ndarray:
    pred = df["y_pred"].to_numpy(dtype=np.float32, copy=False)

    if strategy == "long_only":
        return np.ones_like(pred, dtype=np.float32)

    if strategy == "cash":
        return np.zeros_like(pred, dtype=np.float32)

    if strategy == "sign":
        return np.where(np.abs(pred) >= threshold, np.sign(pred), 0.0).astype(
            np.float32
        )

    if strategy == "long":
        return np.where(pred >= threshold, 1.0, 0.0).astype(np.float32)

    if strategy == "tanh":
        # Smooth position sizing in [-1, 1].
        return np.tanh(tanh_alpha * pred).astype(np.float32)

    if strategy == "topq":
        if not (0.0 < topq <= 0.5):
            raise ValueError("--topq must be in (0, 0.5]")

        out = np.zeros_like(pred, dtype=np.float32)
        # For each day: long top q fraction, short bottom q fraction, else flat.
        for _, idx in df.groupby("date", sort=True).groups.items():
            idx = np.asarray(list(idx), dtype=np.int64)
            if idx.size < 2:
                continue

            k = max(1, int(round(idx.size * topq)))
            order = np.argsort(pred[idx])
            short_idx = idx[order[:k]]
            long_idx = idx[order[-k:]]
            out[short_idx] = -1.0
            out[long_idx] = 1.0

        return out

    if strategy == "long_topq":
        if not (0.0 < topq <= 1.0):
            raise ValueError("--topq must be in (0, 1]")

        out = np.zeros_like(pred, dtype=np.float32)
        for _, idx in df.groupby("date", sort=True).groups.items():
            idx = np.asarray(list(idx), dtype=np.int64)
            if idx.size < 2:
                continue

            k = max(1, int(round(idx.size * topq)))
            order = np.argsort(pred[idx])
            long_idx = idx[order[-k:]]
            out[long_idx] = 1.0

        return out

    raise ValueError(f"unknown strategy: {strategy!r}")


def _backtest_strategy(
    meta_test: pd.DataFrame,
    y_pred: np.ndarray,
    *,
    strategy: str,
    threshold: float,
    cost_bps: float,
    tanh_alpha: float = 10.0,
    topq: float = 0.1,
) -> dict[str, float]:
    df = meta_test.copy()
    df["y_pred"] = y_pred.astype(np.float32, copy=False)
    df = df.sort_values(["symbol", "date"], kind="mergesort").reset_index(drop=True)

    pos = _positions_from_predictions(
        df,
        strategy=strategy,
        threshold=threshold,
        tanh_alpha=tanh_alpha,
        topq=topq,
    )
    df["pos"] = pos

    cost = cost_bps / 10_000.0
    df["turnover"] = (
        df.groupby("symbol", sort=False)["pos"].diff().abs().fillna(df["pos"].abs())
    )
    df["cost"] = df["turnover"] * cost
    df["strat_ret"] = (df["pos"] * df["y_true"]) - df["cost"]

    port = df.groupby("date", sort=True)["strat_ret"].mean()
    daily = port.to_numpy(dtype=np.float64, copy=False)
    equity = (1.0 + port).cumprod().to_numpy(dtype=np.float64, copy=False)

    mean = float(np.mean(daily))
    std = float(np.std(daily, ddof=1)) if len(daily) > 1 else 0.0
    sharpe = float(np.sqrt(252.0) * mean / std) if std > 0 else 0.0
    cagr = float(equity[-1] ** (252.0 / max(1, len(daily))) - 1.0)

    return {
        "days": float(len(daily)),
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": _max_drawdown(equity),
        "avg_daily_ret": mean,
        "avg_daily_vol": std,
    }


def _backtest_sign_strategy(
    meta_test: pd.DataFrame,
    y_pred: np.ndarray,
    *,
    threshold: float,
    cost_bps: float,
) -> dict[str, float]:
    return _backtest_strategy(
        meta_test,
        y_pred,
        strategy="sign",
        threshold=threshold,
        cost_bps=cost_bps,
    )


def _select_best_strategy_on_validation(
    meta_val: pd.DataFrame,
    y_pred_val: np.ndarray,
    *,
    cost_bps: float,
    tanh_alpha_grid: list[float],
    threshold_grid: list[float],
    topq_grid: list[float],
) -> tuple[str, dict[str, float]]:
    # Prefer profitability: maximize validation CAGR, break ties by Sharpe.
    best = ("", {"cagr": -1e30, "sharpe": -1e30})

    # Always include long-only and cash as baselines.
    for strat in ["cash", "long_only"]:
        bt = _backtest_strategy(
            meta_val,
            y_pred_val if strat != "long_only" else np.ones_like(y_pred_val),
            strategy=strat,
            threshold=0.0,
            cost_bps=cost_bps,
            tanh_alpha=10.0,
            topq=0.1,
        )
        if (bt["cagr"], bt["sharpe"]) > (best[1]["cagr"], best[1]["sharpe"]):
            best = (
                strat,
                {
                    "cagr": bt["cagr"],
                    "sharpe": bt["sharpe"],
                    "threshold": 0.0,
                    "tanh_alpha": 10.0,
                    "topq": 0.1,
                },
            )

    for threshold in threshold_grid:
        for strat in ["sign", "long"]:
            bt = _backtest_strategy(
                meta_val,
                y_pred_val,
                strategy=strat,
                threshold=float(threshold),
                cost_bps=cost_bps,
                tanh_alpha=10.0,
                topq=0.1,
            )
            if (bt["cagr"], bt["sharpe"]) > (best[1]["cagr"], best[1]["sharpe"]):
                best = (
                    strat,
                    {
                        "cagr": bt["cagr"],
                        "sharpe": bt["sharpe"],
                        "threshold": float(threshold),
                        "tanh_alpha": 10.0,
                        "topq": 0.1,
                    },
                )

    for alpha in tanh_alpha_grid:
        bt = _backtest_strategy(
            meta_val,
            y_pred_val,
            strategy="tanh",
            threshold=0.0,
            cost_bps=cost_bps,
            tanh_alpha=float(alpha),
            topq=0.1,
        )
        if (bt["cagr"], bt["sharpe"]) > (best[1]["cagr"], best[1]["sharpe"]):
            best = (
                "tanh",
                {
                    "cagr": bt["cagr"],
                    "sharpe": bt["sharpe"],
                    "threshold": 0.0,
                    "tanh_alpha": float(alpha),
                    "topq": 0.1,
                },
            )

    for q in topq_grid:
        for strat in ["topq", "long_topq"]:
            bt = _backtest_strategy(
                meta_val,
                y_pred_val,
                strategy=strat,
                threshold=0.0,
                cost_bps=cost_bps,
                tanh_alpha=10.0,
                topq=float(q),
            )
            if (bt["cagr"], bt["sharpe"]) > (best[1]["cagr"], best[1]["sharpe"]):
                best = (
                    strat,
                    {
                        "cagr": bt["cagr"],
                        "sharpe": bt["sharpe"],
                        "threshold": 0.0,
                        "tanh_alpha": 10.0,
                        "topq": float(q),
                    },
                )

    return best


def _profit_utility(
    model: tf.keras.Model,
    groups: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    *,
    alpha: float,
    cost_bps: float,
    risk_aversion: float,
    pos_l2: float,
    long_only: bool,
    use_sortino: bool = True,
    drawdown_penalty: float = 0.5,
    vol_target: float = 0.1,
) -> float:
    """
    Improved profit utility with Sortino ratio and drawdown penalty.

    Args:
        use_sortino: Use downside deviation instead of total std
        drawdown_penalty: Penalty factor for max drawdown
        vol_target: Target annualized volatility for position scaling
    """
    cost = cost_bps / 10_000.0
    pnls: list[np.ndarray] = []
    pos2: list[np.ndarray] = []

    for X_sym, y_sym, _ in groups.values():
        pred = (
            model.predict(X_sym, batch_size=1024, verbose=0)
            .reshape(-1)
            .astype(np.float32)
        )

        # Handle dual-output models (return pred + volatility)
        if pred.ndim > 1:
            pred = pred[:, 0]

        pos = np.tanh(alpha * pred).astype(np.float32)
        if long_only:
            pos = np.clip(pos, 0.0, 1.0)

        # Volatility-adjusted position sizing
        if vol_target > 0:
            # Scale positions by inverse volatility
            vol_scale = vol_target / (np.std(y_sym) + 1e-6)
            vol_scale = np.clip(vol_scale, 0.5, 2.0)  # Limit scaling
            pos = pos * vol_scale

        turnover = np.abs(np.diff(np.r_[0.0, pos])).astype(np.float32)
        pnl = (pos * y_sym) - (cost * turnover)
        pnls.append(pnl)
        pos2.append(pos * pos)

    pnl_all = np.concatenate(pnls, axis=0).astype(np.float64, copy=False)
    mean = float(np.mean(pnl_all))

    # Sortino: only penalize downside volatility
    if use_sortino:
        downside_pnls = pnl_all[pnl_all < 0]
        downside_std = (
            float(np.std(downside_pnls, ddof=1)) if len(downside_pnls) > 1 else 0.0
        )
        std = downside_std
    else:
        std = float(np.std(pnl_all, ddof=1)) if pnl_all.size > 1 else 0.0

    # Calculate max drawdown for penalty
    equity = np.cumprod(1.0 + pnl_all)
    peak = np.maximum.accumulate(equity)
    drawdown = (equity / peak) - 1.0
    max_dd = float(np.min(drawdown))

    reg = float(np.mean(np.concatenate(pos2, axis=0))) if pos2 else 0.0

    # Utility = mean - risk_aversion * downside_std - drawdown_penalty * |max_dd| - pos_l2 * pos^2
    return mean - (risk_aversion * std) + (drawdown_penalty * max_dd) - (pos_l2 * reg)


def _cummax(x: tf.Tensor) -> tf.Tensor:
    """Compute cumulative maximum (compatible with all TF 2.x versions)."""
    # Use scan to compute running max - works in all TF versions
    return tf.scan(tf.maximum, x, initializer=x[0])


def _fine_tune_for_profit(
    model: tf.keras.Model,
    train_groups: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    val_groups: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    *,
    epochs: int,
    learning_rate: float,
    alpha: float,
    cost_bps: float,
    risk_aversion: float,
    pos_l2: float,
    long_only: bool,
    patience: int,
    seed: int,
    use_sortino: bool = True,
    drawdown_penalty: float = 0.5,
    vol_target: float = 0.1,
    use_confidence: bool = False,
) -> None:
    """
    Fine-tune model for profit with improved risk management.

    Args:
        use_sortino: Use downside deviation in utility
        drawdown_penalty: Penalty for max drawdown
        vol_target: Target volatility for position scaling
        use_confidence: Use model confidence for position sizing
    """
    rng = np.random.default_rng(seed)
    optimizer = tf.keras.optimizers.AdamW(
        learning_rate=learning_rate, weight_decay=1e-4
    )
    cost = cost_bps / 10_000.0

    best_utility = -1e30
    best_weights = None
    bad_epochs = 0

    syms = list(train_groups.keys())

    for epoch in range(1, epochs + 1):
        rng.shuffle(syms)
        losses: list[float] = []
        utils: list[float] = []

        for sym in syms:
            X_sym_np, y_sym_np, _ = train_groups[sym]
            X_sym = tf.convert_to_tensor(X_sym_np, dtype=tf.float32)
            y_sym = tf.convert_to_tensor(y_sym_np, dtype=tf.float32)

            with tf.GradientTape() as tape:
                pred = model(X_sym, training=True)
                pred = tf.reshape(pred, [-1])

                # Handle dual-output models
                if len(pred.shape) > 1:
                    pred = pred[:, 0]

                pos = tf.tanh(alpha * pred)
                if long_only:
                    pos = tf.nn.relu(pos)

                # Volatility-adjusted position sizing
                if vol_target > 0:
                    sym_vol = tf.math.reduce_std(y_sym) + 1e-6
                    vol_scale = tf.clip_by_value(vol_target / sym_vol, 0.5, 2.0)
                    pos = pos * vol_scale

                pos_prev = tf.concat([tf.zeros([1], dtype=pos.dtype), pos[:-1]], axis=0)
                turnover = tf.abs(pos - pos_prev)
                pnl = (pos * y_sym) - (cost * turnover)

                mean = tf.reduce_mean(pnl)

                # Sortino: downside deviation
                if use_sortino:
                    downside_pnls = tf.boolean_mask(pnl, pnl < 0)
                    std = tf.cond(
                        tf.size(downside_pnls) > 1,
                        lambda: tf.math.reduce_std(downside_pnls) + 1e-8,
                        lambda: tf.constant(1e-8),
                    )
                else:
                    std = tf.math.reduce_std(pnl) + 1e-8

                reg = tf.reduce_mean(pos * pos)

                # Drawdown penalty (FIXED: subtract absolute drawdown)
                cumulative_pnl = tf.math.cumprod(1.0 + pnl)
                # Use custom cummax for TF compatibility
                running_max = _cummax(cumulative_pnl)
                drawdown = (cumulative_pnl / running_max) - 1.0
                max_dd = tf.reduce_min(drawdown)

                # FIXED: max_dd is negative, so we subtract its absolute value
                utility = (
                    mean
                    - (risk_aversion * std)
                    - (
                        drawdown_penalty * tf.abs(max_dd)
                    )  # FIXED: was + (drawdown_penalty * max_dd)
                    - (pos_l2 * reg)
                )
                loss = -utility

            grads = tape.gradient(loss, model.trainable_variables)
            grads = [
                g if g is not None else tf.zeros_like(v)
                for g, v in zip(grads, model.trainable_variables)
            ]
            optimizer.apply_gradients(zip(grads, model.trainable_variables))
            losses.append(float(loss.numpy()))
            utils.append(float(utility.numpy()))

        val_utility = _profit_utility(
            model,
            val_groups,
            alpha=alpha,
            cost_bps=cost_bps,
            risk_aversion=risk_aversion,
            pos_l2=pos_l2,
            long_only=long_only,
            use_sortino=use_sortino,
            drawdown_penalty=drawdown_penalty,
            vol_target=vol_target,
        )
        print(
            f"profit_epoch={epoch}/{epochs} train_loss={np.mean(losses):.6g} train_utility={np.mean(utils):.6g} val_utility={val_utility:.6g}"
        )

        if val_utility > best_utility:
            best_utility = val_utility
            best_weights = model.get_weights()
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                break

    if best_weights is not None:
        model.set_weights(best_weights)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Train LSTM model on US stock market returns per symbol."
    )
    p.add_argument(
        "--csv",
        default="us_stock_market.csv",
        help="Path to CSV with columns date,symbol,open,close,low,high,volume (default: us_stock_market.csv)",
    )
    p.add_argument(
        "--window",
        type=int,
        default=60,
        help="Lookback window size (recommended: 60 for daily stock data)",
    )
    p.add_argument(
        "--test-frac",
        type=float,
        default=0.3,
        help="Fraction of samples per symbol held out at the end for test/val",
    )
    p.add_argument(
        "--val-frac",
        type=float,
        default=0.1,
        help="Fraction of the non-test part used for validation (time-based tail)",
    )
    p.add_argument(
        "--cs-mode",
        choices=["none", "demean", "zscore"],
        default="none",
        help="Optional cross-sectional transform by date to focus on alpha (none/demean/zscore)",
    )
    p.add_argument(
        "--ret-clip",
        type=float,
        default=0.0,
        help="Optional clip for features/target (log-return units); 0 disables",
    )
    p.add_argument(
        "--y-demean",
        action="store_true",
        help="Demean the training label cross-sectionally by date (PnL still uses raw returns)",
    )
    p.add_argument(
        "--max-symbols",
        type=int,
        default=50,
        help="Limit number of symbols for faster runs (use 0 for all)",
    )
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument(
        "--objective",
        choices=["mse", "profit"],
        default="mse",
        help="Training objective: mse (predict returns) or profit (fine-tune to maximize utility)",
    )
    p.add_argument(
        "--pretrain-epochs",
        type=int,
        default=0,
        help="When --objective=profit, number of MSE pretrain epochs before profit fine-tuning",
    )
    p.add_argument(
        "--profit-lr",
        type=float,
        default=1e-4,
        help="When --objective=profit, learning rate for profit fine-tuning",
    )
    p.add_argument(
        "--tanh-alpha",
        type=float,
        default=5.0,  # Reduced from 10.0 for more conservative position sizing
        help="Slope for tanh position sizing (lower = more conservative)",
    )
    p.add_argument(
        "--risk-aversion",
        type=float,
        default=0.25,  # Increased from 0.1 for more risk penalty
        help="Penalty on pnl stddev in profit utility (higher => less risk)",
    )
    p.add_argument(
        "--pos-l2",
        type=float,
        default=0.02,  # Increased from 0.0 for more position regularization
        help="L2 penalty on positions in profit utility",
    )
    p.add_argument(
        "--profit-patience",
        type=int,
        default=5,  # Increased from 3 for better convergence
        help="Early-stopping patience (epochs) during profit fine-tuning",
    )
    p.add_argument(
        "--profit-long-only",
        action="store_true",
        help="When --objective=profit, constrain positions to be long-only (no shorts)",
    )
    p.add_argument(
        "--use-sortino",
        action="store_true",
        help="Use Sortino ratio (downside deviation) instead of Sharpe in profit utility",
    )
    p.add_argument(
        "--drawdown-penalty",
        type=float,
        default=0.5,
        help="Penalty factor for max drawdown in profit utility (higher => avoid drawdowns)",
    )
    p.add_argument(
        "--vol-target",
        type=float,
        default=0.1,
        help="Target annualized volatility for position scaling (0 disables)",
    )
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument(
        "--shuffle-train",
        action="store_true",
        help="Shuffle training samples (recommended for multi-symbol)",
    )
    p.add_argument(
        "--cost-bps",
        type=float,
        default=1.0,
        help="Transaction cost in bps per 1.0 of position change",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Abstain (go flat) if |pred| < threshold",
    )
    p.add_argument(
        "--topq",
        type=float,
        default=0.1,
        help="For topq backtest: long top q and short bottom q fraction each day",
    )
    p.add_argument(
        "--tune-strategy",
        action="store_true",
        help="Tune strategy (threshold/alpha/topq) on the validation window and report best on test",
    )
    p.add_argument(
        "--save-model",
        default="",
        help="Optional path to save the trained Keras model (recommended extension: .keras)",
    )
    args = p.parse_args()

    max_symbols = None if args.max_symbols == 0 else args.max_symbols
    data_cfg = DataConfig(
        csv_path=args.csv,
        window_size=args.window,
        test_frac=args.test_frac,
        val_frac=args.val_frac,
        cs_mode=args.cs_mode,
        ret_clip=args.ret_clip,
        y_demean=bool(args.y_demean),
        max_symbols=max_symbols,
        seed=args.seed,
    )
    _set_seeds(data_cfg.seed)

    df = _load_and_engineer_features(data_cfg)
    train_groups, val_groups, test_groups, meta_val, meta_test = (
        _make_sequences_grouped(
            df,
            window_size=data_cfg.window_size,
            test_frac=data_cfg.test_frac,
            val_frac=data_cfg.val_frac,
        )
    )
    X_train = np.concatenate([v[0] for v in train_groups.values()], axis=0)
    y_train = np.concatenate([v[1] for v in train_groups.values()], axis=0)
    X_val = np.concatenate([v[0] for v in val_groups.values()], axis=0)
    y_val = np.concatenate([v[1] for v in val_groups.values()], axis=0)
    X_test = np.concatenate([v[0] for v in test_groups.values()], axis=0)
    y_test = np.concatenate([v[1] for v in test_groups.values()], axis=0)

    model_cfg = ModelConfig(window_size=args.window, n_features=X_train.shape[-1])
    model = build_model(model_cfg)

    # Adapt normalization layer on training data so the model carries scaling.
    try:
        norm = model.get_layer("norm")
    except ValueError:
        norm = None
    if norm is not None:
        norm.adapt(X_train)

    if args.objective == "mse":
        callbacks: list[tf.keras.callbacks.Callback] = [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=3, restore_best_weights=True
            ),
        ]
        model.fit(
            X_train,
            y_train,
            epochs=args.epochs,
            batch_size=args.batch_size,
            validation_data=(X_val, y_val),
            verbose=2,
            shuffle=bool(args.shuffle_train),
            callbacks=callbacks,
        )
    else:
        # Optional supervised warm-start.
        if args.pretrain_epochs > 0:
            model.fit(
                X_train,
                y_train,
                epochs=args.pretrain_epochs,
                batch_size=args.batch_size,
                validation_data=(X_val, y_val),
                verbose=2,
                shuffle=bool(args.shuffle_train),
            )

        profit_epochs = max(0, int(args.epochs) - int(args.pretrain_epochs))
        if profit_epochs > 0:
            _fine_tune_for_profit(
                model,
                train_groups=train_groups,
                val_groups=val_groups,
                epochs=profit_epochs,
                learning_rate=float(args.profit_lr),
                alpha=float(args.tanh_alpha),
                cost_bps=float(args.cost_bps),
                risk_aversion=float(args.risk_aversion),
                pos_l2=float(args.pos_l2),
                long_only=bool(args.profit_long_only),
                patience=int(args.profit_patience),
                seed=int(args.seed),
                use_sortino=bool(args.use_sortino),
                drawdown_penalty=float(args.drawdown_penalty),
                vol_target=float(args.vol_target),
            )

    if args.save_model:
        out_dir = os.path.dirname(args.save_model)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        model.save(args.save_model)

    y_pred_val = (
        model.predict(X_val, batch_size=args.batch_size).reshape(-1).astype(np.float32)
    )
    y_pred = (
        model.predict(X_test, batch_size=args.batch_size).reshape(-1).astype(np.float32)
    )

    mse = float(np.mean((y_test - y_pred) ** 2))
    mae = float(np.mean(np.abs(y_test - y_pred)))

    # Simple baseline: predict 0 next-day return (no change).
    base_mse = float(np.mean((y_test - 0.0) ** 2))
    base_mae = float(np.mean(np.abs(y_test - 0.0)))

    da = _directional_accuracy(y_test, y_pred)
    base_da = _directional_accuracy(y_test, np.zeros_like(y_test))

    print(f"test_mse={mse:.6g} test_mae={mae:.6g} dir_acc={da:.4f}")
    print(
        f"baseline_mse={base_mse:.6g} baseline_mae={base_mae:.6g} baseline_dir_acc={base_da:.4f}"
    )
    print("predictions_head:", y_pred[:5].tolist())

    if args.tune_strategy:
        strat, params = _select_best_strategy_on_validation(
            meta_val,
            y_pred_val,
            cost_bps=float(args.cost_bps),
            tanh_alpha_grid=[1.0, 5.0, 10.0, 20.0],
            threshold_grid=[0.0, 0.0005, 0.001, 0.002],
            topq_grid=[0.02, 0.05, 0.1, 0.2],
        )
        print(
            "best_strategy_on_val:",
            f"strategy={strat}",
            f"val_cagr={params['cagr']:.4f}",
            f"val_sharpe={params['sharpe']:.3f}",
            f"threshold={params['threshold']}",
            f"tanh_alpha={params['tanh_alpha']}",
            f"topq={params['topq']}",
        )

        y_pred_for_test = y_pred if strat != "long_only" else np.ones_like(y_pred)
        bt_best = _backtest_strategy(
            meta_test,
            y_pred_for_test,
            strategy=strat,
            threshold=float(params["threshold"]),
            cost_bps=float(args.cost_bps),
            tanh_alpha=float(params["tanh_alpha"]),
            topq=float(params["topq"]),
        )
        print(
            "backtest_best:",
            f"days={int(bt_best['days'])}",
            f"cagr={bt_best['cagr']:.4f}",
            f"sharpe={bt_best['sharpe']:.3f}",
            f"max_dd={bt_best['max_drawdown']:.3f}",
        )
    else:
        bt = _backtest_sign_strategy(
            meta_test,
            y_pred,
            threshold=float(args.threshold),
            cost_bps=float(args.cost_bps),
        )
        print(
            "backtest:",
            f"days={int(bt['days'])}",
            f"cagr={bt['cagr']:.4f}",
            f"sharpe={bt['sharpe']:.3f}",
            f"max_dd={bt['max_drawdown']:.3f}",
        )
        for name, strat in [
            ("backtest_tanh", "tanh"),
            ("backtest_topq", "topq"),
            ("backtest_long_topq", "long_topq"),
            ("backtest_long", "long"),
            ("backtest_long_only", "long_only"),
        ]:
            bt_s = _backtest_strategy(
                meta_test,
                y_pred if strat != "long_only" else np.ones_like(y_pred),
                strategy=strat,
                threshold=float(args.threshold),
                cost_bps=float(args.cost_bps),
                tanh_alpha=float(args.tanh_alpha),
                topq=float(args.topq),
            )
            print(
                f"{name}:",
                f"cagr={bt_s['cagr']:.4f}",
                f"sharpe={bt_s['sharpe']:.3f}",
                f"max_dd={bt_s['max_drawdown']:.3f}",
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
