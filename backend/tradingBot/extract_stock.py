#!/usr/bin/env python3
"""
Extract a single stock's data from us_stock_market.csv for paper trading.

Usage:
    python extract_stock.py --symbol AAPL --output aapl_data.csv
    python extract_stock.py --symbol MSFT --output msft_data.csv
"""

import argparse
import sys

import pandas as pd


def main():
    parser = argparse.ArgumentParser(
        description="Extract single stock data from us_stock_market.csv"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Stock symbol to extract (e.g., AAPL, MSFT, TSLA)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV file path (default: {symbol}_data.csv)",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="us_stock_market.csv",
        help="Input CSV file path (default: us_stock_market.csv)",
    )
    args = parser.parse_args()

    print(f"Loading {args.input}...")
    try:
        df = pd.read_csv(args.input)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)

    print(f"Total records: {len(df)}")
    print(f"Available symbols: {df['symbol'].nunique()}")

    # Filter for the requested symbol
    stock_df = df[df["symbol"] == args.symbol].copy()

    if len(stock_df) == 0:
        print(f"\n❌ Symbol '{args.symbol}' not found in the CSV file.")
        print(f"\nAvailable symbols (first 50):")
        print(df["symbol"].unique()[:50])
        sys.exit(1)

    # Sort by date
    stock_df = stock_df.sort_values("date").reset_index(drop=True)

    # Determine output path
    output_path = args.output if args.output else f"{args.symbol.lower()}_data.csv"

    # Save to CSV
    stock_df.to_csv(output_path, index=False)

    print(f"\n✅ Successfully extracted {len(stock_df)} records for {args.symbol}")
    print(f"   Date range: {stock_df['date'].min()} to {stock_df['date'].max()}")
    print(f"   Saved to: {output_path}")
    print(f"\n💡 Use this file for paper trading:")
    print(
        f"   python paper_trading.py --model artifacts/model.keras --symbol {args.symbol} --csv {output_path}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
