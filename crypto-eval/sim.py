import fox
import datetime as dt
import matplotlib.pyplot as plt
import chart
import math

def coin_static_hold(start_rank, stop_rank, weigh_by_cap = False):
	#Generates a top start# thru stop# hodl strategy
	#Start = zero indexed, inclusive
	#Stop = zero indexed, not inclusive
	#weigh_by_cap = whether to by market cap (T) or weigh equally (F)
	#E.g. static_hold(0,10) returns the top 10
	def result(game):
		if(game.now == game.start): #Only balance once
			market = game.crypto_by_marketcap()
			print(market['ticker_id'].tolist())
			n = stop_rank-start_rank
			coins = market['ticker_id'].tolist()[start_rank:stop_rank]
			if weigh_by_cap:
				total_cap = market['market_cap'].sum()
				market['weight'] = market['market_cap']/total_cap
				weights = market['weight'].tolist()[start_rank:stop_rank]
			else:
				weights = [1/n]*n
			start_money = game.balances['USD']
			allotments = [int(x*start_money) for x in weights] #int() rounds DOWN
			for i in range(len(coins)):
				coin_id = coins[i]
				allotment = allotments[i]
				game.buy(coin_id, allotment)

	return result

def stock_static_hold(tickers, w=None, short=False):
	#Holds a portfolio of stocks with given weights (default = equal weighting)
	def result(game):
		#Calculate equal weights if nothing already set
		n = len(tickers)
		if w == None:
			weights = [1/n]*n
		else:
			weights = w
		#Calculate USD amount to purchase
		start_money = game.balances['USD']
		allotments = [int(x*start_money) for x in weights]
		#Double check
		if sum(allotments) > start_money:
			raise ValueError("Bad Weights: Sum of allotments > starting balance")
		#Only balance once
		if(game.now == game.start):
			for i in range(len(tickers)):
				ticker = tickers[i]
				allotment = allotments[i]
				if not short:
					game.buy(ticker, allotment)
				else:
					game.short_sell(ticker, allotment)
	return result

def create_ranked(
	start_rank, #Zero indexed, inclusive
	stop_rank, #Zero indexed, exclusive
	rebalance_ratio = 1.2, 
	stop_loss = 0.8, 
	rebalance_interval=dt.timedelta(days=7)):

	def ranked(game):
		epoch = dt.datetime.utcfromtimestamp(0)
		seconds_since_epoch = (game.now-epoch).total_seconds()
		seconds_in_interval = rebalance_interval.total_seconds()
		if seconds_since_epoch % seconds_in_interval == 0:
			market = game.crypto_by_marketcap()
			coins_of_interest = market['ticker_id'].tolist()[start_rank:stop_rank]
			target_per_coin = math.floor(100*game.get_portfolio_value()/len(coins_of_interest))/100.0 #floor to safe divide to lowest cent USD
			
			#Rebalance and stop loss
			for coin, amount in game.balances.items():
				if amount <= 0 or coin == 'USD':
					#Is short or USD, skip
					continue
				coin_USD = game.price_now(coin)*game.balances[coin]
				ratio = coin_USD/target_per_coin
				if ratio > rebalance_ratio:
					extra = (1-(1/ratio))*game.balances[coin]
					game.sell(coin, extra)
				elif ratio < stop_loss:
					game.sell(coin, amount) #sell all of it!

			for coin in coins_of_interest:
				if coin == 'USD' or game.balances[coin] < 0:
					#Is short or USD, skip
					continue

				owned_USD = game.balances[coin]*game.price_now(coin)
				ratio = owned_USD/target_per_coin
				if ratio < 1:
					purchase_USD = (1-ratio)*target_per_coin
					purchase_USD = math.floor(100*purchase_USD)/100.0 #safety
					game.buy(coin, purchase_USD)

	return ranked






fox.setup()
start_money = 10000
start_date = dt.datetime(2017,8,1)


top_10eq = coin_static_hold(0,10)
g,r = fox.simulate(top_10eq, start_money, start=start_date, title='Top 10 Crypto (Static)')
hodl_nvda = stock_static_hold(['NVDA'],w=[1])
g2,r2 = fox.simulate(hodl_nvda, start_money, start=start_date, title='NVDA')
short_vxx = stock_static_hold(['VXX'], w=[1], short=True)
g3, r3 = fox.simulate(short_vxx, start_money, start=start_date, title='Short VXX')
hodl_voo = stock_static_hold(['VOO'],w=[1])
g4, r4 = fox.simulate(hodl_voo, start_money, start=start_date, title='SP500 (VOO)')
top_10eq_rb = create_ranked(0,10)
g5, r5 = fox.simulate(top_10eq_rb, start_money, start=start_date, title='Top 10 Crypto (Weekly re.)')
shit_150_500eq = coin_static_hold(150,500)
g6, r6 = fox.simulate(shit_150_500eq, start_money, start=start_date, title='Crypto 150-500 (Static)')
shit_150_500eq_rb = create_ranked(150,500)
g7, r7 = fox.simulate(shit_150_500eq_rb, start_money, start=start_date, title='Crypto 150-500 (Weekly re.)')

reports = [r,r2,r3,r4,r5,r6,r7]
titles = [g.title, g2.title, g3.title, g4.title, g5.title, g6.title,g7.title]
returns = chart.returns_df(reports, titles)
returns.plot(grid=True, title='Normalized Returns')
returns.plot(grid=True, logy=True, title='Normalized Returns (Log Scale)')
plt.show()
alpha_m = chart.alpha_df(returns, g4.title)
alpha_m.plot(grid=True, title='Monthly Alpha (vs SP500)')
plt.show()
alpha_a = chart.alpha_df(returns, g4.title, resample='A')
alpha_a.plot(grid=True, title='Yearly Alpha (vs SP500)')
plt.show()
