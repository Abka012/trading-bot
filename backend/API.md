# Trading Bot API Documentation

Comprehensive API documentation for the Trading Bot backend.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://your-app.onrender.com`

## Authentication

Currently, the API does not require authentication. For production use, consider adding API key or JWT authentication.

---

## Endpoints

### Health & Status

#### `GET /`

Root endpoint with welcome message.

**Response:**
```json
{
  "message": "Welcome to Trading Bot Dashboard API",
  "version": "2.0.0",
  "status": "running",
  "docs": "/docs"
}
```

#### `GET /api/health`

Health check endpoint for monitoring and load balancers.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2026-03-15T12:00:00.000Z"
}
```

#### `GET /api/dashboard`

Get comprehensive dashboard data including models, predictions, paper trading results, and market data.

**Response:**
```json
{
  "models": [
    {"name": "aapl", "symbol": "AAPL", "loaded": true},
    {"name": "msft", "symbol": "MSFT", "loaded": true}
  ],
  "predictions": [
    {
      "symbol": "AAPL",
      "prediction": 0.0234,
      "signal": 0.116,
      "direction": "UP",
      "confidence": 75.5,
      "current_price": 175.50
    }
  ],
  "paper_trading": [
    {
      "symbol": "AAPL",
      "total_return": 12.5,
      "total_pnl": 1250.00,
      "win_rate": 65.0,
      "profit_factor": 2.1,
      "sharpe_ratio": 1.5,
      "max_drawdown": -8.5,
      "total_trades": 45,
      "start_date": "2026-03-01T00:00:00",
      "end_date": "2026-03-15T00:00:00"
    }
  ],
  "market_data": [
    {"symbol": "AAPL", "price": 175.50, "change": 2.5}
  ],
  "summary": {
    "total_models": 32,
    "total_predictions": 10,
    "avg_confidence": 72.3
  }
}
```

---

### Models

#### `GET /api/models`

List all available models in the artifacts/models directory.

**Response:**
```json
[
  {
    "name": "aapl",
    "path": "/app/tradingBot/artifacts/models/aapl_model.keras",
    "loaded": true,
    "symbol": "AAPL",
    "loaded_at": "2026-03-15T10:00:00.000Z"
  },
  {
    "name": "msft",
    "path": "/app/tradingBot/artifacts/models/msft_model.keras",
    "loaded": false,
    "symbol": "MSFT",
    "loaded_at": null
  }
]
```

#### `GET /api/models/{symbol}`

Get information about a specific model.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| symbol | path | Stock ticker symbol (e.g., AAPL, MSFT) |

**Response:**
```json
{
  "name": "aapl",
  "path": "/app/tradingBot/artifacts/models/aapl_model.keras",
  "loaded": true,
  "symbol": "AAPL",
  "loaded_at": "2026-03-15T10:00:00.000Z"
}
```

**Errors:**
- `404 Not Found` - Model not found for symbol

#### `DELETE /api/models/{symbol}/unload`

Unload a specific model from the cache.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| symbol | path | Stock ticker symbol |

**Response:**
```json
{
  "status": "success",
  "message": "Model for AAPL unloaded"
}
```

#### `DELETE /api/models/cache/clear`

Clear all models from the cache.

**Response:**
```json
{
  "status": "success",
  "message": "All models unloaded from cache"
}
```

---

### Predictions

#### `POST /api/predict`

Make a prediction for a given stock symbol.

**Request Body:**
```json
{
  "symbol": "AAPL",
  "model_name": "aapl_model",
  "use_custom_model": false
}
```

**Response:**
```json
{
  "symbol": "AAPL",
  "model_name": "AAPL",
  "prediction": 0.0234,
  "signal": 0.116,
  "direction": "UP",
  "confidence": 75.5,
  "timestamp": "2026-03-15T12:00:00.000Z",
  "current_price": 175.50
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| symbol | string | Stock ticker symbol |
| model_name | string | Name of the model used |
| prediction | float | Raw model prediction (expected return) |
| signal | float | Trading signal (-1 to 1, from tanh activation) |
| direction | string | Predicted direction: UP, DOWN, or NEUTRAL |
| confidence | float | Confidence level (0-100%) |
| timestamp | datetime | When the prediction was made |
| current_price | float | Current market price |

**Direction Logic:**
- `UP`: signal > 0.1
- `DOWN`: signal < -0.1
- `NEUTRAL`: -0.1 <= signal <= 0.1

**Errors:**
- `404 Not Found` - Model not found for symbol
- `500 Internal Server Error` - Prediction error

---

### Market Data

#### `GET /api/market/{symbol}`

Get current market data for a stock symbol.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| symbol | path | Stock ticker symbol |

**Response:**
```json
{
  "symbol": "AAPL",
  "price": 175.50,
  "change": 2.5,
  "volume": 52000000,
  "high": 176.20,
  "low": 174.80,
  "open": 175.00,
  "previous_close": 171.22,
  "timestamp": "2026-03-15T12:00:00.000Z"
}
```

**Errors:**
- `404 Not Found` - No data available for symbol
- `500 Internal Server Error` - Market data error

---

### Paper Trading

#### `GET /api/paper-trading`

Get paper trading results for all symbols.

**Response:**
```json
[
  {
    "symbol": "AAPL",
    "total_return": 12.5,
    "total_pnl": 1250.00,
    "win_rate": 65.0,
    "profit_factor": 2.1,
    "sharpe_ratio": 1.5,
    "max_drawdown": -8.5,
    "total_trades": 45,
    "start_date": "2026-03-01T00:00:00",
    "end_date": "2026-03-15T00:00:00",
    "model_name": "aapl"
  },
  {
    "symbol": "MSFT",
    "total_return": 8.3,
    "total_pnl": 830.00,
    "win_rate": 58.0,
    "profit_factor": 1.8,
    "sharpe_ratio": 1.2,
    "max_drawdown": -12.0,
    "total_trades": 38,
    "start_date": "2026-03-01T00:00:00",
    "end_date": "2026-03-15T00:00:00",
    "model_name": "msft"
  }
]
```

#### `GET /api/paper-trading/{symbol}`

Get paper trading results for a specific symbol.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| symbol | path | Stock ticker symbol |

**Response:**
```json
{
  "symbol": "AAPL",
  "total_return": 12.5,
  "total_pnl": 1250.00,
  "win_rate": 65.0,
  "profit_factor": 2.1,
  "sharpe_ratio": 1.5,
  "max_drawdown": -8.5,
  "total_trades": 45,
  "start_date": "2026-03-01T00:00:00",
  "end_date": "2026-03-15T00:00:00"
}
```

**Metrics Explained:**
| Metric | Description | Calculation |
|--------|-------------|-------------|
| total_return | Total return percentage | (Final Equity - Initial) / Initial × 100 |
| total_pnl | Total profit and loss in USD | Sum of all trade P&L |
| win_rate | Percentage of winning trades | Winning Trades / Total Trades × 100 |
| profit_factor | Gross profit / Gross loss | Sum(Profits) / Sum(Losses) |
| sharpe_ratio | Risk-adjusted return | (Return - Risk Free) / Std Dev × √252 |
| max_drawdown | Maximum peak-to-trough decline | Min((Current - Peak) / Peak) × 100 |
| total_trades | Number of trades executed | Count of trade records |

**Errors:**
- Returns `{"error": "..."}` if no results available

---

## Trading API Routes

The following routes are mounted under `/api/trading/`:

- `GET /api/trading/` - Trading API root
- `GET /api/trading/models` - List models (same as `/api/models`)
- `POST /api/trading/predict` - Make prediction (same as `/api/predict`)
- `GET /api/trading/market/{symbol}` - Market data (same as `/api/market/{symbol}`)
- `GET /api/trading/paper-trading/{symbol}/results` - Paper trading results

---

## Error Handling

All endpoints return errors in the following format:

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |

---

## Rate Limiting

Currently, there is no rate limiting. For production use, consider implementing:
- Request rate limiting per IP
- API key authentication
- Request quotas

---

## CORS

The API is configured to accept requests from:
- `http://localhost:3000`
- `http://localhost:5173`
- `https://*.render.com`
- `https://*.onrender.com`

For production, update the `allow_origins` list in `main.py`.

---

## Interactive Documentation

When the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

These provide interactive API testing and detailed documentation.

---

## Example Usage

### JavaScript (Frontend)

```javascript
// Get all models
const models = await fetch('http://localhost:8000/api/models')
  .then(res => res.json());

// Make a prediction
const prediction = await fetch('http://localhost:8000/api/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ symbol: 'AAPL' })
}).then(res => res.json());

// Get paper trading results
const results = await fetch('http://localhost:8000/api/paper-trading')
  .then(res => res.json());
```

### Python

```python
import requests

# Get all models
models = requests.get('http://localhost:8000/api/models').json()

# Make a prediction
prediction = requests.post(
    'http://localhost:8000/api/predict',
    json={'symbol': 'AAPL'}
).json()

# Get paper trading results
results = requests.get('http://localhost:8000/api/paper-trading').json()
```

### cURL

```bash
# Get models
curl http://localhost:8000/api/models

# Make prediction
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'

# Get market data
curl http://localhost:8000/api/market/AAPL

# Get paper trading results
curl http://localhost:8000/api/paper-trading
```
