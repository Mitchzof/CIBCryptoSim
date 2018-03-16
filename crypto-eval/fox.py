import os
import datetime as dt
import pandas as pd
import time
import download_history as dh
import exchange
import logging

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
BUFFER = 10 #Number of intervals before UNIVERSE_END to cut off

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

class Game_live():
  # WORK IN PROGRESS
  def __init__(self, exchange_objs, coin_to_exchange, start, interval, leniency=0.99):
    #exchange_objs - ccxt exchange objects
    #coin_to_exchange - dict of which exchange to use for each coin {coin : exchange_obj}
    #interval - update frequency to fetch new data, typically not the same as the strat interval!
    #start - time at which the script was started (if not <10s from now, a reboot occurred)
    #leniency - float in range (0,1] that is the "wiggle room" for any time related activity
      #e.g. 0.99 leniency --> 14 minutes over 24h, 3s over 5min. 
    self.balances_btc = exchange.get_balances(exchange_objs)
    self.stop_loss = {} # {coin_id : price_USD}
    self.avg_price = {} # {coin_id : price_USD}

    self.now = dt.datetime.now()
    self.start = start
    self.interval = interval
    self.last_update = dt.datetime.now()
    if self.now-start > dt.timedelta(seconds=10):
      #Start was more than 10 seconds ago, probably a reboot.
      #TODO: HANDLE REBOOTS

  def check_update(self):
    now = dt.datetime.now()
    time_diff = now-self.last_update
    lower_bound = interval*leniency #e.g. 5min*0.99=4min,57sec
    if time_diff > lower_bound:
      print(r"UPDATE NEEDED")

  #Dataframe of coinmarketcap data sorted by marketcap
  def crypto_by_marketcap(self, start_rank, stop_rank):
    #Start rank - Starts at 1, inclusive
    #Stop rank - The bigger number, inclusive
    tickers_url = "https://api.coinmarketcap.com/v1/ticker/?start={0}&limit={1}"
    tickers_url = tickers_url.format(start_rank,stop_rank-start_rank+1)
    df = pd.read_json(tickers_url)
    # >>> df.columns
    # Index(['24h_volume_usd', 'available_supply', 'id', 'last_updated',
    #        'market_cap_usd', 'max_supply', 'name', 'percent_change_1h',
    #        'percent_change_24h', 'percent_change_7d', 'price_btc', 'price_usd',
    #        'rank', 'symbol', 'total_supply'],
    #       dtype='object')
    return df
    
  #Live price of symbol (e.g. 'XRP')
  def price_now(self, symbol):
    exchange_obj = coin_to_exchange[symbol]
    pair = symbol + exchange_obj.delim + exchange_obj.base
    p = exchange.price(exchange_obj, pair, side='avg')
    return p

  #Current value in BTC, estimate only for reporting, total funds held
  def get_portfolio_value_btc(self):
    self.check_update()
    total_value = 0
    for coin, value in self.balances_btc.items():
      total_value += value
    return total_value

  #Current value in USD, estimate only for reporting, total funds held
  def get_portfolio_value_usd(self):
    self.check_update()
    btc_usd = exchange.btc_to_usd()
    return btc_usd*get_portfolio_value_btc()

  #Attempt a market buy
  def buy(self, symbol, amount_base):
    exchange_obj = coin_to_exchange(symbol)
    pair = exchange.sym_to_pair(symbol, exchange_obj)
    attempt = exchange.exchange_market_buy(exchange_obj, pair, amount_base)
    return attempt

  #Attempt a market sell
  def sell(self, symbol, amount_symbol, retry=0):
    exchange_obj = coin_to_exchange(symbol)
    pair = exchange.sym_to_pair(symbol, exchange_obj)
    attempt = exchange.exchange_market_sell(exchange_objs, pair, amount_symbol)
    return attempt

    #if amount_ticker >  self.balances[ticker_id]:
    #  raise ValueError("Sell failed, insufficient {0} balance".format(ticker_id))
    price_USD = self.price_now(ticker_id)*TRADE_EFFICIENCY
    amount_USD = (amount_ticker*price_USD)
    dprint("Sold {0:.3f} {1} for {2:.3f} each".format(amount_ticker,ticker_id,price_USD))

    #Update balances. Avg price and stoploss not affected.
    self.balances[ticker_id] -= amount_ticker
    self.balances['USD'] += amount_USD

  def short_sell(self, ticker_id, amount_USD):
    raise NotImplementedError('Shorting is not supported yet')

  def short_buy(self, ticker_id, amount_ticker):
    raise NotImplementedError('Shorting is not supported yet')

  def adjust_balance(self, amount, ticker_id):
    raise NotImplementedError('Programmatic deposit/withdrawal is not supported yet')


# Helper Functions
def dprint(msg, debug=False):
  if debug:
    print(msg)

# Main sim loop for backtests
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

# Main loop for live trading
def live_trade(
  strategy,
  exchange_objs,
  coin_to_exchange,
  start=None,
  update_interval=dt.timedelta(hours=1), #granularity for small tasks like checking stoplosses and reporting
  strat_interval=dt.timedelta(days=1), #granularity for strategy execution
  report_types = ['value'],
  report_freq = 1, #whole number multiple in terms of update interval
  verbose = True,
  title="Untitled"
  ):

  ## Error check ##

  # Check report interval
  if report_freq < 1 or type(report_freq) != int:
    raise ValueError("Report Frequency is not aligned with update interval. Make sure report frequency is an int with value > 0")
  print("{0} : Fox live trading start".format(title))

  # Check exchange auth/connect by attempting to fetch balance
  # TODO: confirm access to trade and not just read only
  for exchange_obj in exchange_objs:
    exchange_obj.fetch_balance()


  ## Set default params ##

  # Start time
  if start == None:
    start = dt.datetime.now() + dt.timedelta(seconds = 5)


  ## Initialize Game and Reporting ##

  game = Game_live(exchange_objs, coin_to_exchange, start, update_interval)

  ## Main Loop ##
  while True:
    # Determine when to next update/strat/both 
    next_update_s, next_update_dt = get_next_interval(start, update_interval)
    next_strat_s, next_strat_dt = get_next_interval(start, strat_interval)
    sleep_time = min(next_update_s, next_strat_s)
    print("Next Update Execution: {0}".format(next_update_dt))
    print("Next Strategy Execution: {0}".format(next_strat_dt))
    print("Sleeping for {0}".format(dt.timedelta(seconds=sleep_time)))

    next_dt = min(next_update_dt, next_strat_dt)
    strat_is_next = (next_dt == next_strat_dt)
    update_is_next = (next_dt == next_update_dt)
    time.sleep(sleep_time)

    #Run code for update/strat/both
    if update_is_next:
      print("{0} | Update")
      game.check_update()
    if strat_is_next:
      print("{0} | Strategy")
      strategy(game)
      
  print("Main loop terminated. Trading has halted.")

# Given a start datetime and a timedelta interval, calculate when the next interval starts
# Return the seconds until the next interval and a datetime of when it occurs
def get_next_interval(start, interval):
  now = dt.datetime.now()
  time_diff = (now-start).total_seconds()
  interval_s = interval.total_seconds()
  next_interval_s = interval_s - (time_diff % interval_s)
  next_interval_dt = now + dt.timedelta(seconds=next_interval_s)
  return (next_interval_s, next_interval_dt)

# Returns True if var_time is close enough to fixed_time
# Inputs: var_time (datetime) the variable time
#         fixed_time (datetime) the time to check against
#         interval (timedelta) used for leniency
#         leniency_float (float) how close var_time must be to fixed_time
#             e.g. leniency of 90% --> can be +/- 0.1 intervals away 
def time_within_tolerance(var_time, fixed_time, interval, leniency_float):
  leniency = interval*(1-leniency_float) #can be +/- this much away
  lower_bound = fixed_time-leniency
  upper_bound = fixed_time+leniency
  return var_time > lower_bound and var_time < upper_bound
