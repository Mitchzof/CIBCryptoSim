# Download data from all sources with a certain interval
# Interval is specified by one of ['minute','hour','day'] with an
#   aggregate option (>=1) that will resample for the given timeframe
# Data is saved to DATA_FOLDER which is './data' by default
# Prices are saved in DATA_FOLDER/prices/ and factors in DATA_FOLDER/factors/
# Each price/factor is a separate file

# IDs for data lookup are stored in *tickers.csv files
# Crypto tickers to query are in DATA_FOLDER/cryptotickers.csv
# Stock tickers to query are in DATA_FOLDER/stocktickers.csv
# If multiple data sources are being used, storage is in the format
# datasource_<crypto/stock/etc>tickers.txt

#TODOs
#1. Add interval support once non-daily data is available  
#2. Add aggregate support
#3. Add command line args to override defaults

import os
import datetime as dt
import pandas as pd
from time import sleep
import re

DATA_FOLDER = "./data"
STOP_RANK = 1000 #Changes to this var require setting CACHE = False to update
CACHE = False
DO_PRINT = True
ALPHAVANTAGE_API_KEY = 'DNIYDNFQRBRGIT6H'
#Other vars below
#CMC_TICKERLIST
#CMC_TICKERDATA_DIR
#AV_TICKERDATA_DIR

#Phase 0: Ensure necessary directories exist
if not os.path.exists(DATA_FOLDER):
  os.makedirs(DATA_FOLDER)

prices_dir = os.path.join(DATA_FOLDER, 'prices')
if not os.path.exists(prices_dir):
  os.makedirs(prices_dir)

factors_dir = os.path.join(DATA_FOLDER, 'factors')
if not os.path.exists(factors_dir):
  os.makedirs(factors_dir)


#Phase Crypto-1: Gather a list of cryptocurrencies to store id,name,symbol
#TODO - implement try/except for downloads

CMC_TICKERLIST = os.path.join(DATA_FOLDER, 'cryptotickers.csv')
def download_cmc(
  stop_rank, 
  save_loc=CMC_TICKERLIST):
  fetch_url = 'https://api.coinmarketcap.com/v1/ticker/?limit=' + str(stop_rank)
  df = pd.read_json(fetch_url)
  df.to_csv(save_loc, index=False, header=True, columns=['id', 'name', 'symbol'])

def get_cmc_tickers(try_cache=CACHE, path=CMC_TICKERLIST, stop_rank=STOP_RANK):
  if not (try_cache and os.path.exists(path)) and stop_rank is not None:
    download_cmc(stop_rank, save_loc=path)
  
  return pd.read_csv(path)['id'].tolist()

#Phase Crypto-2: Download historical data for each ticker.
#TODO - Append new data and retain older info instead of rewriting

#Price data - CSV with date, asset_type, id, open, high, low, close,
#volume, and possibly additional columns

CMC_TICKERDATA_DIR = os.path.join(DATA_FOLDER, 'prices')

#Fetch data for single coin
def save_cmc_ticker_info(ticker_id, path=CMC_TICKERDATA_DIR, try_cache = CACHE, start='20140101', end=None):
  full_path = os.path.join(CMC_TICKERDATA_DIR, "coin_"+ticker_id+'.csv')
  if try_cache and os.path.exists(full_path):
    return

  if end == None: #Get up to yesterday
    delta = dt.timedelta(days=1)
    yesterday = dt.datetime.now() - delta
    end = yesterday.strftime("%Y%m%d")
  fetch_url = 'https://coinmarketcap.com/currencies/' + ticker_id + \
  '/historical-data/?start={start}&end={end}'.format(
    start = start,
    end = end)

  #Pandas will read the page and return a list of dataframes
  data = pd.read_html(fetch_url, na_values=["-"])
  if len(data) != 1:
    raise ValueError(ticker_id + ' | Error: Got more than one dataframe from reading url')
  df = data[0]
  df['ticker_id'] = ticker_id
  df['asset_type'] = 'crypto'
  #Rename columns to conform with standard, leave market_cap in df as additional column
  df = df.rename(columns={"Open" : "open", "High" : "high", "Low" : "low",
    "Close" : "close", "Volume" : "volume", "Market Cap" : "market_cap",
    "Date" : "date"})
  df['date'] = pd.to_datetime(df['date'])
  df.to_csv(full_path, index=False, header=True, date_format="%Y, %m, %d, %H, %M")

#Fetch data for all coins
def save_all_cmc_ticker_info(ticker_list_path = None, ticker_list=None, wait_secs=None, 
  path=CMC_TICKERDATA_DIR, try_cache=CACHE, start='20140101', end=None):

  if ticker_list == None:
    ticker_list = pd.read_csv(ticker_list_path)['id'].tolist()
  if try_cache == False:
    purge(path, "^coin_")
  n = len(ticker_list)
  for i in range(n):
    if wait_secs:
      sleep(wait_secs)

    ticker = ticker_list[i]
    try:
      save_cmc_ticker_info(ticker, path=path, try_cache=try_cache, start=start, end=end)
      dprint("{0}/{1} : {2}".format(i+1,n,ticker))
    except Error as e:
      print(ticker + " | ERROR fetching/saving data | " +str(e))

#Phase Stocks-1: Hardcoded ticker list (for now)
stocks = ['NVDA','AMD','TSM','VXX']

#Phase Stocks-2: Download historical data for each ticker.
AV_TICKERDATA_DIR = CMC_TICKERDATA_DIR

#Fetch data for single stock
def save_stock_ticker_info(ticker_id, path=AV_TICKERDATA_DIR, try_cache = CACHE, api_key = ALPHAVANTAGE_API_KEY):
  full_path = os.path.join(path, "stock_"+ticker_id+'.csv')
  if try_cache and os.path.exists(full_path):
    return
  fetch_url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={0}&outputsize=full&apikey={1}&datatype=csv"
  df = pd.read_csv(fetch_url.format(ticker_id, api_key))
  df['date'] = pd.to_datetime(df['timestamp'])
  df['asset_type'] = "stock"
  df['ticker_id'] = ticker_id
  df.to_csv(full_path, index=False, header=True, date_format="%Y, %m, %d, %H, %M")

#Fetch data for all stocks
def save_all_stock_ticker_info(ticker_list, wait_secs=0, path=AV_TICKERDATA_DIR, try_cache = CACHE, api_key = ALPHAVANTAGE_API_KEY):
  count = 0
  n = len(ticker_list)
  if try_cache == False:
    purge(path, "^stock_")

  for ticker in ticker_list:
    count += 1
    dprint("{0}/{1} : {2}".format(count, n, ticker))
    sleep(wait_secs) #AV recommends 1 sec between calls, and responds within .5s (25-75% percentile).
    try:
      save_stock_ticker_info(ticker, path=path, try_cache = try_cache, api_key=api_key)
    except Exception as e:
      print(ticker + " | ERROR: " + str(e))

#Helper Functions

#Print with option to turn off
def dprint(msg, do_print = DO_PRINT):
  if do_print:
    print(msg)

#Remove everything in folder with filename matching pattern
#E.g. p="^coin_" gets rid of all coin_ prefixed files
def purge(folder, pattern):
  for f in os.listdir(folder):
    if re.search(pattern, f):
      os.remove(os.path.join(folder,f))

#Execution

if __name__ == "__main__":
  print("Phase 1: Downloading ticker lists...")
  coins = get_cmc_tickers()
  stocks = stocks
  print("Success. Downloaded {0} ticker ids from coinmarketcap".format(len(coins)))
  print("Phase 2A: Downloading coin data...")
  save_all_cmc_ticker_info(ticker_list = coins)
  print("Phase 2B: Fetching stock data...".format(len(stocks)))
  save_all_stock_ticker_info(stocks)





