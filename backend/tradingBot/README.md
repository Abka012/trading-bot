# US Stock Market Trading Bot

A deep learning-based trading system for US stock market trading using TensorFlow, pandas, and yfinance. This project implements a sophisticated neural network architecture for predicting stock price movements and includes a complete paper trading system for live simulation.

## 🚀 Features

- **Advanced Model Architecture**: Bidirectional LSTM + Dense layers for pattern recognition
- **Real-time Data Integration**: Fetches live US stock data via yfinance
- **Paper Trading System**: Simulated trading with realistic position management
- **Comprehensive Evaluation**: Multiple trading strategies with detailed performance metrics
- **Risk Management**: Stop-loss, take-profit, and position sizing controls
- **Multi-Stock Support**: Train on hundreds of US stocks simultaneously

---

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Data Format](#data-format)
- [Training](#training)
- [Evaluation](#evaluation)
- [Paper Trading](#paper-trading)
- [Model Architecture](#model-architecture)
- [Features](#features-1)
- [Trading Strategies](#trading-strategies)
- [Performance Metrics](#performance-metrics)
- [Project Structure](#project-structure)

---

## 🛠️ Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Setup

1. **Clone or navigate to the project directory**:
   ```bash
   cd trading-bot-demo-2
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   ```

3. **Activate the virtual environment**:
   ```bash
   # Linux/macOS
   source .venv/bin/activate
   
   # Windows
   .venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Dependencies

The project requires the following main packages:
- `tensorflow>=2.15.0` - Deep learning framework
- `pandas>=2.0.0` - Data manipulation
- `numpy>=1.24.0` - Numerical computing
- `yfinance>=0.2.50` - Yahoo Finance data fetching
- `matplotlib>=3.7.0` - Visualization
- `scikit-learn>=1.2.0` - Machine learning utilities

---

## ⚡ Quick Start

### 🚀 ONE COMMAND TO TRADE ALL POPULAR STOCKS

```bash
./trade_all_popular_stocks.sh
```

This single command will automatically:
- Extract data for 20 popular US stocks (AAPL, MSFT, GOOGL, AMZN, etc.)
- Train custom models for each stock
- Run paper trading for all stocks
- Save outputs to organized folders
- Generate comprehensive summary report

**Time:** 30-60 minutes | **See:** [TRADE_ALL.md](TRADE_ALL.md) for details

---

### Manual Step-by-Step

**Recommended Training (Simplified Model + Conservative Parameters)**:

```bash
# Train with US stock market data (default)
python train.py --csv us_stock_market.csv --window 60 --epochs 50 \
  --objective profit --pretrain-epochs 15 \
  --cs-mode zscore \
  --ret-clip 0.15 \
  --tanh-alpha 5.0 \
  --risk-aversion 0.25 \
  --drawdown-penalty 0.5 \
  --pos-l2 0.02 \
  --cost-bps 2.0 \
  --tune-strategy \
  --save-model artifacts/model.keras
```

**Key Improvements in v2**:
- ✅ **Fixed drawdown penalty bug** (was rewarding drawdowns)
- ✅ **Simplified model architecture** (removed over-engineered attention/Conv1D)
- ✅ **Reduced feature set** (15 features instead of 33 to prevent overfitting)
- ✅ **More conservative position sizing** (tanh-alpha=5.0 instead of 10.0)
- ✅ **Higher risk aversion** (0.25 instead of 0.1)
- ✅ **Realistic transaction costs** (2 bps instead of 1 bps)

### 2. Evaluate the Model

```bash
# Evaluate with detailed metrics
python evaluate.py --model artifacts/model.keras \
  --csv us_stock_market.csv --out evaluation.png --verbose
```

### 3. Run Paper Trading

```bash
# Historical replay mode (fast)
python paper_trading.py --model artifacts/model.keras \
  --symbol AAPL --duration 60 --interval 1

# Live trading mode (real-time)
python paper_trading.py --model artifacts/model.keras \
  --symbol AAPL --live --duration 120 --interval 60
```

---

## 📊 Data Format

### us_stock_market.csv Format

The project expects CSV data in the following format:

**With Header**:
```csv
date,symbol,open,high,low,close,volume
2016-01-05 00:00:00,WLTW,123.43,126.25,122.31,125.84,2163600.0
2016-01-06 00:00:00,WLTW,125.24,125.54,119.94,119.98,2386400.0
```

**Columns**:
- `date`: Timestamp (YYYY-MM-DD HH:MM:SS format)
- `symbol`: Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)
- `open`: Opening price
- `high`: Highest price during the period
- `low`: Lowest price during the period
- `close`: Closing price
- `volume`: Trading volume

The system automatically detects the format and adjusts accordingly.

### Using yfinance Data

The paper trading system fetches data directly from Yahoo Finance:
- **Symbol**: Any valid US stock ticker (e.g., AAPL, MSFT, TSLA)
- **Interval**: Daily data (default)
- **Period**: Last 5 days (for feature calculation)

---

## 🎓 Training

### Basic Training (MSE Objective)

```bash
python train.py --csv us_stock_market.csv \
  --window 60 \
  --epochs 20 \
  --batch-size 256 \
  --save-model artifacts/model_mse.keras
```

### Advanced Training (Profit Objective)

Recommended for better trading performance:

```bash
python train.py --csv us_stock_market.csv \
  --window 60 \
  --epochs 30 \
  --pretrain-epochs 10 \
  --objective profit \
  --cs-mode zscore \
  --y-demean \
  --ret-clip 0.2 \
  --use-sortino \
  --drawdown-penalty 0.5 \
  --vol-target 0.1 \
  --tanh-alpha 10 \
  --risk-aversion 0.2 \
  --pos-l2 0.01 \
  --save-model artifacts/model_profit.keras
```

### Training Parameters Explained

| Parameter | Description | Recommended Value |
|-----------|-------------|-------------------|
| `--window` | Lookback window size | 60 (for 1-hour data) |
| `--epochs` | Total training epochs | 30-50 |
| `--pretrain-epochs` | MSE pretraining epochs | 10-15 |
| `--objective` | Training objective | `profit` |
| `--cs-mode` | Cross-sectional normalization | `zscore` |
| `--ret-clip` | Return clipping threshold | 0.2 |
| `--use-sortino` | Use downside deviation | Enable |
| `--drawdown-penalty` | Drawdown penalty | 0.3-0.7 |
| `--vol-target` | Target volatility | 0.1 |
| `--risk-aversion` | Risk penalty | 0.15-0.3 |

### Training Output

Training produces:
- Model weights file (`.keras`)
- Console output with metrics:
  - MSE/MAE on test set
  - Directional accuracy
  - Backtest results (CAGR, Sharpe, Max Drawdown)

---

## 📈 Evaluation

### Basic Evaluation

```bash
python evaluate.py --model artifacts/model.keras \
  --csv us_stock_market.csv \
  --out evaluation.png
```

### Detailed Evaluation

```bash
python evaluate.py --model artifacts/model.keras \
  --csv us_stock_market.csv \
  --out evaluation.png \
  --verbose
```

### Evaluation Metrics

The evaluation script provides:

1. **Prediction Metrics**:
   - Mean Squared Error (MSE)
   - Mean Absolute Error (MAE)
   - Directional Accuracy

2. **Strategy Performance** (with `--verbose`):
   - Total Return
   - Annualized Return
   - Sharpe Ratio
   - Maximum Drawdown
   - Win Rate
   - Profit Factor

### Output Files

- `evaluation.png` - Equity curve visualization
- Console output with detailed metrics table

---

## 📰 Paper Trading

The paper trading system simulates real-time trading with:
- Live data fetching via yfinance (if available)
- CSV file support for offline trading (recommended)
- Position management (long/short)
- Stop-loss and take-profit orders
- Transaction cost modeling
- Performance tracking

### ⚡ Quick Start (Recommended)

**Step 1: Extract stock data for paper trading**
```bash
python extract_stock.py --symbol AAPL --output aapl_data.csv
```

**Step 2: Run paper trading with CSV**
```bash
python paper_trading.py \
  --model artifacts/model.keras \
  --symbol AAPL \
  --csv aapl_data.csv \
  --duration 60 \
  --interval 1
```

### Historical Replay Mode

Fast-forward test using historical data:

```bash
python paper_trading.py \
  --model artifacts/model.keras \
  --symbol AAPL \
  --capital 10000 \
  --duration 60 \
  --interval 1 \
  --position-size 0.1 \
  --max-positions 5 \
  --stop-loss 0.02 \
  --take-profit 0.04
```

### Live Trading Mode

Real-time simulation with live data (requires working yfinance):

```bash
python paper_trading.py \
  --model artifacts/model.keras \
  --symbol AAPL \
  --capital 10000 \
  --live \
  --duration 120 \
  --interval 60
```

**Note:** yfinance may not work reliably. Use CSV files for consistent results.

### Paper Trading Parameters

| Parameter | Description | Default (v2) |
|-----------|-------------|--------------|
| `--model` | Path to trained model | `artifacts/model.keras` |
| `--symbol` | Stock ticker symbol | `AAPL` |
| `--capital` | Initial capital (USD) | 10000 |
| `--position-size` | Capital fraction per trade | 0.05 (5%) ⬇️ |
| `--max-positions` | Max concurrent positions | 3 ⬇️ |
| `--stop-loss` | Stop loss percentage | 0.015 (1.5%) ⬇️ |
| `--take-profit` | Take profit percentage | 0.03 (3%) ⬇️ |
| `--cost-bps` | Transaction cost (bps) | 2.0 ⬆️ |
| `--duration` | Trading duration (minutes) | 60 |
| `--interval` | Cycle interval (seconds) | 60 |
| `--live` | Use live data | False |

**Note**: v2 uses more conservative defaults to prevent overtrading and reduce risk.

### Output Files

Paper trading generates:
- `paper_trading_trades_YYYYMMDD_HHMMSS.csv` - Trade history
- `paper_trading_equity_YYYYMMDD_HHMMSS.csv` - Equity curve

### Console Output

Real-time updates showing:
- 📈 Position openings (LONG/SHORT)
- 💰 Profitable trades closed
- 💸 Losing trades closed
- 📊 Portfolio summary

---

## 🏗️ Model Architecture (v2 - Simplified)

The v2 architecture is **deliberately simplified** to prevent overfitting on noisy stock market data:

```
Input Layer (window_size × 15 features)
        ↓
Normalization Layer
        ↓
Bidirectional LSTM (64 units)  ← Simplified: removed Conv1D
        ↓
BatchNorm + Dropout
        ↓
Dense Layer (64 units, ReLU)  ← Simplified: removed 3-layer residual tower
        ↓
BatchNorm + Dropout
        ↓
Output Layer (1 unit) - Return Prediction
```

### Why Simpler is Better for Stock Markets

| Component | v1 (Over-engineered) | v2 (Simplified) | Reason |
|-----------|---------------------|-----------------|--------|
| **Features** | 33 | 15 | Reduces overfitting |
| **Conv1D** | Multi-scale (3,7,15) | Removed | Added noise, not signal |
| **Attention** | Multi-head ensemble (4,8,16) | Removed | Overfitting to noise |
| **Dense Layers** | 3 residual blocks | 1 layer | Simpler = better generalization |
| **LSTM** | 128 units, seq=True | 64 units, seq=False | Reduced capacity |
| **Recurrent Dropout** | 0.15 | 0.1 (capped) | More stable training |

**Key Insight**: Daily stock returns have low signal-to-noise ratio. Complex architectures learn noise patterns that don't generalize.

---

## 🔬 Features (v2 - Reduced Set)

The v2 model uses **15 carefully selected features** (reduced from 33) to prevent overfitting:

### Core Price Features (5)
| Feature | Description |
|---------|-------------|
| `close_lr` | Log return of close price |
| `open_gap` | Open vs previous close gap |
| `close_open` | Intraday move (close - open) |
| `hl_range` | Intraday range (high - low) |

### Lagged Returns (3)
| Feature | Description |
|---------|-------------|
| `close_lr_lag1` | 1-day lagged return |
| `close_lr_lag3` | 3-day lagged return |
| `close_lr_lag5` | 5-day lagged return |

### Momentum & Volatility (2)
| Feature | Description |
|---------|-------------|
| `mom_5` | 5-period momentum |
| `vol_20` | 20-period volatility |

### Technical Indicators (3)
| Feature | Description |
|---------|-------------|
| `rsi_14` | Relative Strength Index |
| `macd_hist` | MACD histogram (most informative component) |
| `bb_pct` | Bollinger Bands %B |

### Volume & Regime (2)
| Feature | Description |
|---------|-------------|
| `vol_ma_ratio` | Volume vs 20-period MA ratio |
| `trend_strength` | Trend strength measure |

**Removed Features** (to reduce overfitting): vol_lr, close_lr_lag10/21, mom_3/10/21, vol_5/10/60, rsi_7, macd/signal, atr_14, obv_lr, vol_std_20, close_ma_ratio, hl_range_pct, vol_regime

---

## 🎯 Trading Strategies

The system supports multiple trading strategies:

### 1. Sign Strategy
- **Logic**: Long if prediction > 0, Short if prediction < 0
- **Use Case**: Directional trading based on model signal

### 2. Long Strategy
- **Logic**: Long only when prediction ≥ threshold
- **Use Case**: Conservative long-only trading

### 3. Tanh Strategy
- **Logic**: Position size = tanh(α × prediction)
- **Use Case**: Smooth position sizing in [-1, 1]

### 4. Top Quantile (topq)
- **Logic**: Long top q%, Short bottom q%
- **Use Case**: Relative value trading

### 5. Long Top Quantile
- **Logic**: Long top q% only
- **Use Case**: Best opportunities long-only

---

## 📊 Performance Metrics

### Prediction Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| MSE | Mean Squared Error | Lower is better |
| MAE | Mean Absolute Error | Lower is better |
| Directional Accuracy | % correct direction predictions | > 0.55 |

### Trading Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Total Return | Cumulative return | > 0% |
| Annualized Return | Compounded annual return | > 10% |
| Sharpe Ratio | Risk-adjusted return | > 1.0 |
| Max Drawdown | Largest peak-to-trough decline | < -20% |
| Win Rate | % profitable trades | > 50% |
| Profit Factor | Gross profit / Gross loss | > 1.5 |

---

## 📁 Project Structure

```
trading-bot-demo-2/
├── model.py                 # Model architecture definition
├── train.py                 # Training pipeline
├── evaluate.py              # Model evaluation
├── paper_trading.py         # Paper trading system
├── extract_stock.py         # Helper to extract single stock data
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── USAGE.md                 # Detailed usage guide
├── us_stock_market.csv      # US stock market data (501 stocks)
├── artifacts/               # Trained models and outputs
│   └── model.keras          # Saved model
├── .venv/                   # Virtual environment
└── evaluation.png           # Equity curve plot
```

---

## 🔧 Troubleshooting

### Common Issues

**1. Model not found error**:
```
FileNotFoundError: Model file not found: artifacts/model.keras
```
**Solution**: Train a model first:
```bash
python train.py --csv us_stock_market.csv --save-model artifacts/model.keras
```

**2. CUDA/GPU warnings**:
```
Could not find cuda drivers... GPU will not be used
```
**Solution**: This is normal for CPU-only systems. Training will proceed on CPU.

**3. Insufficient data**:
```
ValueError: No sequences were created
```
**Solution**:
- Check that CSV has enough data points (> window_size)
- Verify CSV format matches expected columns

**4. yfinance data fetch error**:
```
No data received for symbol AAPL
```
**Solution**:
- Check internet connection
- Verify symbol is correct (e.g., AAPL, MSFT, TSLA)
- Try during market hours (stocks trade 9:30 AM - 4:00 PM ET)

**5. Model not profitable / losing money**:
```
Equity curve shows consistent losses, long-only baseline performs better
```
**Solution**: This is a common issue with stock prediction. Try:
- Use v2 simplified architecture (this version) - v1 was overfitting
- Reduce feature set to 15 core features (done in v2)
- Increase risk aversion: `--risk-aversion 0.25`
- Reduce tanh-alpha: `--tanh-alpha 5.0` (more conservative positions)
- Use higher transaction cost: `--cost-bps 2.0` (more realistic)
- Train longer: `--epochs 50 --pretrain-epochs 15`
- Consider that daily stock returns have low predictability

---

## ⚠️ Important Notes on Profitability

**Why is my model losing money?**

This is the #1 question in trading bot development. Here's the reality:

1. **Daily stock returns are noisy** - The signal-to-noise ratio is very low
2. **Overfitting is easy** - Complex models learn noise patterns that don't generalize
3. **Transaction costs matter** - Even 1-2 bps can erase profits from frequent trading
4. **Past performance ≠ future results** - Backtest metrics are often overly optimistic

**What v2 does differently**:
- ✅ Fixed critical drawdown penalty bug (was rewarding drawdowns!)
- ✅ Simplified architecture (removed Conv1D, attention ensemble)
- ✅ Reduced features (15 instead of 33)
- ✅ Conservative defaults (lower position sizing, higher risk aversion)
- ✅ Realistic transaction costs (2 bps)

**Still losing money?** Consider:
- The model may not be profitable on this data (common for stocks)
- Try longer timeframes (weekly/monthly data has better signal)
- Add external features (earnings reports, news sentiment, macro indicators)
- Use ensemble methods (train multiple models, average predictions)
- Accept that consistent alpha in stock markets is extremely difficult

---

## 📝 License

This project is for educational and research purposes. Trading involves substantial risk of loss. Past performance does not guarantee future results.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

---

## 📧 Support

For questions or issues, please open an issue on the project repository.

---

**Disclaimer**: This software is for educational purposes only. Do not use for actual trading without thorough testing and understanding of the risks involved. Stock trading involves substantial risk of loss. Past performance does not guarantee future results.
