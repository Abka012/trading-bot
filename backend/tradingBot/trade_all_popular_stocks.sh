#!/bin/bash
#
# Trade All 20 Popular US Stocks
# ================================
# This script runs paper trading on all 20 popular US stocks automatically.
#
# What it does:
# 1. Creates organized folder structure
# 2. Extracts data for all 20 stocks
# 3. Trains custom models for each stock
# 4. Runs paper trading for each stock
# 5. Organizes all outputs into folders
# 6. Generates comprehensive summary report
#
# Usage:
#   ./trade_all_popular_stocks.sh
#   or
#   bash trade_all_popular_stocks.sh
#
# Estimated time: 30-60 minutes (depending on CPU)
#

echo "========================================================================"
echo "🚀 TRADING ALL 20 POPULAR US STOCKS"
echo "========================================================================"
echo ""
echo "This will:"
echo "  • Extract data for 20 popular stocks"
echo "  • Train custom models for each stock"
echo "  • Run paper trading (30 min per stock)"
echo "  • Save all outputs to organized folders"
echo ""
echo "Estimated time: 30-60 minutes"
echo ""
echo "Stocks to trade:"
echo "  AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, JPM, V, JNJ,"
echo "  WMT, PG, MA, UNH, HD, DIS, BAC, NFLX, ADBE, BRK.B"
echo ""
echo "========================================================================"
echo ""

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found at .venv"
    echo "Please create it with: python3 -m venv .venv"
    exit 1
fi

# Check if us_stock_market.csv exists
if [ ! -f "us_stock_market.csv" ]; then
    echo "❌ us_stock_market.csv not found!"
    exit 1
fi

echo "✅ Data file found: us_stock_market.csv"
echo ""

# Run the paper trading script with all 20 popular stocks
python run_paper_trading.py \
    --symbols "AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA,JPM,V,JNJ,WMT,PG,MA,UNH,HD,DIS,BAC,NFLX,ADBE,BRK.B" \
    --duration 30 \
    --interval 1 \
    --epochs 20 \
    --window 60 \
    --input-csv "us_stock_market.csv"

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "✅ TRADING COMPLETE!"
    echo "========================================================================"
    echo ""
    echo "📁 Outputs saved to:"
    echo "   • Trades:   outputs/trades/"
    echo "   • Equity:   outputs/equity/"
    echo "   • Reports:  outputs/reports/"
    echo "   • Models:   artifacts/models/"
    echo "   • Data:     data/extracted_stocks/"
    echo ""
    echo "📊 View summary report:"
    echo "   cat outputs/reports/summary_report_*.txt"
    echo ""
    echo "========================================================================"
else
    echo ""
    echo "========================================================================"
    echo "❌ TRADING FAILED"
    echo "========================================================================"
    echo ""
    echo "Check the error messages above for details."
    echo ""
fi
