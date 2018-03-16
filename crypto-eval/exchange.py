# This is a helper file for integrating live exchange functionality into the backtester
# Because exchange APIs change, we decided to make this file separate to keep things modular.

import ccxt
import time
import json
import urllib.request

#For security purposes, store exchange info as keys in a separate file that are NOT in the github repo
#Key info is stored as a json object with the format:
#  {exchanges: [list of exchange objs]},
#  each exchange obj is a json object: {"ccxt_id" : "binance", "apikey" : "1234", "secret": "4321"}
#Python loads these into an easy to use dictionary!

KEYS_FILEPATH = 'key.json'

def load_keys(filepath=KEYS_FILEPATH):
	with open('key.json','r') as f:
		keys = json.load(KEYS_FILEPATH)
	return keys


# Make ccxt exchange objects
# Input: keys_data, e.g. loaded json file
# Output: dictionary of {ccxt_id : ccxt exchange object}
# Caution! Keys exposed in exchange objects
def make_exchange_objs(keys_data):
	exchanges = {}
	for data in keys_data['exchanges']:
		exchange = getattr(ccxt, data['ccxt_id'])
		exchange.apiKey = data['apikey']
		exchange.secret = data['secret']
		exchanges[data['ccxt_id']] = exchange
	
	# Set custom fields inside exchange object
	# delim: Seperator between symbols, e.g. the '/' in BTC/USD
	# base: The base currencies all trades are made in, e.g. the 'USD' in BTC/USD
	for k in exchanges.keys():
		exchange = exchanges[k]
		exchange.delim = '/'
		exchange.base = 'BTC' #Binance and others typically trade in BTC
	return exchanges

# Wrapper function to get total balance from exchange
# Used to calculate portfolio value
# Input: CCXT exchange object, kind='total'/'free'/'used'
# Output: Dict of all nonzero balances in the form of {coin : value}
# Caution! Don't use kind='total' for any buy/sell/rebalance since this ignores 'used'
def get_balance(exchange_obj, kind):
	bal = exchange_obj.fetch_balance()[kind]
	res = {}
	for curr,val in bal.items():
		if val > 0:
			res[curr] = val
	return res

# Combines get_balance for a list of exchanges into one aggregate dict
# Used to calculate portfolio value
# Input: List of CCXT exchange objects
# Output: Dict of all nonzero balances in the form of {coin :  value}
# Caution! Don't use kind='total' for any buy/sell/rebalance since this ignores 'used'
def get_balances(exchange_objs, kind='total'):
	master_bal = {}
	for e in exchange_objs:
		if e.base != 'BTC':
			raise NotImplementedError("Non-BTC base pairs not supported yet")
		bal = get_balance(e, kind)
		for curr,val in bal.items():
			if curr not in master_bal:
				master_bal[curr] = 0
			master_bal[curr] += val
	return master_bal

# Gets all open order ids on an exchange obj
# To be used for closing all open orders before buy/sell/rebalance
# Input: CCXT exchang eobject
# Output: List of (order_id, symbol)
def get_open_order_ids(exchange_obj):
	used_bal = get_balance(exchange_obj, 'used')
	order_ids = []
	for curr in used_bal.keys():
		pair = curr + exchange_obj.delim + exchange_obj.base
		orders = exchange_obj.fetch_open_orders(pair)
		for o in orders:
			order_ids.append((o['id'],pair))
	return order_ids

# Attempts to cancel all orders passed in
# Prints warning if any id has an exception
# Used on all open orders before buy/sell/rebalance
# Input: Exchange obj, List of (order_id, symbol) e.g. [('1234','XRP/BTC')]
# Output: List of success/fail booleans e.g. [True, False, True, ...]
# Caution! OrderNotFound exception can happen on already closed and already cancelled orders
def cancel_orders(exchange_obj, order_ids):
	out = []
	for o in order_ids:
		order_id = o[0]
		order_pair = o[1]
		try:
			exchange_obj.cancel_order(order_id, order_pair)
			out.append(True)
		except Exception as ex:
		    template = "WARN | An exception of type {0} occurred. Arguments:\n{1!r}"
		    message = template.format(type(ex).__name__, ex.args)
		    print(message)
		    out.append(False)
	return out	    

# Helper function that gets current BTC/USD from crytocompare's aggregate exchange data
# ESTIMATE ONLY!!!
# Input: None
# Output: Float value of USD for 1 BTC, e.g. 9265.55
def btc_to_usd():
	link = 'https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD'
	with urllib.request.urlopen(link) as url:
		btcusd = json.loads(url.read().decode())
	return btcusd['USD']

# Gets order book from exchange for symbol/base
# Input: exchange object, string pair (e.g. 'XRP/BTC'),
# 		 order_depth = number of orders in book to fetch,
#        side = 'bid'/'ask'/'avg'
# Output: The amount of symbol for 1 base
def price(exchange_obj, pair, side, order_depth=None):
	if order_depth == None:
		orderbook = exchange_obj.fetch_order_book(pair)
	else:
		orderbook = exchange_obj.fetch_order_book(pair, order_depth)

	if side == 'bid': # Bids to buy
		total_val = sum([x[0]*x[1] for x in orderbook['bids']])
		total_amt = sum([x[1] for x in orderbook['bids']])
		bid_avg = total_val/total_amt
		return bid_avg
	elif side == 'ask': # Asks to sell
		total_val = sum([x[0]*x[1] for x in orderbook['asks']])
		total_amt = sum([x[1] for x in orderbook['asks']])
		ask_avg = total_val/total_amt
		return ask_avg
	else:
		total_val = sum([x[0]*x[1] for x in oderbook['bids']+orderbook['asks']])
		total_amt = sum([x[1] for x in orderbook['bids']+orderbook['asks']])
		avg = total_val/total_amt
		return avg

# Wrapper function that executes a market buy on the exchange
# Input: exchange object, pair (e.g. 'XRP/BTC'), amount_base (e.g. BTC), wait for confirmation (seconds)
# Output: order success/fail
# Need to test: buying with insufficient balance, what kind of error? what happens to order? how to fix?
def exchange_market_buy(exchange_obj, pair, amount_base, wait=3):
	symbol_to_base = price(exchange_obj, pair, 'ask')
	amount_symbol = int(1000000*amount_base/symbol_to_base)/1000000
	try:
		order = exchange_obj.create_market_buy_order(pair, amount_base)
	except ccxt.insufficientFunds:
		print('{0},{1} - Market buy failed, insufficient funds. Nothing was purchased.'.format(
			exchange_obj.id, pair))
		return False

	if order['status'] != 'closed':
		time.sleep(wait)
		return exchange_obj.fetch_order(order['id'])['status'] == 'closed'
	return True

# Same thing as sell but in the opposite direction
def exchange_market_sell(exchange_obj, pair, amount_coin, wait=3):
	try:
		order = exchange_obj.create_market_sell_order(pair, amount_coin)
	except ccxt.insufficientFunds:
		print('{0},{1} - Market sell failed, insufficient funds. Nothing was sold.'.format(
			exchange_obj.id, pair))
		return False

	if order['status'] != 'closed':
		time.sleep(wait)
		return exchange_obj.fetch_order(order['id'])['status'] == 'closed'
	return True

#Convert from symbol to default pair for exchange
def sym_to_pair(symbol, exchange_obj):
	return symbol + exchange_obj.delim + exchange_obj.base


	









