# AI Trading - Full Stack Application

A full-stack AI trading dashboard with a React frontend and FastAPI backend. The system discovers trained models from `backend/tradingBot/artifacts/models`, serves predictions and performance data, and runs a paper-trading engine backed by Alpaca.

## Features

### Backend (FastAPI)
- Model discovery and caching from `backend/tradingBot/artifacts/models`
- Prediction API with signal/confidence output
- Paper trading performance metrics
- Alpaca paper/live trading integration
- Trading engine control (start/stop/status/logs)
- P&L history endpoints for charts

### Frontend (React)
- AI Trading dashboard UI
- Live cards for all models with P&L and max drawdown
- Analysis view with model P&L and account P&L charts
- Manual trade flow (buy/sell) via the Trade tab
- Engine runtime shown in the header

## Project Structure

```
trading-bot/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── API.md
│   └── tradingBot/
│       ├── api.py
│       ├── live_trading.py
│       ├── engine_service.py
│       ├── alpaca_client.py
│       ├── artifacts/
│       │   ├── models/
│       │   └── model.keras
│       └── outputs/
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
└── README.md
```

## Quick Start

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend:
- `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

### 2) Frontend

```bash
cd frontend
npm install
npm start
```

Frontend:
- `http://localhost:3000`

## Environment Variables

### Backend
Set Alpaca credentials in `backend/.env` for paper/live trading:

```env
ALPACA_API_KEY=PKXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
ALPACA_SECRET_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
ALPACA_TRADING_MODE=paper
```

### Frontend
Create `frontend/.env` if your backend isn’t on `http://localhost:8000`:

```env
REACT_APP_API_URL=http://localhost:8000
```

## Notes

- The trading engine auto-discovers symbols from `backend/tradingBot/artifacts/models`.
- The analysis view shows both model P&L and account P&L charts.
- Manual trade uses `POST /api/live/order` (paper or live depending on Alpaca config).

## Docs

- Backend API: `backend/API.md`
- Deployment: `backend/DEPLOYMENT.md`
- Live trading: `backend/LIVE_TRADING.md`
- Training/paper trading workflows: `backend/tradingBot/README.md`
