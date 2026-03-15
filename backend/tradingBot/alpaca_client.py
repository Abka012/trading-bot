"""
Alpaca API Client for Live Trading.

This module provides a client for interacting with the Alpaca trading API.
It handles:
- Authentication using API keys from environment variables
- Market data fetching (real-time and historical)
- Order placement and management
- Portfolio/account monitoring
- Position management

Example:
    ```python
    from tradingBot.alpaca_client import AlpacaClient

    client = AlpacaClient()

    # Get account info
    account = client.get_account()
    print(f"Account: {account.cash}")

    # Place an order
    order = client.place_order("AAPL", qty=1, side="buy", type="market")
    ```

Author: Abka Ferguson
Date: 2026
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderType, QueryOrderStatus
from alpaca.trading.models import (
    Calendar as AlpacaCalendar,
)
from alpaca.trading.models import (
    Clock as AlpacaClock,
)
from alpaca.trading.models import (
    Order as AlpacaOrder,
)
from alpaca.trading.models import (
    Position as AlpacaPosition,
)
from alpaca.trading.models import (
    TradeAccount as AlpacaAccount,
)
from alpaca.trading.requests import (
    GetPortfolioHistoryRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    StopLimitOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
    TrailingStopOrderRequest,
)
from alpaca.trading.stream import TradingStream
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class TradingMode(Enum):
    """Trading mode enumeration.

    Attributes:
        PAPER: Paper trading (simulated)
        LIVE: Live trading (real money)
    """

    PAPER = "paper"
    LIVE = "live"


@dataclass
class OrderConfig:
    """Configuration for placing orders.

    Attributes:
        symbol: Stock ticker symbol
        qty: Number of shares to trade
        side: Buy or sell
        order_type: Market, limit, stop, etc.
        limit_price: Price for limit orders
        stop_price: Price for stop orders
        take_profit: Take profit price level
        stop_loss: Stop loss price level
        trail_percent: Trailing stop percentage
        time_in_force: Order duration (GTC, DAY, etc.)
    """

    symbol: str
    qty: float
    side: str = "buy"
    order_type: str = "market"
    limit_price: float | None = None
    stop_price: float | None = None
    take_profit: float | None = None
    stop_loss: float | None = None
    trail_percent: float | None = None
    time_in_force: str = "gtc"


@dataclass
class TradeResult:
    """Result of a trade execution.

    Attributes:
        success: Whether the trade was successful
        order_id: Alpaca order ID
        symbol: Stock ticker symbol
        side: Buy or sell
        qty: Number of shares
        price: Execution price
        status: Order status
        message: Additional information
        timestamp: When the trade occurred
    """

    success: bool
    order_id: str | None = None
    symbol: str | None = None
    side: str | None = None
    qty: float | None = None
    price: float | None = None
    status: str | None = None
    message: str | None = None
    timestamp: datetime | None = None


@dataclass
class AccountInfo:
    """Account information summary.

    Attributes:
        account_id: Alpaca account ID
        cash: Available cash balance
        portfolio_value: Total portfolio value
        buying_power: Available buying power
        equity: Account equity
        last_equity: Previous day's equity
        day_trading_buying_power: Day trading buying power
        pattern_day_trader: Whether account is flagged as PDT
        trade_suspended: Whether trading is suspended
        currency: Account currency
    """

    account_id: str
    cash: float
    portfolio_value: float
    buying_power: float
    equity: float
    last_equity: float
    day_trading_buying_power: float
    pattern_day_trader: bool
    trade_suspended: bool
    currency: str


class AlpacaClient:
    """Client for interacting with Alpaca trading API.

    This class provides a high-level interface for:
    - Account management
    - Market data retrieval
    - Order placement and cancellation
    - Position management
    - Real-time trading updates

    The client supports both paper trading and live trading modes.
    Set ALPACA_TRADING_MODE environment variable to 'live' for live trading.

    Attributes:
        trading_mode: Current trading mode (paper or live)
        api_key: Alpaca API key
        secret_key: Alpaca API secret key
    """

    def __init__(self, api_key: str | None = None, secret_key: str | None = None):
        """Initialize the Alpaca client.

        Args:
            api_key: Optional Alpaca API key (defaults to env var)
            secret_key: Optional Alpaca secret key (defaults to env var)

        Raises:
            ValueError: If API credentials are not provided
        """
        # Get credentials from environment or parameters
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        self.base_url = os.getenv("ALPACA_BASE_URL", None)

        # Determine trading mode
        mode_str = os.getenv("ALPACA_TRADING_MODE", "paper").lower()
        self.trading_mode = (
            TradingMode.PAPER if mode_str == "paper" else TradingMode.LIVE
        )

        # Validate credentials
        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Alpaca API credentials not found. "
                "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in your .env file."
            )

        # Initialize clients
        self._trading_client = TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=self.trading_mode == TradingMode.PAPER,
        )

        self._data_client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
        )

        self._trading_stream = TradingStream(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=self.trading_mode == TradingMode.PAPER,
        )

        print(f"AlpacaClient initialized in {self.trading_mode.value.upper()} mode")

    def get_account(self) -> AccountInfo:
        """Get account information.

        Returns:
            AccountInfo with current account status

        Raises:
            Exception: If API call fails
        """
        account: AlpacaAccount = self._trading_client.get_account()

        return AccountInfo(
            account_id=str(account.id),
            cash=float(account.cash),
            portfolio_value=float(account.portfolio_value),
            buying_power=float(account.buying_power),
            equity=float(account.equity),
            last_equity=float(account.last_equity),
            day_trading_buying_power=float(account.daytrading_buying_power),
            pattern_day_trader=account.pattern_day_trader,
            trade_suspended=account.trade_suspended_by_user,
            currency=str(account.currency),
        )

    def get_clock(self) -> AlpacaClock:
        """Get market clock.

        Returns:
            Clock object with market open/close times
        """
        return self._trading_client.get_clock()

    def is_market_open(self) -> bool:
        """Check if the market is currently open.

        Returns:
            True if market is open, False otherwise
        """
        clock = self.get_clock()
        return clock.is_open

    def get_calendar(
        self, start: datetime | None = None, end: datetime | None = None
    ) -> list[AlpacaCalendar]:
        """Get market calendar.

        Args:
            start: Start date (defaults to today)
            end: End date (defaults to today)

        Returns:
            List of Calendar objects with market hours
        """
        if start is None:
            start = datetime.now()
        if end is None:
            end = start

        return self._trading_client.get_calendar(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
        )

    def get_position(self, symbol: str) -> AlpacaPosition | None:
        """Get current position for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Position object or None if no position
        """
        try:
            return self._trading_client.get_open_position(symbol)
        except Exception:
            return None

    def get_all_positions(self) -> list[AlpacaPosition]:
        """Get all open positions.

        Returns:
            List of Position objects
        """
        return self._trading_client.get_all_positions()

    def get_latest_price(self, symbol: str) -> float | None:
        """Get the latest price for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Latest bid/ask midpoint price or None
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = self._data_client.get_stock_latest_quote(request)
            if symbol in quote:
                bid = quote[symbol].bid_price
                ask = quote[symbol].ask_price
                return (bid + ask) / 2
        except Exception as e:
            print(f"Error getting price for {symbol}: {e}")
        return None

    def get_portfolio_history(
        self,
        period: str | None = "1D",
        timeframe: str | None = None,
        extended_hours: bool | None = True,
    ):
        """Get portfolio history for the account.

        Args:
            period: Duration (e.g., 1D, 1W, 1M)
            timeframe: Resolution (e.g., 1Min, 5Min, 1H, 1D)
            extended_hours: Include extended hours data if applicable

        Returns:
            PortfolioHistory model
        """
        history_filter = GetPortfolioHistoryRequest(
            period=period,
            timeframe=timeframe,
            extended_hours=extended_hours,
        )
        return self._trading_client.get_portfolio_history(history_filter)

    def get_historical_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        days: int = 30,
    ) -> dict[str, Any] | None:
        """Get historical price bars.

        Args:
            symbol: Stock ticker symbol
            timeframe: Timeframe (1Min, 5Min, 1Hour, 1Day, etc.)
            days: Number of days of data

        Returns:
            Dictionary with bars data or None
        """
        try:
            tf = TimeFrame.from_str(timeframe)
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=(datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
            )
            bars = self._data_client.get_stock_bars(request)
            if symbol in bars:
                return {
                    "symbol": symbol,
                    "bars": [
                        {
                            "timestamp": bar.timestamp.isoformat(),
                            "open": float(bar.open),
                            "high": float(bar.high),
                            "low": float(bar.low),
                            "close": float(bar.close),
                            "volume": int(bar.volume),
                        }
                        for bar in bars[symbol]
                    ],
                }
        except Exception as e:
            print(f"Error getting bars for {symbol}: {e}")
        return None

    def place_order(self, config: OrderConfig) -> TradeResult:
        """Place a trading order.

        Args:
            config: Order configuration

        Returns:
            TradeResult with order details
        """
        try:
            # Check if market is open
            if not self.is_market_open():
                return TradeResult(
                    success=False,
                    message="Market is currently closed. Orders cannot be placed.",
                )

            # Build order request based on type
            order_request = None

            if config.order_type == "market":
                # Market order with optional take profit/stop loss
                take_profit = None
                stop_loss = None

                if config.take_profit:
                    take_profit = TakeProfitRequest(limit_price=config.take_profit)

                if config.stop_loss:
                    stop_loss = StopLossRequest(stop_price=config.stop_loss)

                order_request = MarketOrderRequest(
                    symbol=config.symbol,
                    qty=config.qty,
                    side=OrderSide(config.side.lower()),
                    time_in_force=config.time_in_force,
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                )

            elif config.order_type == "limit":
                if not config.limit_price:
                    return TradeResult(
                        success=False, message="Limit price required for limit order"
                    )

                order_request = LimitOrderRequest(
                    symbol=config.symbol,
                    qty=config.qty,
                    side=OrderSide(config.side.lower()),
                    time_in_force=config.time_in_force,
                    limit_price=config.limit_price,
                )

            elif config.order_type == "stop":
                if not config.stop_price:
                    return TradeResult(
                        success=False, message="Stop price required for stop order"
                    )

                order_request = StopLimitOrderRequest(
                    symbol=config.symbol,
                    qty=config.qty,
                    side=OrderSide(config.side.lower()),
                    time_in_force=config.time_in_force,
                    stop_price=config.stop_price,
                    limit_price=config.limit_price or config.stop_price,
                )

            elif config.order_type == "trailing_stop":
                if not config.trail_percent:
                    return TradeResult(
                        success=False,
                        message="Trail percent required for trailing stop order",
                    )

                order_request = TrailingStopOrderRequest(
                    symbol=config.symbol,
                    qty=config.qty,
                    side=OrderSide(config.side.lower()),
                    time_in_force=config.time_in_force,
                    trail_percent=config.trail_percent,
                )

            else:
                return TradeResult(
                    success=False, message=f"Unknown order type: {config.order_type}"
                )

            # Submit order
            order: AlpacaOrder = self._trading_client.submit_order(order_request)

            return TradeResult(
                success=True,
                order_id=order.id,
                symbol=order.symbol,
                side=order.side.value,
                qty=float(order.qty),
                price=float(order.limit_price or order.filled_avg_price or 0),
                status=order.status.value,
                timestamp=order.submitted_at,
            )

        except Exception as e:
            return TradeResult(success=False, message=str(e))

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order.

        Args:
            order_id: Alpaca order ID

        Returns:
            True if cancelled successfully
        """
        try:
            self._trading_client.cancel_order_by_id(order_id)
            return True
        except Exception as e:
            print(f"Error cancelling order {order_id}: {e}")
            return False

    def cancel_all_orders(self) -> int:
        """Cancel all open orders.

        Returns:
            Number of orders cancelled
        """
        try:
            self._trading_client.cancel_orders()
            return True
        except Exception as e:
            print(f"Error cancelling all orders: {e}")
            return False

    def get_orders(self, status: str = "open", limit: int = 100) -> list[AlpacaOrder]:
        """Get orders by status.

        Args:
            status: Order status (open, closed, all)
            limit: Maximum number of orders

        Returns:
            List of Order objects
        """
        query_status = QueryOrderStatus(status.lower())
        return self._trading_client.get_orders(query_status, limit=limit)

    def get_order_by_id(self, order_id: str) -> AlpacaOrder | None:
        """Get a specific order by ID.

        Args:
            order_id: Alpaca order ID

        Returns:
            Order object or None
        """
        try:
            return self._trading_client.get_order_by_id(order_id)
        except Exception:
            return None

    def close_position(self, symbol: str) -> TradeResult:
        """Close all positions for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            TradeResult with close order details
        """
        try:
            order: AlpacaOrder = self._trading_client.close_position(symbol)
            return TradeResult(
                success=True,
                order_id=order.id,
                symbol=order.symbol,
                side=order.side.value,
                status=order.status.value,
                timestamp=order.submitted_at,
            )
        except Exception as e:
            return TradeResult(success=False, message=str(e))

    def close_all_positions(self) -> list[TradeResult]:
        """Close all open positions.

        Returns:
            List of TradeResult for each position closed
        """
        results = []
        positions = self.get_all_positions()

        for position in positions:
            result = self.close_position(position.symbol)
            results.append(result)

        return results

    async def connect_trading_stream(
        self,
        on_order_update: callable | None = None,
        on_trade_update: callable | None = None,
    ) -> None:
        """Connect to the trading stream for real-time updates.

        Args:
            on_order_update: Callback for order updates
            on_trade_update: Callback for trade updates
        """

        async def handle_order_update(order):
            if on_order_update:
                await on_order_update(order)

        async def handle_trade_update(trade):
            if on_trade_update:
                await on_trade_update(trade)

        if on_order_update:
            self._trading_stream.subscribe_orders(handle_order_update)

        if on_trade_update:
            self._trading_stream.subscribe_trades(handle_trade_update)

        await self._trading_stream.run()

    def get_portfolio_summary(self) -> dict[str, Any]:
        """Get a comprehensive portfolio summary.

        Returns:
            Dictionary with portfolio metrics and positions
        """
        account = self.get_account()
        positions = self.get_all_positions()

        position_details = []
        for pos in positions:
            position_details.append(
                {
                    "symbol": pos.symbol,
                    "qty": float(pos.qty),
                    "avg_entry_price": float(pos.avg_entry_price),
                    "current_price": float(pos.current_price),
                    "market_value": float(pos.market_value),
                    "cost_basis": float(pos.cost_basis),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_plpc": float(pos.unrealized_plpc),
                    "side": pos.side,
                }
            )

        return {
            "account": {
                "account_id": account.account_id,
                "cash": account.cash,
                "portfolio_value": account.portfolio_value,
                "buying_power": account.buying_power,
                "equity": account.equity,
                "day_change": (
                    (account.equity - account.last_equity) / account.last_equity * 100
                    if account.last_equity > 0
                    else 0
                ),
            },
            "positions": position_details,
            "position_count": len(positions),
            "trading_mode": self.trading_mode.value,
            "market_open": self.is_market_open(),
            "timestamp": datetime.now().isoformat(),
        }
