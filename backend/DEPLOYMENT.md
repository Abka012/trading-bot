# Deployment Guide (Render)

This guide deploys the backend API to Render.

## Prerequisites
- Render account
- Git repo with this project

## Models

The engine loads models from `backend/tradingBot/artifacts/models`.

Options:
1. Commit `.keras` files to the repo (small models)
2. Download on startup (large models)

## Render Service Config

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2` |

## Environment Variables

Required for Alpaca:

```
ALPACA_API_KEY=PKXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
ALPACA_SECRET_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
ALPACA_TRADING_MODE=paper
```

Optional:
- `LOG_LEVEL`
- `ALLOWED_ORIGINS`

## Health Check

Endpoint: `GET /api/health`

## Frontend Deploy

Set `REACT_APP_API_URL` to your Render URL in your frontend host (Vercel/Netlify/Render static site).
