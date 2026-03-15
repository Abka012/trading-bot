# 🚀 Quick Commands for Paper Trading

## ⚡ ONE COMMAND TO TRADE ALL 20 POPULAR STOCKS

```bash
./trade_all_popular_stocks.sh
```

That's it! This single command will:
- Extract data for all 20 popular stocks
- Train custom models for each stock
- Run paper trading (30 minutes per stock)
- Save all outputs to organized folders
- Generate comprehensive summary report

**Estimated time:** 30-60 minutes

**Or using Python directly:**
```bash
python run_paper_trading.py --top 20 --duration 30 --epochs 20
```

---

## Other Quick Commands

### Trade Specific Stocks
```bash
# Trade Apple and Microsoft
python run_paper_trading.py --symbols AAPL,MSFT --duration 30

# Trade 5 popular stocks
python run_paper_trading.py --symbols AAPL,MSFT,GOOGL,AMZN,TSLA --duration 30
```

### Trade Top Stocks by Volume
```bash
# Trade top 10 most active stocks
python run_paper_trading.py --top 10 --duration 60

# Trade top 20 most active stocks (takes longer)
python run_paper_trading.py --top 20 --duration 60 --epochs 15
```

### Trade All Popular Stocks
```bash
# Trade all 20 popular stocks
python run_paper_trading.py --top 20 --duration 30 --epochs 10
```

## Custom Training Options

```bash
# Quick test (fast)
python run_paper_trading.py --symbols AAPL --duration 5 --epochs 5

# Production training (slower but better)
python run_paper_trading.py --symbols AAPL,MSFT,NVDA --duration 60 --epochs 50 --window 60

# Use existing model (skip training)
python run_paper_trading.py --symbols AAPL --duration 30 --skip-training --existing-model artifacts/model.keras
```

## Output Organization

All outputs are automatically organized into folders:

```
backend/tradingBot/
├── data/
│   └── extracted_stocks/
│       ├── aapl_data.csv
│       └── msft_data.csv
├── artifacts/
│   └── models/
│       ├── aapl_model.keras
│       └── msft_model.keras
├── outputs/
│   ├── trades/
│   │   ├── aapl_trades_YYYYMMDD_HHMMSS.csv
│   │   └── msft_trades_YYYYMMDD_HHMMSS.csv
│   ├── equity/
│   │   ├── aapl_equity_YYYYMMDD_HHMMSS.csv
│   │   └── msft_equity_YYYYMMDD_HHMMSS.csv
│   └── reports/
│       └── summary_report_YYYYMMDD_HHMMSS.txt
└── outputs/logs/
```

## Available Popular Stocks

The script includes these popular stocks by default:

| Symbol | Company |
|--------|---------|
| AAPL | Apple Inc. |
| MSFT | Microsoft Corporation |
| GOOGL | Alphabet Inc. |
| AMZN | Amazon.com Inc. |
| NVDA | NVIDIA Corporation |
| META | Meta Platforms Inc. |
| TSLA | Tesla Inc. |
| JPM | JPMorgan Chase & Co. |
| V | Visa Inc. |
| JNJ | Johnson & Johnson |
| WMT | Walmart Inc. |
| PG | Procter & Gamble Co. |
| MA | Mastercard Inc. |
| UNH | UnitedHealth Group Inc. |
| HD | Home Depot Inc. |
| DIS | Walt Disney Co. |
| BAC | Bank of America Corp. |
| NFLX | Netflix Inc. |
| ADBE | Adobe Inc. |

## Parameter Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--symbols` | None | Comma-separated stock symbols |
| `--top` | None | Top N stocks by trading volume |
| `--duration` | 30 | Paper trading duration (minutes) |
| `--interval` | 1 | Time between cycles (seconds) |
| `--epochs` | 20 | Training epochs per stock |
| `--window` | 60 | Lookback window (days) |
| `--skip-training` | False | Use existing models |
| `--existing-model` | None | Use specific model file |
| `--input-csv` | us_stock_market.csv | Source data file |

## Example Workflows

### 1. Quick Test (5 minutes)
```bash
python run_paper_trading.py --symbols AAPL --duration 5 --epochs 5
```

### 2. Standard Trading (30 minutes)
```bash
python run_paper_trading.py --symbols AAPL,MSFT,GOOGL --duration 30 --epochs 20
```

### 3. Full Portfolio Trading (2-3 hours)
```bash
python run_paper_trading.py --top 20 --duration 60 --epochs 30
```

### 4. Using Pre-trained Model
```bash
# First train a general model
python train.py --csv us_stock_market.csv --epochs 50 --save-model artifacts/model.keras

# Then trade multiple stocks with the same model
python run_paper_trading.py --symbols AAPL,MSFT,NVDA --duration 30 --existing-model artifacts/model.keras
```

## Viewing Results

After paper trading completes:

```bash
# View summary report
cat outputs/reports/summary_report_*.txt

# View trade history
cat outputs/trades/aapl_trades_*.csv

# View equity curve
cat outputs/equity/aapl_equity_*.csv

# Or open in Python/pandas
python -c "import pandas as pd; df = pd.read_csv('outputs/trades/aapl_trades_*.csv'); print(df)"
```

## Cleaning Up

```bash
# Remove all generated outputs
rm -rf data/ outputs/ artifacts/models/

# Keep only the main model
rm -rf data/ outputs/
rm -f artifacts/models/*  # Keep artifacts/model.keras
```

## Tips

1. **Start Small**: Test with 1-2 stocks first to ensure everything works
2. **Short Duration**: Use `--duration 5` for quick tests
3. **Fewer Epochs**: Use `--epochs 5-10` for testing, `30-50` for production
4. **Organized Outputs**: All files are automatically organized by stock and timestamp
5. **Check Availability**: Not all popular stocks may be in your CSV file

## Troubleshooting

**Stock not found:**
```bash
# Check available symbols
python -c "import pandas as pd; df = pd.read_csv('us_stock_market.csv'); print(df['symbol'].unique()[:50])"
```

**Out of memory:**
```bash
# Reduce epochs or number of stocks
python run_paper_trading.py --symbols AAPL,MSFT --epochs 10
```

**Slow training:**
```bash
# Use fewer epochs and smaller window
python run_paper_trading.py --symbols AAPL --epochs 10 --window 30
```
