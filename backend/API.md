# Trading Bot API Documentation

Base URL:
- Development: `http://localhost:8000`

Authentication:
- None by default. Add your own for production.

## Core Endpoints

### Health
- `GET /`
- `GET /api/health`

### Models
- `GET /api/models`
- `GET /api/models/{symbol}`
- `DELETE /api/models/{symbol}/unload`
- `DELETE /api/models/cache/clear`

### Predictions & Market
- `POST /api/predict`
- `GET /api/market/{symbol}`

### P&L
- `GET /api/pnl/{symbol}`
- `GET /api/live/pnl-history`

### Live Trading (Alpaca)
- `GET /api/live/status`
- `GET /api/live/positions`
- `GET /api/live/account`
- `POST /api/live/order`
- `POST /api/live/order/close/{symbol}`

### Engine Control
- `GET /api/engine/status`
- `GET /api/engine/logs`
- `POST /api/engine/start`
- `POST /api/engine/stop`

## Example Requests

### Predict
```json
POST /api/predict
{
  "symbol": "AAPL"
}
```

### Place Order (Paper or Live)
```json
POST /api/live/order
{
  "symbol": "AAPL",
  "qty": 5,
  "side": "buy",
  "order_type": "market"
}
```

### P&L History
```json
GET /api/pnl/AAPL
```

## Notes

- Model discovery reads from `backend/tradingBot/artifacts/models`.
- Engine status includes `start_time` and configuration.
- `ALPACA_TRADING_MODE=paper` is recommended during development.
