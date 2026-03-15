# Live Trading with Alpaca

This project integrates with Alpaca for paper/live trading. Always start with paper trading first.

## Setup

1. Create Alpaca account and API keys
2. Add `backend/.env`:

```env
ALPACA_API_KEY=PKXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
ALPACA_SECRET_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
ALPACA_TRADING_MODE=paper
```

## Engine Behavior

- Models are discovered from `backend/tradingBot/artifacts/models`.
- The engine auto-starts on backend startup and can be controlled via API.

## API Endpoints

- `GET /api/live/status`
- `GET /api/live/positions`
- `GET /api/live/account`
- `POST /api/live/order`
- `POST /api/live/order/close/{symbol}`
- `GET /api/live/pnl-history`

### Engine Control

- `GET /api/engine/status`
- `POST /api/engine/start`
- `POST /api/engine/stop`
- `GET /api/engine/logs`

## Manual Trading

The frontend Trade tab places orders via `POST /api/live/order`.

## Risk Warning

Live trading uses real funds. Validate models and signals in paper mode first.
