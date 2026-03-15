# Trading Bot Backend

FastAPI backend for the AlphaMindStock dashboard. Provides model discovery, predictions, paper trading metrics, Alpaca live/paper trading, and engine control.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Environment

Create `backend/.env` for Alpaca credentials:

```env
ALPACA_API_KEY=PKXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
ALPACA_SECRET_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
ALPACA_TRADING_MODE=paper
```

## Key Endpoints

- `GET /api/models`
- `POST /api/predict`
- `GET /api/pnl/{symbol}`
- `GET /api/live/pnl-history`
- `GET /api/live/positions`
- `POST /api/live/order`
- `GET /api/engine/status`
- `POST /api/engine/start`
- `POST /api/engine/stop`

## Notes

- Models are discovered from `backend/tradingBot/artifacts/models`.
- The engine auto-starts on app startup using those models.

See `backend/API.md` for detailed API documentation.
