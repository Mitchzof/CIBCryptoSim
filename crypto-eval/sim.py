import fox
import datetime as dt
import matplotlib.pyplot as plt
import chart
fox.setup()

def coin_static_hold(start_rank, stop_rank, weigh_by_cap = False):
	#Generates a top start# thru stop# hodl strategy
	#Start = zero indexed, inclusive
	#Stop = zero indexed, not inclusive
	#weigh_by_cap = whether to by market cap (T) or weigh equally (F)
	#E.g. static_hold(0,10) returns the top 10
	def result(game):
		if(game.now == game.start): #Only balance once
			market = game.crypto_by_marketcap()
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

start_money = 10000
start_date = dt.datetime(2017,1,1)


top_10eq = coin_static_hold(0,10)
g,r = fox.simulate(top_10eq, start_money, start=start_date, title='Top 10 Crypto')
hodl_nvda = stock_static_hold(['NVDA'],w=[1])
g2,r2 = fox.simulate(hodl_nvda, start_money, start=start_date, title='NVDA')
short_vxx = stock_static_hold(['VXX'], w=[1], short=True)
g3, r3 = fox.simulate(short_vxx, start_money, start=start_date, title='Short VXX')
hodl_voo = stock_static_hold(['VOO'],w=[1])
g4, r4 = fox.simulate(hodl_voo, start_money, start=start_date, title='SP500 (VOO)')

reports = [r,r2,r3,r4]
titles = [g.title, g2.title, g3.title, g4.title]
returns = chart.returns_df(reports, titles)
returns.plot(grid=True, title='Normalized Returns')
returns.plot(grid=True, logy=True, title='Normalized Returns (Log Scale)')
plt.show()
alpha_m = chart.alpha_df(returns, g4.title)
alpha_m.plot(grid=True, title='Monthly Alpha')
alpha_a = chart.alpha_df(returns, g4.title, resample='A')
print(alpha_a)
