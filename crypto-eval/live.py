import fox
import datetime as dt
import pandas as pd
import ccxt
import exchange

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

def create_ranked(
	start_rank, # 1-indexed, inclusive
	stop_rank, # 1-indexed, inclusive
	rebalance_ratio=1.2, # Don't adjust positions below this
	stop_loss=0.75, # Sell positions below this and blacklist them for 2 rebalance intervals
	blacklist={}, # dict of coins and for how long to blacklist them e.g. { 'XRP' : dt.datetime(2019,1,1)}
	rebalance_interval=dt.timedelta(days=1), #execute strat
	):
	def strat(game):
		print("="*20)
		print("Ranked Execute!")

		# Get coins of interest and targets per coin
		df = game.crypto_by_market_cap(start_rank, stop_rank)
		df['pair'] = df['symbol']+'/BTC'
		df['on_binance'] = df['pair'].apply(on_binance)
		coins_of_interest = list(df[df['on_binance'] == True]['symbol'])
		now = dt.datetime.now()
		for coin in coins_of_interest:
			if coin in blacklist and blacklist[coin] > now:
				coins_of_interest.remove(coin)
			elif coin in blacklist and blacklist[coin] <= now:
				del blacklist[coin] #coin has passed expire time and is okay again
		
		print("-"*10)	
		print('Coins of interest:\n')
		print(coins_of_interest)

		target_per_coin = game.get_portfolio_value_btc()/len(coins_of_interest)

		print("-"*10)
		print('Target btc per coin: {:.5f}\n'.format(target_per_coin))

		print("-"*10)
		print('Ratios for each coin:\n')
		# Do rebalance and stop_loss
		bals = game.balances #update already occured, this is up to date
		for symbol, amount_symbol in bals.items():
			if symbol == 'BTC':
				continue
			amount_btc = game.price_now(symbol)*amount_symbol
			ratio = amount_btc/target_per_coin
			print(f"{symbol} | {ratio}")
			if ratio > rebalance_ratio: # Too much of symbol
				extra = (1-(1/ratio))*amount_symbol
				s = game.sell(symbol, extra)
				print('SELL | Sym: {} | Amount sym: {:.4f} | Success: {}'.format(symbol,extra,s))
			elif ratio < stop_loss: # Stop loss triggered, sell it all and add to blacklist
				s = game.sell(symbol, amount_symbol)
				print('SELL | Sym: {} | Amount sym: {:.4f} | Success: {}'.format(symbol,amount_symbol,s))
				blacklist[coin] = now + rebalance_interval*2

		# Make purchases
		for coin in coins_of_interest:
			if coin == 'BTC' or coin in blacklist:
				#Base currency should never be in here, but gets a pass just in case
				#Skip blacklisted coins
				continue

			if coin in bals:
				amount_coin = bals[coin]
			else:
				amount_coin = 0

			amount_btc = amount_coin*game.price_now(coin)
			ratio = amount_btc/target_per_coin
			print(f'{coin} | Amount coin held: {amount_coin} | Amount btc worth: {amount_btc}')
			print(f'Ratio: {ratio}')
			if ratio < 0.99: # 1% tolerance, e.g. a ratio of 0.995 gets treated as >=1
				purchase_btc = (1-ratio)*target_per_coin
				print('Amount of btc worth of coin to buy: '+str(purchase_btc))
				print('ATTEMPT BUY | Sym: {} | Amount sym: {}'.format(coin,amount_coin))
				b = game.buy(coin, purchase_btc)
				print(b)

	return strat


binance = ccxt.binance()
m = binance.load_markets()
def on_binance(pair):
	return pair in binance.symbols

update_interval = dt.timedelta(minutes=1)
strat_interval = dt.timedelta(minutes=5)

rank_strat = create_ranked(150,300)

fox.live_setup()
fox.live_trade(rank_strat, fox.exchange_objs,{}, 
	update_interval=update_interval, strat_interval=strat_interval)

