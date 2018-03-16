import fox
import datetime as dt
import pandas as pd
import ccxt

def live_do_nothing(game):
	print("="*20)
	print("Do-nothing execute!")
	print("-"*10)
	print("Balances:")
	print(game.balances)
	print("-"*10)
	print("Current Top 5 Crypto")
	top5_df = game.crypto_by_market_cap(1,5)
	print(top5_df['symbol'])
	print("-"*10)
	print("Coins ranked 150-300 and on Binance")
	df_low = game.crypto_by_market_cap(150,300)
	df_low['pair'] = df_low['symbol']+'/BTC'
	df_low['on_binance'] = df_low['pair'].apply(on_binance)
	print(df_low[df_low['on_binance'] == True][['rank','symbol']])
	print("="*20)

binance = ccxt.binance()
m = binance.load_markets()
def on_binance(pair):
	return pair in binance.symbols

update_interval = dt.timedelta(minutes=1)
strat_interval = dt.timedelta(minutes=5)

fox.live_setup()
fox.live_trade(live_do_nothing, fox.exchange_objs,{}, 
	update_interval=update_interval, strat_interval=strat_interval)

