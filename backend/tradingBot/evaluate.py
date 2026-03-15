from __future__ import annotations

import argparse
import importlib.util
import os

import numpy as np
import tensorflow as tf

from train import DataConfig, _load_and_engineer_features, _make_sequences_grouped


def _directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate directional accuracy of predictions.

    Args:
        y_true: Actual values
        y_pred: Predicted values

    Returns:
        Fraction of correct direction predictions
    """
    yt = np.sign(y_true)
    yp = np.sign(y_pred)
    return float((yt == yp).mean())


def _require_matplotlib() -> None:
    """Check if matplotlib is installed, exit with helpful message if not."""
    if importlib.util.find_spec("matplotlib") is None:
        raise SystemExit(
            "matplotlib is not installed in this environment.\n"
            "Install it (inside the venv) then re-run:\n"
            "  .venv/bin/python -m pip install matplotlib\n"
        )


def _calculate_detailed_metrics(
    equity: pd.Series, returns: pd.Series
) -> dict[str, float]:
    """Calculate comprehensive performance metrics.

    Args:
        equity: Equity curve series
        returns: Daily returns series

    Returns:
        Dictionary of performance metrics
    """
    # Basic stats
    total_return = float((equity.iloc[-1] / equity.iloc[0]) - 1)
    days = len(returns)
    annualized_return = float((1 + total_return) ** (252 / days) - 1) if days > 0 else 0

    # Risk metrics
    daily_vol = float(returns.std()) * np.sqrt(252) if len(returns) > 1 else 0
    sharpe = float(annualized_return / daily_vol) if daily_vol > 0 else 0

    # Drawdown analysis
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak
    max_drawdown = float(drawdown.min())

    # Win/loss stats
    wins = (returns > 0).sum()
    losses = (returns < 0).sum()
    win_rate = float(wins / (wins + losses)) if (wins + losses) > 0 else 0

    avg_win = float(returns[returns > 0].mean()) if wins > 0 else 0
    avg_loss = float(returns[returns < 0].mean()) if losses > 0 else 0
    profit_factor = float(abs(avg_win / avg_loss)) if avg_loss != 0 else float("inf")

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "daily_volatility": daily_vol,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_days": days,
        "avg_daily_return": float(returns.mean()),
    }


def _print_metrics_table(metrics_by_strategy: dict[str, dict[str, float]]) -> None:
    """Print a formatted table of performance metrics.

    Args:
        metrics_by_strategy: Dictionary mapping strategy names to metrics
    """
    print("\n" + "=" * 100)
    print("📊 PERFORMANCE METRICS SUMMARY")
    print("=" * 100)

    # Header
    headers = [
        "Strategy",
        "Total Return",
        "Ann. Return",
        "Sharpe",
        "Max DD",
        "Win Rate",
        "Profit Factor",
    ]
    print(
        f"{headers[0]:<20} {headers[1]:<15} {headers[2]:<15} {headers[3]:<10} {headers[4]:<12} {headers[5]:<12} {headers[6]:<15}"
    )
    print("-" * 100)

    # Rows
    for strategy, metrics in metrics_by_strategy.items():
        print(
            f"{strategy:<20} "
            f"{metrics['total_return'] * 100:>13.2f}%  "
            f"{metrics['annualized_return'] * 100:>13.2f}%  "
            f"{metrics['sharpe_ratio']:>10.3f}  "
            f"{metrics['max_drawdown'] * 100:>10.2f}%  "
            f"{metrics['win_rate'] * 100:>10.1f}%  "
            f"{metrics['profit_factor']:>13.2f}"
        )

    print("=" * 100 + "\n")


def _equity_from_predictions(
    meta_test,
    y_pred: np.ndarray,
    *,
    strategy: str,
    threshold: float,
    cost_bps: float,
    tanh_alpha: float,
    topq: float,
) -> tuple[pd.Series, pd.Series]:
    """Calculate equity curve from model predictions using specified strategy.

    This function simulates trading based on model predictions and computes
    the resulting equity curve after transaction costs.

    Args:
        meta_test: DataFrame with symbol, date, y_true columns
        y_pred: Model predictions array
        strategy: Trading strategy name (sign, long, tanh, topq, long_topq)
        threshold: Threshold for entry signals
        cost_bps: Transaction cost in basis points
        tanh_alpha: Scaling factor for tanh position sizing
        topq: Fraction for top/bottom quantile strategies

    Returns:
        Tuple of (portfolio returns series, equity curve series)
    """
    import pandas as pd

    df = meta_test.copy()
    df["y_pred"] = y_pred.astype(np.float32, copy=False)
    df = df.sort_values(["symbol", "date"], kind="mergesort").reset_index(drop=True)

    pred = df["y_pred"].to_numpy(dtype=np.float32, copy=False)
    if strategy == "sign":
        pos = np.where(np.abs(pred) >= threshold, np.sign(pred), 0.0).astype(np.float32)
    elif strategy == "long":
        pos = np.where(pred >= threshold, 1.0, 0.0).astype(np.float32)
    elif strategy == "tanh":
        pos = np.tanh(tanh_alpha * pred).astype(np.float32)
    elif strategy == "topq":
        if not (0.0 < topq <= 0.5):
            raise ValueError("--topq must be in (0, 0.5]")
        pos = np.zeros_like(pred, dtype=np.float32)
        for _, idx in df.groupby("date", sort=True).groups.items():
            idx = np.asarray(list(idx), dtype=np.int64)
            if idx.size < 2:
                continue
            k = max(1, int(round(idx.size * topq)))
            order = np.argsort(pred[idx])
            pos[idx[order[:k]]] = -1.0
            pos[idx[order[-k:]]] = 1.0
    elif strategy == "long_topq":
        if not (0.0 < topq <= 1.0):
            raise ValueError("--topq must be in (0, 1]")
        pos = np.zeros_like(pred, dtype=np.float32)
        for _, idx in df.groupby("date", sort=True).groups.items():
            idx = np.asarray(list(idx), dtype=np.int64)
            if idx.size < 2:
                continue
            k = max(1, int(round(idx.size * topq)))
            order = np.argsort(pred[idx])
            pos[idx[order[-k:]]] = 1.0
    else:
        raise ValueError(f"unknown strategy: {strategy!r}")
    df["pos"] = pos

    cost = cost_bps / 10_000.0
    df["turnover"] = (
        df.groupby("symbol", sort=False)["pos"].diff().abs().fillna(df["pos"].abs())
    )
    df["cost"] = df["turnover"] * cost
    df["strat_ret"] = (df["pos"] * df["y_true"]) - df["cost"]

    port = df.groupby("date", sort=True)["strat_ret"].mean()
    equity = (1.0 + port).cumprod()
    return port, equity


def main() -> int:
    """Main entry point for model evaluation.

    This function loads a trained model, evaluates it on test data,
    generates equity curves for multiple strategies, and saves results.

    Returns:
        Exit code (0 for success)
    """
    p = argparse.ArgumentParser(
        description="Evaluate a saved model on forex_data.csv and write a performance plot."
    )
    p.add_argument(
        "--model",
        required=True,
        help="Path to saved Keras model (e.g. artifacts/model.keras)",
    )
    p.add_argument(
        "--csv",
        default="us_stock_market.csv",
        help="Path to CSV with columns date,symbol,open,close,low,high,volume (default: us_stock_market.csv)",
    )
    p.add_argument(
        "--max-symbols",
        type=int,
        default=50,
        help="Limit number of symbols for faster runs (use 0 for all)",
    )
    p.add_argument(
        "--test-frac",
        type=float,
        default=0.3,
        help="Fraction of samples per symbol held out at the end for test",
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
        help="Cross-sectional transform by date (must match training if used)",
    )
    p.add_argument(
        "--ret-clip",
        type=float,
        default=0.0,
        help="Clip for features/target (must match training if used)",
    )
    p.add_argument(
        "--y-demean",
        action="store_true",
        help="If training used --y-demean, enable the same label transform for evaluation metrics",
    )
    p.add_argument("--cost-bps", type=float, default=1.0)
    p.add_argument("--threshold", type=float, default=0.0)
    p.add_argument("--tanh-alpha", type=float, default=10.0)
    p.add_argument("--topq", type=float, default=0.1)
    p.add_argument(
        "--out",
        default="evaluation.png",
        help="Output plot path (PNG)",
    )
    p.add_argument(
        "--symbol",
        default="",
        help="Optional symbol to plot (otherwise portfolio-level only)",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed performance metrics",
    )
    args = p.parse_args()

    _require_matplotlib()
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    model = tf.keras.models.load_model(args.model)
    window_size = int(model.input_shape[1])

    max_symbols = None if args.max_symbols == 0 else args.max_symbols
    data_cfg = DataConfig(
        csv_path=args.csv,
        window_size=window_size,
        test_frac=float(args.test_frac),
        val_frac=float(args.val_frac),
        cs_mode=str(args.cs_mode),
        ret_clip=float(args.ret_clip),
        y_demean=bool(args.y_demean),
        max_symbols=max_symbols,
        seed=0,
    )

    df = _load_and_engineer_features(data_cfg)
    _, _, test_groups, _, meta_test = _make_sequences_grouped(
        df,
        window_size=window_size,
        test_frac=float(args.test_frac),
        val_frac=float(args.val_frac),
    )
    X_test = np.concatenate([v[0] for v in test_groups.values()], axis=0)
    y_test = np.concatenate([v[1] for v in test_groups.values()], axis=0)
    y_pred = model.predict(X_test, batch_size=1024).reshape(-1).astype(np.float32)

    port_sign, equity_sign = _equity_from_predictions(
        meta_test,
        y_pred,
        strategy="sign",
        threshold=float(args.threshold),
        cost_bps=float(args.cost_bps),
        tanh_alpha=float(args.tanh_alpha),
        topq=float(args.topq),
    )
    port_long, equity_long = _equity_from_predictions(
        meta_test,
        y_pred,
        strategy="long",
        threshold=float(args.threshold),
        cost_bps=float(args.cost_bps),
        tanh_alpha=float(args.tanh_alpha),
        topq=float(args.topq),
    )
    port_tanh, equity_tanh = _equity_from_predictions(
        meta_test,
        y_pred,
        strategy="tanh",
        threshold=float(args.threshold),
        cost_bps=float(args.cost_bps),
        tanh_alpha=float(args.tanh_alpha),
        topq=float(args.topq),
    )
    port_topq, equity_topq = _equity_from_predictions(
        meta_test,
        y_pred,
        strategy="topq",
        threshold=float(args.threshold),
        cost_bps=float(args.cost_bps),
        tanh_alpha=float(args.tanh_alpha),
        topq=float(args.topq),
    )
    port_long_topq, equity_long_topq = _equity_from_predictions(
        meta_test,
        y_pred,
        strategy="long_topq",
        threshold=float(args.threshold),
        cost_bps=float(args.cost_bps),
        tanh_alpha=float(args.tanh_alpha),
        topq=float(args.topq),
    )

    # Long-only comparator (pos=+1).
    meta_lo = meta_test.copy()
    meta_lo["y_pred"] = 1.0
    port_lo, equity_lo = _equity_from_predictions(
        meta_lo,
        np.ones_like(y_pred, dtype=np.float32),
        strategy="sign",
        threshold=-1.0,
        cost_bps=float(args.cost_bps),
        tanh_alpha=float(args.tanh_alpha),
        topq=float(args.topq),
    )

    fig, ax = plt.subplots(1, 1, figsize=(11, 5))
    ax.plot(
        equity_sign.index,
        equity_sign.to_numpy(),
        label="sign(pred)",
        linewidth=1.5,
    )
    ax.plot(
        equity_long.index,
        equity_long.to_numpy(),
        label="long(pred>thr)",
        linewidth=1.2,
        alpha=0.85,
    )
    ax.plot(
        equity_tanh.index,
        equity_tanh.to_numpy(),
        label=f"tanh({float(args.tanh_alpha):g}*pred)",
        linewidth=1.2,
        alpha=0.85,
    )
    ax.plot(
        equity_topq.index,
        equity_topq.to_numpy(),
        label=f"topq={float(args.topq):g}",
        linewidth=1.2,
        alpha=0.85,
    )
    ax.plot(
        equity_long_topq.index,
        equity_long_topq.to_numpy(),
        label=f"long_topq={float(args.topq):g}",
        linewidth=1.2,
        alpha=0.85,
    )
    ax.plot(
        equity_lo.index,
        equity_lo.to_numpy(),
        label="long-only",
        linewidth=1.2,
        alpha=0.8,
    )
    ax.set_title("Test-Window Equity Curve (Equal-Weighted Across Symbols)")
    ax.set_xlabel("date")
    ax.set_ylabel("equity")
    ax.grid(True, alpha=0.25)
    ax.legend()

    # Optional per-symbol plot: strategy vs actual next-day returns over time.
    if args.symbol:
        sub = meta_test.copy()
        sub["y_pred"] = y_pred
        sub = sub[sub["symbol"] == args.symbol].sort_values("date")
        if len(sub) == 0:
            raise SystemExit(f"symbol not found in evaluation set: {args.symbol!r}")

        pred_sym = sub["y_pred"].to_numpy(dtype=np.float32)
        pos_sign = np.sign(pred_sym)
        pos_tanh = np.tanh(float(args.tanh_alpha) * pred_sym)

        cost = float(args.cost_bps) / 10_000.0
        y_true = sub["y_true"].to_numpy(dtype=np.float32)
        daily_sign = (pos_sign * y_true) - (
            cost * np.abs(np.diff(np.r_[0.0, pos_sign]))
        )
        daily_tanh = (pos_tanh * y_true) - (
            cost * np.abs(np.diff(np.r_[0.0, pos_tanh]))
        )

        eq_sign = np.cumprod(1.0 + daily_sign)
        eq_tanh = np.cumprod(1.0 + daily_tanh)

        fig2, ax2 = plt.subplots(1, 1, figsize=(11, 4))
        ax2.plot(
            sub["date"].to_numpy(),
            eq_sign,
            label=f"{args.symbol} sign(pred)",
            linewidth=1.5,
        )
        ax2.plot(
            sub["date"].to_numpy(),
            eq_tanh,
            label=f"{args.symbol} tanh",
            linewidth=1.2,
            alpha=0.85,
        )
        ax2.set_title(f"Per-Symbol Equity (Test Window): {args.symbol}")
        ax2.set_xlabel("date")
        ax2.set_ylabel("equity")
        ax2.grid(True, alpha=0.25)
        ax2.legend()

    fig.tight_layout()
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    fig.savefig(args.out, dpi=140)
    print(f"wrote_plot={args.out}")

    # Print prediction metrics
    test_mse = float(np.mean((y_test - y_pred) ** 2))
    test_mae = float(np.mean(np.abs(y_test - y_pred)))
    print(f"\n📈 PREDICTION METRICS")
    print(f"  Test MSE:  {test_mse:.6g}")
    print(f"  Test MAE:  {test_mae:.6g}")
    print(f"  Directional Accuracy: {_directional_accuracy(y_test, y_pred):.4f}")

    # Calculate and print detailed strategy metrics
    if args.verbose:
        metrics_by_strategy = {
            "sign(pred)": _calculate_detailed_metrics(equity_sign, port_sign),
            "long(pred>thr)": _calculate_detailed_metrics(equity_long, port_long),
            "tanh": _calculate_detailed_metrics(equity_tanh, port_tanh),
            "topq": _calculate_detailed_metrics(equity_topq, port_topq),
            "long_topq": _calculate_detailed_metrics(equity_long_topq, port_long_topq),
            "long-only": _calculate_detailed_metrics(equity_lo, port_lo),
        }
        _print_metrics_table(metrics_by_strategy)
    else:
        print(f"\n💡 Use --verbose flag for detailed performance metrics")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
