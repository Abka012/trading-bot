"""
Trading Engine Service.

This module provides a background service that runs the live trading engine
alongside the FastAPI server. It enables:
- Starting/stopping the trading engine via API
- Real-time status updates
- Log streaming
- Thread-safe operation

Example:
    ```python
    from tradingBot.engine_service import TradingEngineService

    service = TradingEngineService()
    service.start()
    # ... trading runs in background ...
    service.stop()
    ```

Author: Abka Ferguson
Date: 2026
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from tradingBot.live_trading import LiveTradingEngine, TradingConfig

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """A single log entry from the trading engine.

    Attributes:
        timestamp: When the log was created
        level: Log level (INFO, WARNING, ERROR)
        message: Log message
    """

    timestamp: str
    level: str
    message: str


@dataclass
class EngineStats:
    """Statistics from the trading engine.

    Attributes:
        running: Whether engine is currently running
        start_time: When the engine was started
        trades_executed: Number of trades executed
        total_pnl: Total profit and loss
        active_positions: Number of active positions
        errors: Number of errors encountered
    """

    running: bool = False
    start_time: Optional[datetime] = None
    trades_executed: int = 0
    total_pnl: float = 0.0
    active_positions: int = 0
    errors: int = 0


class TradingEngineService:
    """Service for managing the trading engine lifecycle.

    This class wraps the LiveTradingEngine and provides:
    - Thread-safe start/stop operations
    - Log buffering for API access
    - Statistics tracking
    - Health monitoring

    The service runs the trading engine in a separate thread,
    allowing the FastAPI server to continue handling requests.

    Attributes:
        config: Trading configuration
        stats: Current engine statistics
    """

    _instance: Optional["TradingEngineService"] = None
    _lock = threading.Lock()

    def __new__(cls, config: Optional[TradingConfig] = None) -> "TradingEngineService":
        """Singleton pattern to ensure only one engine service exists."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config: Optional[TradingConfig] = None):
        """Initialize the trading engine service.

        Args:
            config: Optional trading configuration
        """
        if self._initialized:
            return

        self._initialized = True
        self.config = config or TradingConfig(
            symbols=["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
            max_position_size=0.05,
            max_positions=5,
            stop_loss_pct=0.02,
            take_profit_pct=0.04,
            signal_threshold=0.15,
            paper_trading=True,
        )

        self.engine: Optional[LiveTradingEngine] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._logs: deque = deque(maxlen=100)  # Keep last 100 logs
        self._stats = EngineStats()
        self._callbacks: list[Callable] = []

        # Custom log handler
        self._log_handler = None

    def _add_log(self, level: str, message: str) -> None:
        """Add a log entry to the buffer.

        Args:
            level: Log level
            message: Log message
        """
        entry = LogEntry(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            level=level,
            message=message,
        )
        self._logs.append(entry)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(entry)
            except Exception as e:
                logger.error(f"Error in log callback: {e}")

    def _setup_logging(self) -> None:
        """Setup custom logging to capture engine logs."""

        class EngineLogHandler(logging.Handler):
            def __init__(self, service):
                super().__init__()
                self.service = service

            def emit(self, record):
                msg = self.format(record)
                level = record.levelname
                self.service._add_log(level, msg)

        self._log_handler = EngineLogHandler(self)
        self._log_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s")
        self._log_handler.setFormatter(formatter)

        # Add to tradingBot logger
        bot_logger = logging.getLogger("tradingBot")
        bot_logger.addHandler(self._log_handler)
        bot_logger.setLevel(logging.INFO)

    def start(self) -> bool:
        """Start the trading engine in a background thread.

        Returns:
            True if started successfully, False if already running
        """
        if self._stats.running:
            self._add_log("WARNING", "Engine already running")
            return False

        try:
            self._add_log("INFO", "Starting trading engine...")

            # Create engine instance
            self.engine = LiveTradingEngine(self.config)

            # Setup logging
            self._setup_logging()

            # Clear stop event
            self._stop_event.clear()

            # Start thread
            self._thread = threading.Thread(target=self._run_engine, daemon=True)
            self._thread.start()

            # Update stats
            self._stats.running = True
            self._stats.start_time = datetime.now()
            self._stats.errors = 0

            self._add_log("INFO", "Trading engine started successfully")
            return True

        except Exception as e:
            self._add_log("ERROR", f"Failed to start engine: {e}")
            self._stats.errors += 1
            return False

    def _run_engine(self) -> None:
        """Run the trading engine main loop.

        This method runs in a separate thread.
        """
        try:
            # Initialize engine
            if not self.engine.initialize():
                self._add_log("ERROR", "Engine initialization failed")
                self._stats.running = False
                self._stats.errors += 1
                return

            self._add_log("INFO", "Engine initialized, starting trading loop...")

            # Run engine loop
            while self._running and not self._stop_event.is_set():
                try:
                    # Check if market is open
                    if (
                        self.engine.alpaca_client
                        and self.engine.alpaca_client.is_market_open()
                    ):
                        # Rebalance at intervals
                        if (
                            self.engine._last_rebalance is None
                            or datetime.now() - self.engine._last_rebalance
                            >= timedelta(minutes=self.engine.config.rebalance_interval)
                        ):
                            self._add_log("INFO", "Rebalancing portfolio...")
                            self.engine._rebalance()

                        # Save equity snapshot
                        self.engine._save_equity_snapshot()

                        # Update stats
                        positions = self.engine.alpaca_client.get_all_positions()
                        self._stats.active_positions = len(positions)
                        self._stats.trades_executed = len(self.engine.trade_history)

                    else:
                        time.sleep(60)  # Check every minute when market closed

                    # Save trades
                    self.engine._save_trades()

                    # Wait for next cycle
                    time.sleep(10)

                except Exception as e:
                    self._add_log("ERROR", f"Error in trading loop: {e}")
                    self._stats.errors += 1
                    time.sleep(30)

        except Exception as e:
            self._add_log("ERROR", f"Engine error: {e}")
            self._stats.errors += 1

        finally:
            self._stats.running = False
            self._add_log("INFO", "Trading engine stopped")

    def stop(self) -> bool:
        """Stop the trading engine.

        Returns:
            True if stopped successfully
        """
        if not self._stats.running:
            self._add_log("WARNING", "Engine not running")
            return True

        try:
            self._add_log("INFO", "Stopping trading engine...")

            # Signal stop
            self._stop_event.set()

            # Stop engine
            if self.engine:
                self.engine.stop()

            # Wait for thread to finish
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=10)

            # Update stats
            self._stats.running = False

            self._add_log("INFO", "Trading engine stopped successfully")
            return True

        except Exception as e:
            self._add_log("ERROR", f"Error stopping engine: {e}")
            self._stats.errors += 1
            return False

    def get_status(self) -> dict:
        """Get current engine status.

        Returns:
            Dictionary with engine status information
        """
        return {
            "running": self._stats.running,
            "start_time": self._stats.start_time.isoformat()
            if self._stats.start_time
            else None,
            "uptime_seconds": (
                (datetime.now() - self._stats.start_time).total_seconds()
                if self._stats.start_time
                else 0
            ),
            "trades_executed": self._stats.trades_executed,
            "active_positions": self._stats.active_positions,
            "errors": self._stats.errors,
            "config": {
                "symbols": self.config.symbols,
                "paper_trading": self.config.paper_trading,
                "max_positions": self.config.max_positions,
                "max_position_size": self.config.max_position_size,
            },
        }

    def get_logs(self, limit: int = 50) -> list[dict]:
        """Get recent engine logs.

        Args:
            limit: Maximum number of logs to return

        Returns:
            List of log entries
        """
        logs = list(self._logs)[-limit:]
        return [
            {
                "timestamp": log.timestamp,
                "level": log.level,
                "message": log.message,
            }
            for log in logs
        ]

    def get_stats(self) -> EngineStats:
        """Get current engine statistics.

        Returns:
            EngineStats object
        """
        return self._stats

    def register_callback(self, callback: Callable) -> None:
        """Register a callback for log events.

        Args:
            callback: Function to call when new log arrives
        """
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable) -> None:
        """Unregister a log callback.

        Args:
            callback: Callback to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    @property
    def _running(self) -> bool:
        """Check if engine should be running."""
        return not self._stop_event.is_set()


# Import timedelta for the engine service
from datetime import timedelta

# Global service instance
_engine_service: Optional[TradingEngineService] = None


def get_engine_service(config: Optional[TradingConfig] = None) -> TradingEngineService:
    """Get or create the global engine service instance.

    Args:
        config: Optional configuration for first-time initialization

    Returns:
        TradingEngineService instance
    """
    global _engine_service
    if _engine_service is None:
        _engine_service = TradingEngineService(config)
    return _engine_service


def start_engine(config: Optional[TradingConfig] = None) -> bool:
    """Start the global trading engine.

    Args:
        config: Optional trading configuration

    Returns:
        True if started successfully
    """
    service = get_engine_service(config)
    return service.start()


def stop_engine() -> bool:
    """Stop the global trading engine.

    Returns:
        True if stopped successfully
    """
    if _engine_service is None:
        return False
    return _engine_service.stop()


def get_engine_status() -> dict:
    """Get the global engine status.

    Returns:
        Engine status dictionary
    """
    if _engine_service is None:
        return {"running": False, "error": "Engine not initialized"}
    return _engine_service.get_status()


def get_engine_logs(limit: int = 50) -> list[dict]:
    """Get recent engine logs.

    Args:
        limit: Maximum number of logs to return

    Returns:
        List of log entries
    """
    if _engine_service is None:
        return []
    return _engine_service.get_logs(limit)
