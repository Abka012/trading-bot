# US Stock Market Trading Bot - Usage Guide

## Quick Start

This trading bot is now configured to work with **US stock market data** from `us_stock_market.csv`.
Models saved under `backend/tradingBot/artifacts/models` are used by the backend trading engine and shown in the AlphaMindStock dashboard.

## 1. Training a Model

### Basic Training (Recommended for Testing)
```bash
python train.py --csv us_stock_market.csv \
  --window 60 \
  --epochs 20 \
  --max-symbols 50 \
  --save-model artifacts/model.keras
```

### Full Training (Production)
```bash
python train.py --csv us_stock_market.csv \
  --window 60 \
  --epochs 50 \
  --pretrain-epochs 15 \
  --objective profit \
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

### Training Parameters Explained

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--csv` | `us_stock_market.csv` | Path to stock data CSV |
| `--window` | 60 | Lookback window (60 days for daily data) |
| `--epochs` | 20 | Number of training epochs |
| `--max-symbols` | 50 | Number of stocks to use (use 0 for all 501) |
| `--objective` | mse | Training objective: mse or profit |
| `--cs-mode` | none | Cross-sectional normalization: none/demean/zscore |

## 2. Evaluating the Model

```bash
python evaluate.py --model artifacts/model.keras \
  --csv us_stock_market.csv \
  --out evaluation.png \
  --verbose
```

This will generate:
- `evaluation.png` - Equity curve visualization
- Console output with detailed performance metrics

## 3. Paper Trading

### Option A: Using CSV File (Recommended - Works Offline)

**Step 1: Extract stock data for a specific symbol**
```bash
python extract_stock.py --symbol AAPL --output aapl_data.csv
```

**Step 2: Run paper trading with the CSV**
```bash
python paper_trading.py --model artifacts/model.keras \
  --symbol AAPL \
  --csv aapl_data.csv \
  --duration 60 \
  --interval 1
```

### Option B: Using Live Data (Requires Working yfinance)

```bash
python paper_trading.py --model artifacts/model.keras \
  --symbol AAPL \
  --duration 60 \
  --interval 60 \
  --live
```

**Note:** yfinance may not work reliably. If you encounter errors, use Option A with CSV files.

### Paper Trading Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--model` | `artifacts/model.keras` | Path to trained model |
| `--symbol` | `AAPL` | Stock ticker symbol |
| `--csv` | `None` | Optional CSV file for offline trading |
| `--capital` | 10000 | Initial capital (USD) |
| `--position-size` | 0.1 | Fraction of capital per trade |
| `--duration` | 60 | Trading duration (minutes) |
| `--interval` | 1 | Time between cycles (seconds) |

## 4. Available Stocks

The `us_stock_market.csv` file contains 501 stocks including:
- **AAPL** - Apple Inc.
- **MSFT** - Microsoft Corporation
- **GOOGL** - Alphabet Inc.
- **AMZN** - Amazon.com Inc.
- **TSLA** - Tesla Inc.
- **META** - Meta Platforms Inc.
- **NVDA** - NVIDIA Corporation
- **JPM** - JPMorgan Chase & Co.
- **V** - Visa Inc.
- **JNJ** - Johnson & Johnson

And 491 more stocks from the US stock market.

## 5. Complete Workflow Example

```bash
# Step 1: Train on multiple stocks
python train.py --csv us_stock_market.csv \
  --window 60 --epochs 30 --max-symbols 100 \
  --save-model artifacts/model.keras

# Step 2: Evaluate performance
python evaluate.py --model artifacts/model.keras \
  --csv us_stock_market.csv \
  --out evaluation.png --verbose

# Step 3: Extract specific stock for paper trading
python extract_stock.py --symbol AAPL --output aapl_data.csv

# Step 4: Run paper trading
python paper_trading.py --model artifacts/model.keras \
  --symbol AAPL \
  --csv aapl_data.csv \
  --duration 60 --interval 1
```

## 6. Troubleshooting

### yfinance Not Working
If you get errors like "Failed to get ticker" or "No data received":
```bash
# Use CSV file instead
python paper_trading.py --model artifacts/model.keras \
  --symbol AAPL \
  --csv aapl_data.csv
```

### Model Not Found
```bash
# Train a model first
python train.py --csv us_stock_market.csv --save-model artifacts/model.keras
```

### Insufficient Data
```bash
# Reduce window size or use more data
python train.py --csv us_stock_market.csv --window 30
```

### Out of Memory
```bash
# Reduce number of symbols
python train.py --csv us_stock_market.csv --max-symbols 20
```

## 7. Data Format

The `us_stock_market.csv` file has the following format:

```csv
date,symbol,open,high,low,close,volume
2016-01-05 00:00:00,WLTW,123.43,126.25,122.31,125.84,2163600.0
2016-01-06 00:00:00,WLTW,125.24,125.54,119.94,119.98,2386400.0
```

## 8. Performance Tips

1. **Use more stocks**: Train on 100-500 stocks for better generalization
2. **Longer training**: Use 50+ epochs for better convergence
3. **Profit objective**: Use `--objective profit` for better trading performance
4. **Cross-sectional normalization**: Use `--cs-mode zscore` to focus on relative performance
5. **Conservative parameters**: Use lower `--tanh-alpha` and higher `--risk-aversion` for safer trading

## 9. Expected Results

With proper training on US stock market data, you can expect:
- **Directional Accuracy**: 48-52% (stock returns are hard to predict)
- **Sharpe Ratio**: 0.2-0.5 (reasonable risk-adjusted returns)
- **Max Drawdown**: -10% to -30% (depends on risk parameters)
- **CAGR**: -5% to +10% (highly variable)

**Note:** Stock market prediction is extremely difficult. These models are for educational purposes and should not be used for actual trading without extensive testing and risk management.

## 10. File Structure

```
trading-bot-demo-2/
├── us_stock_market.csv      # Stock market data (501 stocks)
├── model.py                  # Model architecture
├── train.py                  # Training script
├── evaluate.py               # Evaluation script
├── paper_trading.py          # Paper trading script
├── extract_stock.py          # Helper to extract single stock data
├── artifacts/
│   └── model.keras           # Trained model
└── evaluation.png            # Performance plot
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the main README.md
3. Ensure you're using the correct data format
4. Start with small datasets for testing

**Disclaimer:** This software is for educational purposes only. Stock trading involves substantial risk of loss. Past performance does not guarantee future results.
