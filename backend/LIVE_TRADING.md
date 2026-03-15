# Live Trading with Alpaca

Automated live trading integration with Alpaca Markets API. This module enables real-time automated trading using your trained ML models.

## ⚠️ Important Warning

**Live trading involves real financial risk.** Always start with paper trading and thoroughly test your strategies before using real money.

- **Paper Trading**: Simulated trading with fake money (recommended for testing)
- **Live Trading**: Real money trading (use with extreme caution)

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Automated Trading Engine](#automated-trading-engine)
- [Manual Trading](#manual-trading)
- [Risk Management](#risk-management)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## 🛠️ Prerequisites

### 1. Create Alpaca Account

1. Go to [Alpaca Markets](https://alpaca.markets/)
2. Sign up for an account
3. Complete identity verification

### 2. Get API Keys

**For Paper Trading:**
1. Go to [Paper Dashboard](https://app.alpaca.markets/paper-dashboard/overview)
2. Click on "API Keys" tab
3. Generate new keys or copy existing ones

**For Live Trading:**
1. Go to [Live Dashboard](https://app.alpaca.markets/dashboard/overview)
2. Enable live trading
3. Generate API keys

### 3. Install Dependencies

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 🔧 Setup

### 1. Create .env File

Copy the example file and fill in your credentials:

```bash
cd backend
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` with your credentials:

```env
# Alpaca API Credentials (from paper dashboard for testing)
ALPACA_API_KEY=PKXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
ALPACA_SECRET_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Trading Mode: 'paper' or 'live'
ALPACA_TRADING_MODE=paper

# Risk Management
MAX_POSITION_SIZE=0.05      # 5% of portfolio per position
MAX_POSITIONS=5             # Maximum concurrent positions
STOP_LOSS_PCT=0.02          # 2% stop loss
TAKE_PROFIT_PCT=0.04        # 4% take profit
SIGNAL_THRESHOLD=0.15       # Minimum signal to trade (15%)
```

### 3. Verify Connection

Test your Alpaca connection:

```bash
cd backend
source .venv/bin/activate
python -c "from tradingBot.alpaca_client import AlpacaClient; c = AlpacaClient(); print(c.get_account())"
```

---

## ⚙️ Configuration

### Trading Configuration Options

| Parameter | Description | Default | Recommended |
|-----------|-------------|---------|-------------|
| `ALPACA_TRADING_MODE` | Paper or live trading | `paper` | `paper` for testing |
| `MAX_POSITION_SIZE` | Max position as % of portfolio | `0.05` (5%) | `0.02-0.05` |
| `MAX_POSITIONS` | Maximum concurrent positions | `5` | `3-5` |
| `STOP_LOSS_PCT` | Stop loss percentage | `0.02` (2%) | `0.015-0.03` |
| `TAKE_PROFIT_PCT` | Take profit percentage | `0.04` (4%) | `0.03-0.06` |
| `SIGNAL_THRESHOLD` | Minimum signal strength | `0.15` (15%) | `0.1-0.2` |
| `REBALANCE_INTERVAL` | Rebalance frequency (minutes) | `5` | `5-15` |
| `MAX_TRADE_PER_SYMBOL` | Max trades per symbol per day | `10` | `5-10` |

### Model Configuration

The trading engine uses models from `tradingBot/artifacts/models/`. Each stock should have a corresponding model:

```
artifacts/models/
├── aapl_model.keras
├── msft_model.keras
├── googl_model.keras
└── ...
```

---

## 📡 API Endpoints

### Account & Status

#### Get Trading Status
```bash
GET /api/live/status
```

Response:
```json
{
  "connected": true,
  "trading_mode": "paper",
  "market_open": true,
  "account_id": "12345678...",
  "cash": 100000.00,
  "portfolio_value": 105000.00,
  "positions_count": 3,
  "timestamp": "2026-03-15T14:30:00"
}
```

#### Get Account Details
```bash
GET /api/live/account
```

#### Get Portfolio Summary
```bash
GET /api/live/portfolio
```

### Positions

#### Get All Positions
```bash
GET /api/live/positions
```

Response:
```json
[
  {
    "symbol": "AAPL",
    "qty": 10,
    "side": "long",
    "entry_price": 175.50,
    "current_price": 178.20,
    "market_value": 1782.00,
    "unrealized_pl": 27.00,
    "unrealized_plpc": 0.0154
  }
]
```

### Orders

#### Place Order
```bash
POST /api/live/order
Content-Type: application/json

{
  "symbol": "AAPL",
  "qty": 10,
  "side": "buy",
  "order_type": "market",
  "stop_loss": 170.00,
  "take_profit": 185.00
}
```

#### Get Orders
```bash
GET /api/live/orders?status=open
```

#### Cancel Order
```bash
DELETE /api/live/order/{order_id}
```

#### Close Position
```bash
POST /api/live/order/close/{symbol}
```

#### Close All Positions
```bash
POST /api/live/orders/close-all
```

---

## 🤖 Automated Trading Engine

### Starting the Engine

**Paper Trading (Recommended):**
```bash
cd backend
source .venv/bin/activate
python tradingBot/live_trading.py
```

### Custom Configuration

Create a custom trading script:

```python
from tradingBot.live_trading import LiveTradingEngine, TradingConfig

# Configure trading parameters
config = TradingConfig(
    symbols=["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
    max_position_size=0.05,      # 5% per position
    max_positions=5,              # Max 5 concurrent positions
    stop_loss_pct=0.02,           # 2% stop loss
    take_profit_pct=0.04,         # 4% take profit
    signal_threshold=0.15,        # 15% signal threshold
    rebalance_interval=5,         # Rebalance every 5 minutes
    paper_trading=True,           # Paper trading mode
)

# Start trading engine
engine = LiveTradingEngine(config)
engine.start()
```

### How It Works

1. **Initialization**: Loads models and connects to Alpaca
2. **Market Check**: Verifies market is open
3. **Prediction**: Generates signals for each symbol
4. **Position Sizing**: Calculates position size based on signal strength
5. **Order Execution**: Places orders via Alpaca API
6. **Risk Management**: Monitors stop-loss and take-profit levels
7. **Rebalancing**: Periodically reviews and adjusts positions

### Stopping the Engine

Press `Ctrl+C` to gracefully stop the engine. It will:
- Save all trade logs
- Optionally close positions (configurable)
- Write final equity snapshot

---

## 📊 Manual Trading

### Using the API

**Place a Market Order:**
```bash
curl -X POST http://localhost:8000/api/live/order \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "qty": 10,
    "side": "buy",
    "order_type": "market"
  }'
```

**Place a Limit Order:**
```bash
curl -X POST http://localhost:8000/api/live/order \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "qty": 10,
    "side": "buy",
    "order_type": "limit",
    "limit_price": 175.00
  }'
```

**Close a Position:**
```bash
curl -X POST http://localhost:8000/api/live/order/close/AAPL
```

---

## 🛡️ Risk Management

### Position Sizing

The engine uses a signal-based position sizing approach:

```python
# Position size scales with signal strength
position_fraction = abs(signal) * max_position_size
# Stronger signal = larger position (up to max)
```

### Stop Loss & Take Profit

Every order automatically includes:
- **Stop Loss**: Limits downside risk
- **Take Profit**: Locks in gains

```env
STOP_LOSS_PCT=0.02      # Exit if down 2%
TAKE_PROFIT_PCT=0.04    # Exit if up 4%
```

### Daily Trade Limits

Prevents overtrading:
```env
MAX_TRADE_PER_SYMBOL=10  # Max 10 trades per symbol per day
```

### Market Hours

The engine only trades during market hours (9:30 AM - 4:00 PM ET).

---

## 📈 Monitoring

### Log Files

Trading logs are saved to:
```
outputs/live_trading/logs/trading_YYYYMMDD_HHMMSS.log
```

### Trade History

All trades are logged to:
```
outputs/live_trading/trades/trades_YYYYMMDD.csv
```

Columns:
- `timestamp`: Trade time
- `symbol`: Stock symbol
- `side`: Buy/sell
- `qty`: Number of shares
- `price`: Execution price
- `pnl`: Profit/loss
- `reason`: Why trade was executed

### Equity Curve

Equity snapshots saved to:
```
outputs/live_trading/equity/equity_YYYYMMDD.csv
```

### Dashboard

The frontend dashboard shows:
- Real-time positions
- Unrealized P&L
- Account equity
- Today's trades

---

## 🔍 Troubleshooting

### Connection Issues

**Error: "Alpaca not configured"**
```
Solution: Check your .env file has valid API keys
```

**Error: "Invalid API key"**
```
Solution: Verify keys from Alpaca dashboard are correct
Check you're using paper keys for paper trading
```

### Trading Issues

**Error: "Market is currently closed"**
```
Solution: Trading only works during market hours (9:30 AM - 4:00 PM ET)
Check: GET /api/live/status to see market status
```

**Error: "Insufficient buying power"**
```
Solution: Reduce MAX_POSITION_SIZE in .env
Or increase account capital
```

**Orders not executing:**
```
1. Check market is open
2. Verify you have buying power
3. Check symbol is tradeable
4. Review order parameters
```

### Model Issues

**Error: "Model not found for symbol"**
```
Solution: Train model first:
python tradingBot/train.py --csv data.csv --save-model artifacts/models/aapl_model.keras
```

**Poor predictions:**
```
1. Retrain model with more data
2. Adjust SIGNAL_THRESHOLD
3. Review model performance metrics
```

---

## 📝 Best Practices

### Before Live Trading

1. ✅ Test extensively with paper trading
2. ✅ Backtest your models thoroughly
3. ✅ Start with small position sizes
4. ✅ Monitor trades closely
5. ✅ Set conservative stop losses

### During Trading

1. 📊 Monitor the dashboard regularly
2. 📈 Review trade logs daily
3. ⚠️ Watch for unusual activity
4. 💰 Check account balance frequently
5. 🛑 Be ready to stop trading if needed

### Risk Limits

Never risk more than you can afford to lose:
- Start with 1-2% position sizes
- Use tight stop losses (1.5-2%)
- Limit concurrent positions (3-5)
- Set daily loss limits

---

## 🚨 Emergency Procedures

### Stop All Trading

```bash
# Stop the trading engine
Ctrl+C in terminal

# Close all positions via API
curl -X POST http://localhost:8000/api/live/orders/close-all
```

### Kill Switch

Create a `STOP` file to trigger emergency shutdown:
```bash
touch outputs/live_trading/STOP
```

---

## 📚 Additional Resources

- [Alpaca API Documentation](https://docs.alpaca.markets/)
- [Alpaca Paper Trading](https://alpaca.markets/docs/paper-trading/)
- [Order Types](https://alpaca.markets/docs/trading-on-alpaca/orders/)

---

## ⚠️ Disclaimer

**This software is for educational purposes only.**

- Trading involves substantial risk of loss
- Past performance does not guarantee future results
- Do not trade with money you cannot afford to lose
- Test thoroughly with paper trading before using real money
- The authors are not responsible for any financial losses

**Always start with paper trading!**
