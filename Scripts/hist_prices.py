#!/usr/bin/python3

# Could've also used json, but there is no particular need.
import yfinance

# Updating the historical prices to be used in stock_trader.py
with open("/home/mimis/Projects/StockTrader/StockSpecials/historicals.txt", "w") as f:
  f.write("{")

  safe_company_tickers = ["SMCI",
                          "NVDA",
                          "AMD",
                          "META",
                          "MSFT",
                          "TSM",
                          "TSLA",
                          "LLY",
                          "GOOGL",
                          "AMZN",
                          "AAPL",
                          "NFLX",
                          "DIS",
                          "KO",
                          "SBUX",
                          "JNJ",
                          "PEP",
                          "PANW",
                          "COIN",
                          "AVGO",
                          "ADBE",
                          "PFE",
                          "ABBV",
                          "MRK",
                          "ABNB",
                          "DELL",
                          ]
  # For each ticker, get the stock's 7-day close prices with a 2 decimal precision.
  tickers = yfinance.Tickers(" ".join(safe_company_tickers))
  for ticker in tickers.tickers:
    prices = list(tickers.tickers[ticker].history(period="7d")["Close"])
    prices = [float(f"{price:.2f}") for price in prices]
    avg = sum(prices) / 7
    f.write(f"{ticker}: {avg}, ")

  f.write("}")
