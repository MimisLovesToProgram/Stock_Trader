#!/usr/bin/python3

import yfinance

with open("/home/mimis/Projects/StockTrader/StockSpecials/historicals.txt", "w") as f:
  f.write("{")

  safe_company_tickers = ["SMCI",
                          "NVDA",
                          "AMD",
                          "META",
                          "MSFT",
                          "TSM",
                          "NFLX",
                          "LLY",
                          "GOOGL",
                          "AMZN",
                          "AAPL",
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
  tickers = yfinance.Tickers(" ".join(safe_company_tickers))
  for ticker in tickers.tickers:
    prices = list(tickers.tickers[ticker].history(period="7d")["Close"])
    prices = [float(f"{price:.2f}") for price in prices]
    f.write(f"{ticker}: {prices}, ")

  f.write("}")
