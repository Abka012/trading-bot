# 🚀 Trade All 20 Popular Stocks - One Command

## Quick Start

```bash
./trade_all_popular_stocks.sh
```

That's it. This will run end-to-end paper trading for the popular stock set.

## What This Does

This single command will:

1. **Extract Data** - Pull individual stock data for all 20 popular stocks
2. **Train Models** - Create custom AI models for each stock (20 epochs each)
3. **Paper Trade** - Run 30-minute trading simulations for each stock
4. **Organize Outputs** - Save everything to neatly organized folders
5. **Generate Report** - Create a comprehensive summary of all trading activity

## Stocks Being Traded

| Symbol | Company | Symbol | Company |
|--------|---------|--------|---------|
| AAPL | Apple Inc. | JPM | JPMorgan Chase |
| MSFT | Microsoft | V | Visa Inc. |
| GOOGL | Alphabet | JNJ | Johnson & Johnson |
| AMZN | Amazon | WMT | Walmart |
| NVDA | NVIDIA | PG | Procter & Gamble |
| META | Meta | MA | Mastercard |
| TSLA | Tesla | UNH | UnitedHealth |
| BRK.B | Berkshire Hathaway | HD | Home Depot |
| DIS | Disney | BAC | Bank of America |
| NFLX | Netflix | ADBE | Adobe |

## Time Required

- **Estimated:** 30-60 minutes
- **Depends on:** CPU speed, number of cores

## Output Structure

After completion, you'll find:

```
outputs/
├── trades/           # Trade history for each stock
├── equity/           # Equity curve data
└── reports/          # Summary report

artifacts/models/      # Trained models for each stock
data/extracted_stocks/ # Individual stock data files
```

## Viewing Results

```bash
# View summary report
cat outputs/reports/summary_report_*.txt

# View all trade files
ls -lh outputs/trades/

# View all equity files
ls -lh outputs/equity/
```

## Requirements

- Virtual environment must be set up (`.venv/`)
- `us_stock_market.csv` must be present
- All dependencies installed (`pip install -r requirements.txt`)

## Troubleshooting

**Script not executable?**
```bash
chmod +x trade_all_popular_stocks.sh
```

**Virtual environment missing?**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Data file missing?**
Make sure `us_stock_market.csv` is in the current directory.

## Customization

Want to modify the trading parameters? Edit the script:

```bash
# Open the script
nano trade_all_popular_stocks.sh

# Find and modify these lines:
--duration 30      # Change trading duration (minutes)
--epochs 20        # Change training epochs
--window 60        # Change lookback window
```

## Alternative: Python Command

If you prefer Python directly:

```bash
python run_paper_trading.py --top 20 --duration 30 --epochs 20
```

Or trade specific stocks:

```bash
python run_paper_trading.py --symbols AAPL,MSFT,TSLA --duration 30 --epochs 20
```

## After Trading Completes

1. **Check the summary report** in `outputs/reports/`
2. **Review trade history** in `outputs/trades/`
3. **Analyze equity curves** in `outputs/equity/`
4. **Compare performance** across different stocks

## Next Steps

- Compare results across stocks
- Analyze which stocks performed best
- Review winning vs losing trades
- Experiment with different parameters
- Try trading with different time periods

---

**Happy Trading! 📈**

*Remember: This is for educational purposes only. Not financial advice.*
