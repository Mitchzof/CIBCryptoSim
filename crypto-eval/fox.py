import os
import datetime as dt
import pandas as pd
import time
import download_history as dh

CRYPTO_TICKERS = "./data/cryptotickers.csv"
PRICES_DIR = "./data/prices"
PRICES_PREFIX = "coin_"
TRADE_EFFICIENCY = 0.99 #Assume 1% fees
SHORT_EFFICIENCY = (1-TRADE_EFFICIENCY)+1 #Assume 1% fees
STOP_LOSS = 0.80 #Not implemented yet: Sell off an order if it's below 80% of purchase (or above in the case of short)
MIN_VOLUME = 10000 #Don't trade coins below this volume
TIME_DELTA = dt.timedelta(days=1) #Interval between data points

UNIVERSE_START = dt.datetime(2014, 1, 1)
UNIVERSE_END = dt.datetime.now()
BUFFER = 5 #Number of intervals before UNIVERSE_END to cut off

def setup():
  print("Fox Setup")
  start_time = time.time()
  global cryptotickers
  global ticker_data
  global ticker_ids
  global all_price_data

  #Grab tickers from file, stocks are hardcoded in download_history.py for now (will later be in STOCK_TICKERS)
  cryptotickers = pd.read_csv(CRYPTO_TICKERS).set_index('id').to_dict()
  stocktickers = dh.stocks
  #Get csv names and load up dataframes
  ticker_csvs = [f for f in os.listdir(PRICES_DIR) if os.path.isfile(os.path.join(PRICES_DIR, f)) and (f[:5] == "coin_" or f[:6] == "stock_")]
  frames = [pd.read_csv(os.path.join(PRICES_DIR, f)) for f in ticker_csvs]
  ticker_data = {}
  ticker_ids = []

  #Process from stored format to read to use format
  for dataframe in frames:
    dataframe['date'] = pd.to_datetime(dataframe['date'], format="%Y, %m, %d, %H, %M")
    dataframe.set_index('date',inplace=True)
    ticker_id = dataframe['ticker_id'][0]
    ticker_ids.append(ticker_id)
    ticker_data[ticker_id] = dataframe

  #One mega dataframe for ease of use
  all_price_data = pd.concat(frames)

  print("Processed {0} tickers in {1:.3f}s seconds".format(
    len(ticker_ids),
    time.time()-start_time))

class Game():
  def __init__(self, starting_balance, start, end, interval, title="Untitled"):
    #starting_balance - how much in USD
    #start/end - datetime objects
    #interval - datetime.timedelta object (should match data)
    self.balances = {} # ticker_id -> amount owned (in shares/coins, not USD)
    self.balances['USD'] = starting_balance
    self.stop_loss = {}
    self.avg_price = {}
    for ticker in ticker_ids:
      self.balances[ticker] = 0
      self.stop_loss[ticker] = 0
      self.avg_price[ticker] = 0
    self.now = start
    self.start = start
    self.end = end
    self.interval = interval
    self.invested = starting_balance
    self.title = title

    if start < UNIVERSE_START:
      raise ValueError("Start date {0} is before UNIVERSE_START of {1}".format(
        start,UNIVERSE_START))
    if end > UNIVERSE_END - BUFFER*interval:
      raise ValueError("End date {0} is after UNIVERSE_END minus BUFFER".format(
        end))

  #Gives you a dataframe of the crypto tickers sorted by market cap at a specified time
  def crypto_by_marketcap(self, at_time=None):
    if at_time == None: #default is now
      at_time = self.now

    df = all_price_data[all_price_data['asset_type'] == 'crypto']
    by_market_cap = df[(df.index==at_time) & (df.volume > MIN_VOLUME)]\
      .sort_values('market_cap',ascending=False)
    return by_market_cap

  #Gets current price of ticker_id, if not available it will average between nearest 2 previous and future prices
  def price_now(self, ticker_id):
    df = ticker_data[ticker_id]
    use_col = 'adjusted_close'
    if ticker_id in cryptotickers['name']:
      use_col = 'close'
    if self.now in df.index:
      return df[df.index==self.now][use_col][0]
    else: #Can't sell today. Take average of closest price before and after.
      rows = abs(df.index-self.now).argsort()[:2] #Should return neighboring numbers, something like [5,6]
      return df.iloc[rows,][use_col].mean()

  #Calls price_now on each nonzero asset and sums it all up
  def get_portfolio_value(self):
    value = self.balances['USD']
    for ticker_id, amount in self.balances.items():
      if ticker_id == 'USD' or amount == 0:
        continue
      try:
        price_USD = self.price_now(ticker_id)
        value += price_USD*amount*TRADE_EFFICIENCY
      except Exception as ex:
        print(ex)
        print(ticker_id + " | ERROR: Open price not found on " + str(self.now))
        continue

    return value #Returns value in USD

  #Buys an asset at price_now, does not take into account active trading days or whole numbers of shares for stocks
  def buy(self, ticker_id, amount_USD):
    #if amount_USD > self.balances['USD']:
    #  raise ValueError("Purchase failed, insufficient USD balance")

    price_USD = self.price_now(ticker_id)
    amount_ticker = (amount_USD/price_USD)*TRADE_EFFICIENCY
    dprint("Bought {0:.3f} of {1} for {2:.3f} each".format(amount_ticker,ticker_id,price_USD))

    #Update avg price, balances, and set correct stop loss
    entry_value_before = self.balances[ticker_id]*self.avg_price[ticker_id]
    entry_value_after = entry_value_before + amount_USD
    self.balances[ticker_id] += amount_ticker
    self.avg_price[ticker_id] = entry_value_after / self.balances[ticker_id]
    self.balances['USD'] -= amount_USD

    #Stop loss currently takes most recent price and is not stacked
    self.stop_loss[ticker_id] = STOP_LOSS*price_USD

  #Same as buy, but in reverse.
  def sell(self, ticker_id, amount_ticker):
    #if amount_ticker >  self.balances[ticker_id]:
    #  raise ValueError("Sell failed, insufficient {0} balance".format(ticker_id))
    price_USD = self.price_now(ticker_id)*TRADE_EFFICIENCY
    amount_USD = (amount_ticker*price_USD)
    dprint("Sold {0:.3f} {1} for {2:.3f} each".format(amount_ticker,ticker_id,price_USD))

    #Update balances. Avg price and stoploss not affected.
    self.balances[ticker_id] -= amount_ticker
    self.balances['USD'] += amount_USD

  def short_sell(self, ticker_id, amount_USD):
    price_USD = self.price_now(ticker_id)
    amount_ticker = (amount_USD/price_USD)*SHORT_EFFICIENCY #more to cover = fee
    dprint("Short sold {0:.3f} of {1} for {2:.3f} each".format(amount_ticker,ticker_id,price_USD))

    #Update balances and average price. Set stop loss.
    entry_value_before = -1*self.balances[ticker_id]*self.avg_price[ticker_id] #neg*neg*pos = pos
    entry_value_after = entry_value_before + amount_USD*SHORT_EFFICIENCY #more positive
    self.balances[ticker_id] -= amount_ticker
    self.avg_price = entry_value_after / (-1*self.balances[ticker_id])
    self.balances['USD'] += amount_USD
    self.stop_loss[ticker_id] = ((1-STOP_LOSS)+1)*price_USD

  def short_buy(self, ticker_id, amount_ticker):
    price_USD = self.price_now(ticker_id)
    amount_USD = (amount_ticker*price_USD)*SHORT_EFFICIENCY #more to pay back = fee
    dprint("Short bought {0:.3f} of {1} for {2:.3f} each".format(amount_ticker,ticker_id,price_USD))
    self.balances[ticker_id] += amount_ticker
    self.balances['USD'] -= amount_USD


  #To depots/withdraw any assets, including but not limited to USD
  def adjust_balance(self, amount, ticker_id):
    if amount < 0 and amount > self.balances[ticker_id]:
      raise ValueError("Insufficient balance - Withdrawal > Amount on hand")
    self.balances[ticker_id] += amount
    self.invested += amount

  #Current alpha
  def return_rate_now(self):
    return self.get_portfolio_value()/self.invested

def dprint(msg, debug=False):
  if debug:
    print(msg)

def simulate(
  strategy,
  starting_balance,
  start=None,
  end=None,
  interval=dt.timedelta(days=1),
  report_types = ['value'],
  report_freq = 1, #Whole number >0, in terms of game_interval
  verbose = True,
  title="Untitled"):
  #Check for errors
  if report_freq < 1 or type(report_freq) != int:
    raise ValueError("Report Frequency is not aligned with game interval. Make sure report frequency is an int with value > 0")
  print("{0} : Fox simulate start".format(title))
  start_time = time.time()

  #Set default params
  if start == None:
    start = UNIVERSE_START
  if end == None:
    end = UNIVERSE_END-interval*BUFFER

  #Initialize Game and Reporting
  game = Game(starting_balance, start, end, interval, title)
  reports = {'time' : []} #x-axis
  for r in report_types: #y-axes
    reports[r] = []

  #Go through each interval and execute strategy
  interval_num = 0
  while(game.now < end):
    strategy(game)

    #Reporting interval
    if interval_num % report_freq == 0:
      reports['time'].append(game.now)
      if 'value' in report_types:
        reports['value'].append(game.get_portfolio_value())

    #Print statement / progress interval
    if interval_num % 100 == 0:
      print("{0} : {1:.3f}".format(game.now,reports['value'][-1]))

    #Maintain vars
    game.now += interval
    interval_num += 1

  #Sim over, return results
  print("{0} : {1:.3f}".format(game.now,reports['value'][-1]))
  print("Fox simulate completed")
  #print("{0} : Fox simulate completed in {1:.3f}s\n".format(title, time.time()-start_time))
  return (game, reports)
