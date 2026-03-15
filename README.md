# Trading Bot - Full Stack Application

A modern, full-stack trading bot application with a React frontend and FastAPI backend. The system uses deep learning models to predict stock price movements and provides real-time predictions, paper trading results, and market data through an interactive dashboard.

## 🚀 Features

### Backend (FastAPI)
- **Model API**: RESTful API for loading and managing multiple trained TensorFlow models
- **Real-time Predictions**: Generate trading signals for 30+ US stocks
- **Paper Trading Results**: Retrieve historical paper trading performance metrics
- **Market Data**: Fetch current market data via yfinance
- **Model Caching**: Efficient in-memory model management with LRU eviction
- **CORS Enabled**: Ready for frontend integration

### Frontend (React)
- **Live Dashboard**: Real-time display of model predictions and performance
- **Multi-Model Support**: View predictions from all trained models simultaneously
- **Paper Trading Metrics**: Display win rate, profit factor, Sharpe ratio, and more
- **Auto-Refresh**: Data updates every 5 seconds
- **Responsive Design**: Works on desktop and mobile devices
- **Error Handling**: Graceful handling of backend connection issues

### Models
- **30 Pre-trained Models**: Models for popular US stocks (AAPL, MSFT, GOOGL, AMZN, etc.)
- **Bidirectional LSTM Architecture**: Deep learning model for sequential pattern recognition
- **Conservative Trading**: Risk-managed position sizing and stop-loss/take-profit

---

## 📋 Table of Contents

- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [API Documentation](#api-documentation)
- [Docker Deployment](#docker-deployment)
- [Render Deployment](#render-deployment)
- [Training Models](#training-models)
- [Running Paper Trading](#running-paper-trading)
- [Troubleshooting](#troubleshooting)

---

## 📁 Project Structure

```
trading-bot/
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Docker configuration for deployment
│   ├── pyproject.toml          # Python project configuration
│   └── tradingBot/
│       ├── api.py              # Trading bot API with model management
│       ├── model.py            # Model architecture definition
│       ├── paper_trading.py    # Paper trading engine
│       ├── train.py            # Model training pipeline
│       ├── evaluate.py         # Model evaluation
│       ├── extract_stock.py    # Stock data extraction utility
│       ├── artifacts/
│       │   ├── models/         # Trained model files (.keras)
│       │   └── model.keras     # Default trained model
│       └── outputs/
│           ├── trades/         # Paper trading trade history
│           ├── equity/         # Equity curve data
│           ├── logs/           # Trading logs
│           └── reports/        # Performance reports
├── frontend/
│   ├── src/
│   │   ├── App.js              # Main React component
│   │   ├── App.css             # Dashboard styles
│   │   └── index.js            # React entry point
│   ├── package.json            # Node.js dependencies
│   └── public/                 # Static assets
├── README.md                   # This file
└── .gitignore
```

---

## 🛠️ Prerequisites

### Backend
- Python 3.10 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Frontend
- Node.js 18+ and npm
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Optional (for deployment)
- Docker
- Render account (for cloud deployment)

---

## ⚡ Quick Start

### 1. Start the Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`
API Documentation at: `http://localhost:8000/docs`

### 2. Start the Frontend

Open a new terminal:

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start the React development server
npm start
```

Frontend will be available at: `http://localhost:3000`

---

## 🔧 Backend Setup

### Installation

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Running the API Server

**Development mode (with auto-reload):**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port (used by Render) | `8000` |
| `REACT_APP_API_URL` | Backend API URL for frontend | `http://localhost:8000` |

---

## 🎨 Frontend Setup

### Installation

```bash
cd frontend
npm install
```

### Running the Development Server

```bash
npm start
```

### Building for Production

```bash
npm run build
```

The production build will be created in the `build/` directory.

### Environment Variables

Create a `.env` file in the `frontend/` directory:

```env
REACT_APP_API_URL=http://localhost:8000
```

For production deployment, update this to your backend URL.

---

## 📡 API Documentation

The backend provides a comprehensive REST API. Interactive documentation is available at `http://localhost:8000/docs` when the server is running.

### Key Endpoints

#### Health & Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root endpoint with welcome message |
| `GET` | `/api/health` | Health check endpoint |
| `GET` | `/api/dashboard` | Comprehensive dashboard data |

#### Models
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/models` | List all available models |
| `GET` | `/api/models/{symbol}` | Get specific model info |
| `DELETE` | `/api/models/{symbol}/unload` | Unload a model from cache |
| `DELETE` | `/api/models/cache/clear` | Clear all cached models |

#### Predictions
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/predict` | Make a prediction for a symbol |
| `GET` | `/api/market/{symbol}` | Get current market data |

#### Paper Trading
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/paper-trading` | Get all paper trading results |
| `GET` | `/api/paper-trading/{symbol}` | Get results for a specific symbol |

### Example API Calls

**Get all available models:**
```bash
curl http://localhost:8000/api/models
```

**Make a prediction for AAPL:**
```bash
curl -X POST "http://localhost:8000/api/predict" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'
```

**Get paper trading results:**
```bash
curl http://localhost:8000/api/paper-trading
```

---

## 🐳 Docker Deployment

### Build the Docker Image

```bash
cd backend
docker build -t trading-bot-backend .
```

### Run the Docker Container

```bash
docker run -p 8000:8000 \
  -e PORT=8000 \
  -v $(pwd)/tradingBot/artifacts:/app/tradingBot/artifacts \
  trading-bot-backend
```

### Docker Compose (Optional)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
    volumes:
      - ./backend/tradingBot/artifacts:/app/tradingBot/artifacts

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    depends_on:
      - backend
```

Run with:
```bash
docker-compose up
```

---

## ☁️ Render Deployment

The backend is configured for deployment to Render. The Dockerfile includes:
- Health checks for Render's monitoring
- PORT environment variable support
- Non-root user for security
- Optimized layer caching

### Deploy to Render

1. **Push your code to GitHub**

2. **Create a new Web Service on Render:**
   - Connect your GitHub repository
   - Set Root Directory to `backend`
   - Set Build Command: `pip install -r requirements.txt`
   - Set Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2`

3. **Environment Variables:**
   - `PORT`: `8000` (Render sets this automatically)

4. **Health Check Path:** `/api/health`

### Frontend Deployment

For the frontend, you can deploy to:
- **Vercel**: Connect GitHub repo, set build command to `npm run build`
- **Netlify**: Connect GitHub repo, set build command to `npm run build`

Update `REACT_APP_API_URL` in the frontend to point to your Render backend URL.

---

## 🎓 Training Models

### Train a Model for a Specific Stock

```bash
cd backend
source .venv/bin/activate

# Extract stock data
python tradingBot/extract_stock.py --symbol AAPL --output aapl_data.csv

# Train the model
python tradingBot/train.py \
  --csv aapl_data.csv \
  --window 60 \
  --epochs 30 \
  --objective profit \
  --save-model tradingBot/artifacts/models/aapl_model.keras
```

### Train Models for Multiple Stocks

Use the provided script to train models for all popular stocks:

```bash
cd backend/tradingBot
./trade_all_popular_stocks.sh
```

This will:
1. Extract data for 20+ popular US stocks
2. Train a model for each stock
3. Run paper trading simulations
4. Generate performance reports

### Available Training Options

| Option | Description | Default |
|--------|-------------|---------|
| `--csv` | Path to input CSV file | Required |
| `--window` | Lookback window size | 60 |
| `--epochs` | Number of training epochs | 30 |
| `--objective` | Training objective (mse/profit) | profit |
| `--save-model` | Path to save the model | artifacts/model.keras |

See `tradingBot/README.md` for detailed training documentation.

---

## 📰 Running Paper Trading

### Historical Replay Mode

```bash
cd backend
source .venv/bin/activate

python tradingBot/paper_trading.py \
  --model tradingBot/artifacts/models/aapl_model.keras \
  --symbol AAPL \
  --csv aapl_data.csv \
  --duration 60 \
  --interval 1
```

### Live Trading Mode

```bash
python tradingBot/paper_trading.py \
  --model tradingBot/artifacts/models/aapl_model.keras \
  --symbol AAPL \
  --live \
  --duration 120 \
  --interval 60
```

### Paper Trading Outputs

Paper trading generates:
- `outputs/trades/paper_trading_trades_*.csv` - Trade history
- `outputs/equity/paper_trading_equity_*.csv` - Equity curve data

These files are automatically loaded by the frontend dashboard.

---

## 🔍 Troubleshooting

### Backend Issues

**Error: Module not found: tradingBot**
```bash
# Make sure you're running from the backend directory
cd backend
uvicorn main:app --reload
```

**Error: Model not found for symbol**
```bash
# Check if models exist in the artifacts/models directory
ls tradingBot/artifacts/models/

# Train models if they don't exist
python tradingBot/trade_all_popular_stocks.sh
```

**Error: Cannot connect to yfinance**
```bash
# yfinance may have rate limits. Use CSV files for reliable data.
python tradingBot/extract_stock.py --symbol AAPL --output aapl_data.csv
```

### Frontend Issues

**Error: Failed to connect to backend**
```bash
# 1. Make sure backend is running
curl http://localhost:8000/api/health

# 2. Check CORS settings in main.py
# 3. Verify REACT_APP_API_URL environment variable
```

**Error: npm start fails**
```bash
# Clear node modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

### Docker Issues

**Error: Port already in use**
```bash
# Use a different port
docker run -p 8001:8000 trading-bot-backend
```

**Error: Models not found in container**
```bash
# Mount the artifacts directory
docker run -v $(pwd)/tradingBot/artifacts:/app/tradingBot/artifacts trading-bot-backend
```

---

## 📊 Supported Stocks

The system includes pre-trained models for:
- **Technology**: AAPL, MSFT, GOOGL, AMZN, NVDA, META, INTC, CSCO, ADBE, ORCL
- **Finance**: JPM, BAC, WFC, C, GS, MA, V
- **Healthcare**: JNJ, UNH, PFE
- **Consumer**: WMT, HD, PG, KO, PEP, MCD, NKE, TSLA, DIS
- **Industrial**: GE, CAT, BA
- **Energy**: XOM, CVX
- **Real Estate**: AMT, PLD

---

## 📝 License

This project is for educational and research purposes only.

**Disclaimer**: Trading involves substantial risk of loss. This software is not financial advice. Do not use for actual trading without thorough testing and understanding of the risks involved. Past performance does not guarantee future results.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to:
- Open issues for bugs or feature requests
- Submit pull requests with improvements
- Share your trained models and results

---

## 📧 Support

For questions or issues:
1. Check the [tradingBot/README.md](backend/tradingBot/README.md) for model-specific documentation
2. Review the API documentation at `http://localhost:8000/docs`
3. Open an issue on the project repository
