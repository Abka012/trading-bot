#!/usr/bin/env python3
"""
Extract and Paper Trade Popular US Stocks.

This script:
1. Extracts popular US stocks from us_stock_market.csv
2. Organizes outputs into structured folders
3. Runs paper trading for each stock
4. Saves results in organized directories

Usage:
    python run_paper_trading.py --symbols AAPL,MSFT,TSLA --duration 30
    python run_paper_trading.py --top 10 --duration 30  # Top 10 most active stocks
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Popular US stocks by market cap and trading volume
POPULAR_STOCKS = [
    "AAPL",  # Apple Inc.
    "MSFT",  # Microsoft Corporation
    "GOOGL",  # Alphabet Inc. Class A
    "AMZN",  # Amazon.com Inc.
    "NVDA",  # NVIDIA Corporation
    "META",  # Meta Platforms Inc.
    "TSLA",  # Tesla Inc.
    "BRK.B",  # Berkshire Hathaway Inc.
    "JPM",  # JPMorgan Chase & Co.
    "V",  # Visa Inc.
    "JNJ",  # Johnson & Johnson
    "WMT",  # Walmart Inc.
    "PG",  # Procter & Gamble Co.
    "MA",  # Mastercard Inc.
    "UNH",  # UnitedHealth Group Inc.
    "HD",  # Home Depot Inc.
    "DIS",  # Walt Disney Co.
    "BAC",  # Bank of America Corp.
    "NFLX",  # Netflix Inc.
    "ADBE",  # Adobe Inc.
]


def create_directory_structure():
    """Create organized directory structure for outputs."""
    base_dirs = {
        "data": "data/extracted_stocks",
        "models": "artifacts/models",
        "trades": "outputs/trades",
        "equity": "outputs/equity",
        "reports": "outputs/reports",
        "logs": "outputs/logs",
    }

    for dir_path in base_dirs.values():
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    return base_dirs


def check_stock_available(symbol: str, csv_file: str = "us_stock_market.csv") -> bool:
    """Check if a stock symbol is available in the CSV."""
    import pandas as pd

    try:
        df = pd.read_csv(csv_file)
        available_symbols = df["symbol"].unique()
        return symbol in available_symbols
    except Exception as e:
        print(f"  ❌ Error checking availability: {e}")
        return False


def get_top_stocks_by_volume(
    csv_file: str = "us_stock_market.csv", top_n: int = 10
) -> list:
    """Get top N stocks by average trading volume."""
    import pandas as pd

    try:
        df = pd.read_csv(csv_file)

        # Calculate average volume per symbol
        avg_volume = df.groupby("symbol")["volume"].mean().sort_values(ascending=False)

        # Get top N symbols
        top_symbols = avg_volume.head(top_n).index.tolist()

        return top_symbols
    except Exception as e:
        print(f"  ❌ Error getting top stocks: {e}")
        return POPULAR_STOCKS[:top_n]


def extract_stock(
    symbol: str,
    input_csv: str = "us_stock_market.csv",
    output_dir: str = "data/extracted_stocks",
) -> str:
    """Extract a single stock's data from the main CSV."""
    output_path = os.path.join(output_dir, f"{symbol.lower()}_data.csv")

    print(f"\n{'=' * 60}")
    print(f"📥 Extracting {symbol} data...")
    print(f"{'=' * 60}")

    cmd = [
        sys.executable,
        "extract_stock.py",
        "--symbol",
        symbol,
        "--input",
        input_csv,
        "--output",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ❌ Failed to extract {symbol}: {result.stderr}")
        return None

    print(f"  ✅ Extracted data saved to: {output_path}")
    return output_path


def train_model(
    symbol: str,
    data_csv: str,
    output_dir: str = "artifacts/models",
    epochs: int = 20,
    window: int = 60,
) -> str:
    """Train a model for a specific stock."""
    model_path = os.path.join(output_dir, f"{symbol.lower()}_model.keras")

    print(f"\n{'=' * 60}")
    print(f"🎓 Training model for {symbol}...")
    print(f"{'=' * 60}")

    cmd = [
        sys.executable,
        "train.py",
        "--csv",
        data_csv,
        "--window",
        str(window),
        "--epochs",
        str(epochs),
        "--save-model",
        model_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ❌ Failed to train model: {result.stderr}")
        return None

    print(f"  ✅ Model saved to: {model_path}")
    return model_path


def run_paper_trading(
    symbol: str,
    model_path: str,
    data_csv: str,
    output_dir: str = "outputs/trades",
    equity_dir: str = "outputs/equity",
    duration: int = 30,
    interval: int = 1,
) -> dict:
    """Run paper trading for a specific stock."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'=' * 60}")
    print(f"📈 Running paper trading for {symbol}...")
    print(f"{'=' * 60}")

    cmd = [
        sys.executable,
        "paper_trading.py",
        "--model",
        model_path,
        "--symbol",
        symbol,
        "--csv",
        data_csv,
        "--duration",
        str(duration),
        "--interval",
        str(interval),
        "--capital",
        "10000",
        "--position-size",
        "0.1",
    ]

    # Run and capture output
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Print output
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    # Move generated files to organized folders
    trades_file = None
    equity_file = None

    # Find and move generated files
    for file in os.listdir("."):
        if file.startswith("paper_trading_trades_"):
            # Move to trades directory
            src = file
            dst = os.path.join(output_dir, f"{symbol.lower()}_trades_{timestamp}.csv")
            try:
                os.rename(src, dst)
                trades_file = dst
                print(f"  📁 Trades moved to: {dst}")
            except Exception as e:
                print(f"  ⚠️  Could not move trades file: {e}")

        if file.startswith("paper_trading_equity_"):
            # Move to equity directory
            src = file
            dst = os.path.join(equity_dir, f"{symbol.lower()}_equity_{timestamp}.csv")
            try:
                os.rename(src, dst)
                equity_file = dst
                print(f"  📁 Equity moved to: {dst}")
            except Exception as e:
                print(f"  ⚠️  Could not move equity file: {e}")

    return {
        "symbol": symbol,
        "trades_file": trades_file,
        "equity_file": equity_file,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def generate_summary_report(results: list, output_path: str = "outputs/reports"):
    """Generate a summary report of all paper trading results."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(output_path, f"summary_report_{timestamp}.txt")

    print(f"\n{'=' * 60}")
    print(f"📊 Generating summary report...")
    print(f"{'=' * 60}")

    with open(report_path, "w") as f:
        f.write("=" * 60 + "\n")
        f.write("PAPER TRADING SUMMARY REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Stocks Traded: {len(results)}\n\n")

        for result in results:
            f.write("-" * 60 + "\n")
            f.write(f"Symbol: {result['symbol']}\n")
            f.write(
                f"Status: {'✅ Success' if result['returncode'] == 0 else '❌ Failed'}\n"
            )
            if result["trades_file"]:
                f.write(f"Trades File: {result['trades_file']}\n")
            if result["equity_file"]:
                f.write(f"Equity File: {result['equity_file']}\n")
            f.write("\n")

    print(f"  ✅ Summary report saved to: {report_path}")
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="Extract and Paper Trade Popular US Stocks",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated list of stock symbols (e.g., AAPL,MSFT,TSLA)",
    )

    parser.add_argument(
        "--top", type=int, default=None, help="Number of top stocks by volume to trade"
    )

    parser.add_argument(
        "--input-csv",
        type=str,
        default="us_stock_market.csv",
        help="Input CSV file with stock data",
    )

    parser.add_argument(
        "--duration", type=int, default=30, help="Paper trading duration in minutes"
    )

    parser.add_argument(
        "--interval", type=int, default=1, help="Time between trading cycles in seconds"
    )

    parser.add_argument(
        "--epochs", type=int, default=20, help="Number of training epochs per stock"
    )

    parser.add_argument(
        "--window", type=int, default=60, help="Lookback window for training"
    )

    parser.add_argument(
        "--skip-training",
        action="store_true",
        help="Skip training and use existing models from artifacts/models/",
    )

    parser.add_argument(
        "--existing-model",
        type=str,
        default=None,
        help="Use existing model file for all stocks (e.g., artifacts/model.keras)",
    )

    args = parser.parse_args()

    # Determine which stocks to trade
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    elif args.top:
        symbols = get_top_stocks_by_volume(args.input_csv, args.top)
    else:
        symbols = POPULAR_STOCKS[:5]  # Default to first 5 popular stocks

    print(f"\n{'=' * 60}")
    print("🚀 US STOCK MARKET PAPER TRADING")
    print(f"{'=' * 60}")
    print(f"Stocks to trade: {', '.join(symbols)}")
    print(f"Duration: {args.duration} minutes")
    print(f"Interval: {args.interval} seconds")
    print(f"{'=' * 60}\n")

    # Create directory structure
    dirs = create_directory_structure()
    print("📁 Directory structure created:")
    for name, path in dirs.items():
        print(f"   {name}: {path}/")

    # Check which stocks are available
    print(f"\n{'=' * 60}")
    print("🔍 Checking stock availability...")
    print(f"{'=' * 60}")

    available_symbols = []
    for symbol in symbols:
        if check_stock_available(symbol, args.input_csv):
            available_symbols.append(symbol)
            print(f"  ✅ {symbol} - Available")
        else:
            print(f"  ❌ {symbol} - Not found in {args.input_csv}")

    if not available_symbols:
        print("\n❌ No available stocks found. Exiting.")
        sys.exit(1)

    print(f"\n✅ {len(available_symbols)} stocks available for trading")

    # Process each stock
    results = []

    for symbol in available_symbols:
        # Extract stock data
        data_csv = extract_stock(symbol, args.input_csv, dirs["data"])
        if not data_csv:
            continue

        # Train or load model
        if args.existing_model:
            model_path = args.existing_model
        elif args.skip_training:
            model_path = os.path.join(dirs["models"], f"{symbol.lower()}_model.keras")
            if not os.path.exists(model_path):
                print(f"  ⚠️  Model not found: {model_path}. Skipping {symbol}.")
                continue
        else:
            model_path = train_model(
                symbol, data_csv, dirs["models"], args.epochs, args.window
            )

        if not model_path:
            continue

        # Run paper trading
        result = run_paper_trading(
            symbol=symbol,
            model_path=model_path,
            data_csv=data_csv,
            output_dir=dirs["trades"],
            equity_dir=dirs["equity"],
            duration=args.duration,
            interval=args.interval,
        )

        results.append(result)

    # Generate summary report
    if results:
        generate_summary_report(results, dirs["reports"])

        print(f"\n{'=' * 60}")
        print("✅ PAPER TRADING COMPLETE")
        print(f"{'=' * 60}")
        print(f"Stocks processed: {len(results)}")
        print(f"Outputs saved to:")
        print(f"   📁 Trades:   {dirs['trades']}/")
        print(f"   📁 Equity:   {dirs['equity']}/")
        print(f"   📁 Reports:  {dirs['reports']}/")
        print(f"   📁 Models:   {dirs['models']}/")
        print(f"   📁 Data:     {dirs['data']}/")
        print(f"{'=' * 60}\n")
    else:
        print("\n❌ No stocks were successfully processed")
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
