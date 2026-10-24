#!/usr/bin/python3

# For news / stock data fetching
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# For time manipulations
import datetime
import pytz

# For headline analysis
from hugchat import hugchat
from hugchat.login import Login

# Alpaca's official Python API
from alpaca.trading import TradingClient
from alpaca.trading.requests import GetOrdersRequest, LimitOrderRequest, MarketOrderRequest
from alpaca.trading.enums import QueryOrderStatus, OrderStatus, OrderSide, PositionSide, TimeInForce

# For faster execution
from concurrent.futures import ProcessPoolExecutor

# Other / Mixed
import json
import time
import re

# To handle credentials
from dotenv import load_dotenv
import os


project_path = "/home/mimis/Projects/StockTrader"


# Loading some credentials from environment variables
load_dotenv(f"{project_path}/.env")


if __name__ == "__main__":
  # Defining a list of 'safe' company's Ticker Symbols:
  safe_company_tickers = ["SMCI",
                          "NVDA",
                          "AMD",
                          "MU",
                          "META",
                          "MSFT",
                          "TSM",
                          "TSLA",
                          "GOOGL",
                          "AMZN",
                          "AAPL",
                          "COIN",
                          "ADBE",
                          "NFLX",
                          "KO",
                          "SBUX",
                          "PEP",
                          "ABNB",
                          "DELL",
                          ]

  # Getting the credentials from environment variables
  api_key = os.environ.get("API_KEY")
  secret_key = os.environ.get("SECRET_KEY")

  client = TradingClient(api_key, secret_key, paper=True)

  # Getting all open positions. open_positions is a list of Position objects with several attributes like qty, symbol etc.
  current_stock_names = []
  long_positions = []
  short_positions = []
  open_positions = client.get_all_positions()

  for position in open_positions:
    current_stock_names.append(position.symbol)
    if position.side is PositionSide.LONG:
      long_positions.append(position.symbol)
    else:
      short_positions.append(position.symbol)

  # Getting all unfilled orders:
  unfilled = {}

  get_orders_data = GetOrdersRequest(
      status=QueryOrderStatus.ALL,
      limit=480,
      nested=True  # show nested multi-leg orders
      )

  for order in client.get_orders(filter=get_orders_data):
    if not order.status in [OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REPLACED]:
      if not order.symbol in unfilled:
        unfilled[order.symbol] = {"side": order.side, "ID": order.id}

  # Getting the companies the user the bot trades with decided to ignore.
  ignored = []
  with open(f"{project_path}/StockSpecials/ignore.txt") as ignore:
    for line in ignore.readlines():
      ignored.append(line.rstrip())

  # Getting the current immune stocks, good & bad, using the function below
  immune = {}
  bad_immune = {}

def get_immune_file(filename, immune_dict):
  # Basically reading the file, splitting the company and it's immune time for each line, and updating the dictionary given.
  with open(f"{project_path}/StockSpecials/{filename}") as f:
    for line in f.readlines():
      if line != "\n":
        compNtime = line.split()
        company = compNtime[0]
        time = compNtime[1:]
        immune_dict[company] = " ".join(time).rstrip()

def filter_immune_file(filename, immune_dict):
  # Looking for expired immune companies, and only keeping the ones that haven't expired.
  with open(f"{project_path}/StockSpecials/{filename}", "w") as f:
    for item, time in immune_dict.items():
      dateNtime = time.split()
      year, month, day = dateNtime[0].split("-")
      hour, minute, second = dateNtime[1].split(":")
      if datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second)) > datetime.datetime.today() - datetime.timedelta(1):
        f.write(f"{item} {time}\n")

if __name__ == "__main__":
  get_immune_file("immune.txt", immune)
  get_immune_file("bad_immune.txt", bad_immune)

  # Market holidays
  holidays = [
    "01-01",
    "01-15",
    "02-19",
    "03-29",
    "05-27",
    "06-19",
    "07-04",
    "09-02",
    "11-28",
    "12-25",
    ]

def market_status():
    # Set the timezone to US Eastern Time (ET), and get date in month-day format
    tz = pytz.timezone('America/New_York')
    now = datetime.datetime.now(tz)
    short_date = datetime.date.today().strftime("%m-%d")

    # Check if it's a weekday (Monday to Friday), within trading hours, and if it's not a market holiday, and decide what status to return.
    # Time checks are done by comparing open times, current times, and close time in minutes.
    minute_time = now.hour * 60 + now.minute
    if 0 <= now.weekday() <= 4 and not short_date in holidays:
      if 4 * 60 <= minute_time < 9 * 60 + 30:
        return "pre-market-hours"
      elif 16 * 60 <= minute_time <= 20 * 60:
        return "after-hours"
      elif 9 * 60 + 30 <= minute_time < 16 * 60:
        return "open"
    return "closed"

# Now getting the market's status.
status = market_status()

def get_news_prices(companies):
  news = []
  new_sentiments = {}
  prices = {}

  # Log in to HuggingFace and grant authorization to HuggingChat. Different account for different processor.
  PASSWD = os.environ.get("PASS")
  if __name__ == "main":
    EMAIL = os.environ.get("EMAIL1")
    cookie_path_dir = "./cookies/"
  else:
    EMAIL = os.environ.get("EMAIL2")
    cookie_path_dir = "./cookies_2/"

  sign = Login(EMAIL, PASSWD)
  cookies = sign.login(cookie_dir_path=cookie_path_dir, save_cookies=True)

  # Create your ChatBot
  chatbot = hugchat.ChatBot(cookies=cookies.get_dict())

  assistant = chatbot.search_assistant(assistant_name="ChatGpt")
  chatbot.new_conversation(assistant=assistant, switch_to=True)

  # Setting options for Chromium to help the process be as fast as possible.
  chrome_options = webdriver.ChromeOptions()
  chrome_options.add_argument('--log-level=3')
  chrome_options.add_argument("--disable-extensions")
  chrome_options.add_argument("--disable-gpu")
  chrome_options.add_argument("--disable-infobars")
  chrome_options.add_argument("--disable-notifications")
  chrome_options.add_argument("--no-sandbox")
  chrome_options.add_argument("--disable-dev-shm-usage")

  # Opening the browser with the cookie (EDIT IN 2026: NOT SURE IF THE COOKIE STILL WORKS XD... MAYBE REPLACE IT WITH ONE YOU'LL FIND BY MANUALLY LOGGING IN ONCE. IF IT'S NECESSARY.)
  # I REMEMBER SUCH A PROBLEM WAS ALSO FIXED WITH XVFB-RUN TO RUN THE BROWSER WITHOUT HEADLESS MODE ON A VISUAL FRAME BUFFER
  service = Service('/usr/bin/chromedriver')
  driver = webdriver.Chrome(service=service, options=chrome_options)
  driver.get(f"https://www.wsj.com/market-data/quotes/{safe_company_tickers[0]}")
  driver.add_cookie({"name": "datadome", "value": "EmVVS6CNLnHSZVg8Xv1hlu2jUrZB27x4~wz8X~L6aHNL03moRmKFJVXgGlKTcXUI0Sls2dSsAr5yjWVI42v5Eb_xngPCGxKk1I3ZUNLRv~b0~9C0p8OkkW9by5v4Jqon", "domain": ".wsj.com", "path": "/"})
  driver.refresh()

  # Setting up stuff related to element-presence waiting. Max wait time for each element: 2 sec.
  # ANOTHER EDIT IN 2026: THE LAYOUT MAY HAVE CHANGED
  element_wait = WebDriverWait(driver, 2)

  print(driver.page_source)

  elem_locator = (By.ID, "sp_message_iframe_910380")
  manage_iframe = element_wait.until(EC.presence_of_element_located(elem_locator))
  driver.switch_to.frame(manage_iframe)

  element_wait = WebDriverWait(driver, 2)
  elem_locator = (By.XPATH, "//button[@title='MANAGE SETTINGS']")
  manage = element_wait.until(EC.presence_of_element_located(elem_locator))
  manage.click()

  driver.switch_to.default_content()

  element_wait = WebDriverWait(driver, 2)
  elem_locator = (By.ID, "sp_message_iframe_490347")
  reject_iframe = element_wait.until(EC.presence_of_element_located(elem_locator))
  driver.switch_to.frame(reject_iframe)

  element_wait = WebDriverWait(driver, 2)
  elem_locator = (By.XPATH, "//button[@title='REJECT ALL']")
  reject = element_wait.until(EC.presence_of_element_located(elem_locator))
  driver.execute_script("arguments[0].click();", reject)

  driver.switch_to.default_content()
  element_wait = WebDriverWait(driver, 2)

  # Get the sentiments of old news (for all companies) before checking for new ones.
  processed = {}
  with open(f"{project_path}/StockSpecials/processed_news.txt") as f:
    processed = json.load(f)

  # Get prices & news
  for stock in companies:
    if not stock == companies[0]:
      driver.get(f"https://www.wsj.com/market-data/quotes/{stock}")
      if driver.title == "500":
        driver.refresh()

      driver.implicitly_wait(5)

    try:
      elem_locator = (By.ID, "ms_quote_val")
      ext_price = element_wait.until(EC.presence_of_element_located(elem_locator))
      prices[stock] = ext_price.text
    except Exception:
      elem_locator = (By.ID, "quote_val")
      no_ext_price = element_wait.until(EC.presence_of_element_located(elem_locator))
      prices[stock] = no_ext_price.text

    elem_locator = (By.XPATH, "//input[@type='checkbox']")
    checkbox = element_wait.until(EC.presence_of_element_located(elem_locator))
    driver.execute_script("arguments[0].scrollIntoView();", checkbox)
    time.sleep(1)
    checkbox.click()

    elem_locator = (By.CLASS_NAME, "WSJTheme--headline--33gllX4Y ")
    news = element_wait.until(EC.presence_of_all_elements_located(elem_locator))
    elem_locator = (By.CLASS_NAME, "WSJTheme--cr_dateStamp--13KIPpOo ")
    news_dates = element_wait.until(EC.presence_of_all_elements_located(elem_locator))

    while not news[-1].text in processed[stock] or "hours ago" in news_dates[-1].text or datetime.datetime.strptime(news_dates[-1].text, "%m/%d/%y") >= datetime.datetime.strptime(str(datetime.date.today()), "%Y-%m-%d") - datetime.timedelta(days=7):
      elem_locator = (By.ID, "latestNewsLoad")
      load_btn = element_wait.until(EC.presence_of_element_located(elem_locator))
      driver.execute_script("arguments[0].scrollIntoView();", load_btn)
      load_btn.click()

      elem_locator = (By.CLASS_NAME, "WSJTheme--headline--33gllX4Y ")
      news = element_wait.until(EC.presence_of_all_elements_located(elem_locator))
      elem_locator = (By.CLASS_NAME, "WSJTheme--cr_dateStamp--13KIPpOo ")
      news_dates = element_wait.until(EC.presence_of_all_elements_located(elem_locator))

    # Filtering the old preprocessed news (up to a week)
    news = [new.text for new in news]
    new_sentiments[stock] = []
    for ind, new in enumerate(processed[stock]):
      if not re.search(r"[0-9]{2}/[0-9]{2}/[0-9]{2}", processed[stock][new]["date"]):
         continue

      date = datetime.datetime.strptime(processed[stock][new]["date"], "%m/%d/%y")
      if date < datetime.datetime.today() - datetime.timedelta(days=8):
        processed[stock] = processed[stock][:ind]
        break

    # Analyzing the recent news, and if an error occurs, essentially leaving the new_sentiments intact by only counting the preprocessed news. Also replacing the old processed news after adding new ones and removing old ones.
    try:
      for new in news:
        if new.rstrip() in processed[stock]:
          continue

        query_result = chatbot.chat(f"Assign a sentiment value from 1 to -1 according to how much the following new can impact {stock}'s stock price (answer only with the sentiment number): {new}")
        processed[stock][new] = {}
        processed[stock][new]["sentiment"] = float(query_result["text"])
        processed[stock][new]["date"] = news_dates[news.index(new)].text
    except Exception:
      continue

    # Finally, counting the preprocessed news & the ones found in the current run (added in 'processed' above).
    for new in processed[stock]:
      new_sentiments[stock].append(processed[stock][new]["sentiment"])

  with open(f"{project_path}/StockSpecials/processed_news.txt", "w") as f:
    json.dump(processed)

  chatbot.delete_conversation()
  return (new_sentiments, prices)

# The function to trade in Alpaca.
def trade(company, current_price, side, sentiment, articles, got_extra_sentiments):
  order_data = None

  # Getting our buying power.
  cash = float(client.get_account().buying_power)

  # Very important. Basically saying that in Buy orders, we buy with 15% of the account's capital, and in Sell ones, we sell all the equity. Kinda the opposite is true for shorts.
  trade_qty = 0
  limits = [] # If a stop loss is set, it will be handled down below. limits[0] = stop loss, limits[1] = max price (current here).

  if side == "buy":
    if not company in current_stock_names:
      trade_qty = (cash * 33 / 100) / current_price
      limits.append(round(current_price * 0.98))
      limits.append(current_price)
      current_stock_names.append(company)
    else:
      trade_qty = abs(float(client.get_open_position(company).qty))
  else:
    if not company in current_stock_names:
      trade_qty = (cash * 33 / 100) // current_price # Shorts can't be fractional.
      limits.append(round(current_price * 1.02))
      limits.append(current_price)
      current_stock_names.append(company)
    else:
      position_qty = abs(float(client.get_open_position(company).qty))
      trade_qty = position_qty

  if trade_qty == 0:
    print(f"Insufficient money for {company} (${current_price}) at {datetime.datetime.now()}.\n\n")
    if company in current_stock_names:
      current_stock_names.remove(company)
    return

  # Checking the market's status, and submitting the right order accordingly, with the right parameters.
  order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
  if status != "open":
    order_data = LimitOrderRequest(symbol = company,
                                   limit_price = current_price,
                                   qty = trade_qty,
                                   side = order_side,
                                   extended_hours = True,
                                   time_in_force = TimeInForce.DAY,
                                   )
  else:
    order_data = MarketOrderRequest(symbol = company,
                                    qty = trade_qty,
                                    side = order_side,
                                    time_in_force = TimeInForce.DAY,
                                    )
  # Setting / Erasing the take profit & stop loss
  current_stops_maxs = {}
  with open(f"{project_path}/StockSpecials/stops_maxs.txt") as f:
    if f.readline() != "\n":
      f.seek(0)
      current_stops_maxs = json.load(f)

  if limits != []:
    current_stops_maxs[company] = limits
  else:
    current_stops_maxs.pop(company)

  with open(f"{project_path}/StockSpecials/stops_maxs.txt", "w") as f:
    json.dump(current_stops_maxs, f)

  # Finally, submitting the order and logging the information.
  client.submit_order(order_data)
  print(f"""{side} -> {company} at {datetime.datetime.now()}. Sentiment: {sentiment}, Analyzed Articles: {len(articles)}, Added from Averages: {got_extra_sentiments}
Articles: {articles}\n\n""")

if __name__ == "__main__":
  # Getting each company's prices and news sentiments.
  new_sentiments = {}
  prices = {}
  hist_prices = {}

  executor = ProcessPoolExecutor()

  # Splitting the stocks to check between processors
  length_seg = len(safe_company_tickers) // 2
  part1 = executor.submit(get_news_prices, safe_company_tickers[: length_seg])
  part2 = get_news_prices(safe_company_tickers[length_seg:])

  executor.shutdown(wait=True)

  part1 = part1.result()

  new_sentiments.update(part1[0])
  new_sentiments.update(part2[0])

  prices.update(part1[1])
  prices.update(part2[1])

  # Getting each stock's 7-day historical prices.
  with open(f"{project_path}/StockSpecials/historicals.txt") as f:
    hist_prices = json.load(f)

  now = datetime.datetime.now()

  # Getting company's take profits & stop losses.
  stops_maxs = {}
  with open(f"{project_path}/StockSpecials/stops_maxs.txt") as f:
    if f.readline() != "\n":
      f.seek(0)
      stops_maxs = json.load(f)

  for company in safe_company_tickers:
    if not company in ignored:
      current_price = prices[company]
      avg_extras = 0
      sentiments = 0

      # See if the price has hit the stop loss, or if the peak has gone up, thus moving the stop loss up as well.
      if company in stops_maxs:
        if current_price > stops_maxs[company][1]:
          stops_maxs[company][1] = current_price
          if current_price > stops_maxs[company][0]:
            stops_maxs[company][0] = current_price * 0.98
          else:
            stops_maxs[company][0] = current_price * 1.02

          with open(f"{project_path}/StockSpecials/stops_maxs.txt", "w") as f:
            json.dump(stops_maxs, f)

        elif company in long_positions and current_price <= stops_maxs[company][0]:
          trade(company, current_price, "sell", "Moving Stop Loss Reached", [], 0)
        elif company in short_positions and current_price >= stops_maxs[company][0]:
          trade(company, current_price, "buy", "Moving Stop Loss Reached", [], 0)

      # Taking the 7 day average into consideration. In the formulas below, the third multiplier is a stabilizing one. 10 for Normal stability, change this up/down to add/remove gravity.
      avg = sum(hist_prices[company]) / 7

      if current_price < avg and company != "TSLA":  # You can laugh, but this is necessary (I guess)..
        avg_extras += (avg / current_price) * (((current_price - avg) / avg) * 100) * -5 # The greater the average & the current-to-avg %, the more sentiment points are added.
        sentiments += avg_extras

      elif current_price > avg:
        avg_extras -= (current_price / avg) * (((current_price - avg) / avg) * 100) * 5  # The greater the stock's price is & the current-to-avg %, the more sentiment points are deducted.
        sentiments += avg_extras

      # Adding sentiment points according to the news' sentiments.
      for sentiment in new_sentiments[company]:
        if sentiment <= -0.40:
          sentiments -= 80
        elif sentiment >= 0.40:
          sentiments += 80

        if new_sentiments[company].index(sentiment) < 10: # Only counting up to 10 semi-important news. Otherwise it would be very easy to reach the sentiment limit with a lot of them.
          if sentiment > 0:
            sentiments += sentiment * 100 # Recording sentiments as whole numbers, not decimals like .34

          if sentiment <= -0.2:
            sentiments -= sentiment * 2 * 100

      # Checking on their sentiments and selling/buying along with the other required actions & checks.
      open_short_conditions = not company in current_stock_names and len(current_stock_names) + len(unfilled) < 2 and sentiments <= -250
      sell_long_conditions = company in long_positions and (sentiments <= 0 or ((sentiments < 90 and status != "closed") or (sentiments < 45 and status == "closed")) and not company in immune)

      if sell_long_conditions or open_short_conditions:
        # Adding or refreshing the company's bad immunity, and removing it's good immunity
        bad_immune[company] = str(datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"))
        immune.pop(company, None)

        if not company in unfilled:
          trade(company, current_price, "sell", sentiments, valued_articles, avg_extras)
        elif unfilled[company]["side"] is OrderSide.BUY:
          client.cancel_order(unfilled[company]["ID"])
          print(f"Canceled -> {company} at {now}.\n\n")
        continue

      open_long_conditions = not company in current_stock_names and len(current_stock_names) + len(unfilled) < 2 and sentiments >= 250
      close_short_conditions = company in short_positions and (sentiments >= 0 or ((sentiments > -90 and status != "closed") or (sentiments > -45 and status == "closed")) and not company in bad_immune)

      if open_long_conditions or close_short_conditions:
        # Adding or renewing a company's immunity.
        immune[company] = str(datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"))

        # Buying the stock if the condition below is True
        if not company in unfilled:
          trade(company, current_price, "buy", sentiments, valued_articles, avg_extras)
        elif unfilled[company]["side"] is OrderSide.SELL:
          client.cancel_order(unfilled[company]["ID"])
          print(f"Canceled -> {company} at {now}.\n\n")

  # Looking for expired immune companies, and only keeping the ones that haven't expired, using the filter_immune_file function defined above.
  filter_immune_file("immune.txt", immune)
  filter_immune_file("bad_immune.txt", bad_immune)
