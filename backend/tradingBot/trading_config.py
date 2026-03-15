"""
Lightweight trading configuration.

Separated from live_trading.py to avoid importing TensorFlow on startup.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TradingConfig:
    """Configuration for live trading engine."""

    symbols: list[str] = field(default_factory=lambda: ["AAPL", "MSFT", "GOOGL"])
    max_position_size: float = 0.1
    max_positions: int = 5
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    signal_threshold: float = 0.15
    rebalance_interval: int = 5
    max_trade_per_symbol: int = 10
    use_trailing_stop: bool = False
    trail_percent: float = 0.02
    models_dir: str = str(Path(__file__).parent / "artifacts" / "models")
    data_dir: str = str(Path(__file__).parent / "outputs" / "live_trading")
    paper_trading: bool = True
