## 📈 Stock Trader

An old project of mine used to do paper trading on stocks based on news headlines. Recovered from 2024.
Needs some preprocessed news to work, and maybe some changes for the site scraping & trading APIs

# How it works

- Searches for articles for certain stocks from Wall Street Journal with Selenium
- Processes their headlines with AI and gets a sentiment value
- Based on this value, it decides whether to buy / sell stocks from the portfolio
- Submits orders via Alpaca's API for a **paper trading** account. Because of some limitations of Alpaca, the logic for trailing stop-loss trades is custom-made here.

---
*Please, don't use this with real money, this is just a fun project & demonstration of how web-scraping, AI and finance can collide.*
*(though I can attest that it was successful, at least for the time frame I was running it. Don't know if the bull market or the bot logic is to blame...)*
