# Finds exchanges for top coins
# Work saved here so this can be done again with less effort
# This is a super hacky script. Beware.
# Other notes:
# 	# Coinmarketcap doesn't seem to have data on decentralized exchanges 
#   # like etherdelta, but ccxt doesn't support it either. 
#   # Bitmex is supported by ccxt but not coinmarketcap. Also interesting.

import pandas as pd
from pprint import pprint
import ccxt
MIN_VOL = 10000
BASE_CURRS = ['/USD','/BTC','/ETH']

start = 150
stop = 500
tickers_url = "https://api.coinmarketcap.com/v1/ticker/?start={0}&limit={1}"
###
tickers_url = tickers_url.format(start,stop-start+1)

# Match string for trading pairs
# '(/BTC|/USD)$' matches strings that end with /BTC or /USD (/USDT will not match) 
match_str = '('+'|'.join(BASE_CURRS)+')$' 

df = pd.read_json(tickers_url)
coin_ids = df['id']

#Exchanges for a particular coin (with /BTC or /USD and MIN VOLUME)
exchanges = {} # {coin : [exchange1, exchange2, ...]}

#Coins for each exchange and the total number of coins the exchange has (with /BTC or /USD and MIN VOLUME)
ex_coins = {} # {exchange : {coin1 : True, coin2: True, ..., count: 150}}

#Coins that will not be traded due to lack of trading pair / volume 
#Note: If using BTC as base, most likely it's too low volume 
empty = []

#Iterate through all the coins and get data on their markets
count=0
for coin_id in coin_ids:
	print('({0}/{1}) {2}'.format(start+count,stop,coin_id))
	count += 1
	# Fetch url, clean volume columns to be 1,234 instead of '$1,234'
	# Note: some info will have on more '*'s in it, which means it should be ignored
	m_df = pd.read_html('https://coinmarketcap.com/currencies/{0}/#markets'.format(coin_id))[0]
	m_df['Clean Vol'] = pd.to_numeric(m_df['Volume (24h)'].str.replace('[$,]',''), errors='coerce')
	
	# Filter out the shit
	sources = m_df[(m_df['Clean Vol'] > MIN_VOL) & (m_df['Pair'].str.contains(match_str))]['Source']
	exchanges[coin_id] = list(sources)
	if len(sources) == 0:
		empty.append(coin_id)

	# Add relevant data
	for s in sources:
		if s not in ex_coins:
			ex_coins[s] = {}
			ex_coins[s]['count'] = 0
		if coin_id not in s:
			ex_coins[s][coin_id] = True
			ex_coins[s]['count'] += 1

# Dict with highest 'count' in dict of dicts
def most_popular(d):
	max_key = None
	max_val = 0
	for key in d.keys():
		if hasattr(ccxt, key.lower()) == False:
			continue
		if d[key]['count'] > max_val:
			max_val = d[key]['count']
			max_key = key
	return (max_key, max_val)

# Remove blacklist coins and update count
def new_count(d,blacklist):
	for coin in list(d.keys()):
		if coin in blacklist:
			try:
				del d[coin]
			except Exception:
				continue
	d['count'] = len(d.keys())-1 #minus one for count

print(ex_coins)
top_names = []
top_counts = []
top_coins = []
preffered_ex = ['Cryptopia','Poloniex','Bittrex','Binance'] #higher priority towards the end

# Filter out bad exchanges
raw_data = dict(ex_coins)
data = {}
for d in raw_data.keys():
	if hasattr(ccxt,d.lower()):
		data[d] = raw_data[d]

# Main loop
for i in range(len(data.keys())):
	# Pick from preffered first, then anything ccxt supports
	if len(preffered_ex) > 0:
		exchange = preffered_ex.pop()
		count = data[exchange]['count']
	else:
		exchange, count = most_popular(data)
	# Break loop once out of exchanges or count becomes too low
	if exchange == None or count < 5:
		break

	blacklist = data[exchange].keys()
	top_names.append(exchange)
	top_counts.append(count)
	top_coins.append(list(blacklist))
	blacklist = {x:True for x in blacklist}
	del data[exchange]
	for d in data:
		new_count(data[d],blacklist)

# Analysis
print('Overview:')
for i in range(len(top_names)):
	print("{0} - {1}".format(top_names[i],top_counts[i]))

print('Specific coins:')
for i in range(len(top_names)):
	print("{0} - {1}".format(top_names[i],top_coins[i]))

# Previous results
# March 13, 150-500

# Binance - 38
# Bittrex - 75
# Poloniex - 2
# Cryptopia - 28
# Cobinhood - 1
# Kucoin - 33
# OKEx - 23
# HitBTC - 13
# Liqui - 9
# Bibox - 7
# CoinExchange - 6
# Huobi - 4
# Livecoin - 3
# CoinEgg - 2
# YoBit - 2
# Tidex - 1
# Qryptos - 1

# Binance - ['count', 'adx-net', 'ethlend', 'poa-network', 'bluzelle', 'sonm', 'simple-token', 'amber', 'vibe',
#			 'red-pulse', 'wings', 'ripio-credit-network', 'eidoo', 'singulardtv', 'blockmason', 'ins-ecosystem',
#			 'bread', 'wabi', 'appcoins', 'cybermiles', 'viacoin', 'airswap', 'etherparty', 'modum', 'gifto', 
#			 'centra', 'district0x', 'lunyr', 'tierion', 'viberate', 'triggers', 'blox', 'everex', 'monetha', 
#			 'aeron', 'yoyow', 'agrello-delta', 'moeda-loyalty-points', 'oax']
# Bittrex - ['feathercoin', 'ion', 'bitbay', 'peercoin', 'einsteinium', 'quantum-resistant-ledger', 'burst', 
#			 'library-credit', 'cloakcoin', 'counterparty', 'gulden', 'groestlcoin', 'aeon', 'crown', 'adtoken',
#			 'synereo', 'bean-cash', 'decent', 'humaniq', 'cofound-it', 'voxels', 'potcoin', 'sibcoin', 'unikoin-gold',
#			 'shift', 'mercury', 'steem-dollars', 'zclassic', 'numeraire', 'iocoin', 'diamond', 'vericoin', 
#			 'blackcoin', 'elastic', 'guppy', 'faircoin', 'blocktix', 'trust', 'florincoin', 'gridcoin', 'expanse', 
#		     'omni', 'hempcoin', 'firstblood', 'solarcoin', 'radium', 'monetaryunit', 'bitsend', 'clams', 'incent', 
#			 'energycoin', 'rubycoin', 'swarm-city', 'databits', 'auroracoin', 'okcash', 'myriad', 'lomocoin', 
#			 'musicoin', 'golos', 'neoscoin', 'patientory', 'transfercoin', 'nexium', 'syndicate', 'nubits', 
#			 'foldingcoin', 'dynamic', 'tokes', 'circuits-of-value', 'stealthcoin', 'internet-of-people', 'bitcrystals',
#			 'pinkcoin', 'sphere', 'dopecoin', 'count']
# Poloniex - ['pascal-coin', 'primecoin', 'bitmark', 'count']
# Cryptopia - ['spankchain', 'xtrabytes', 'unobtanium', 'flash', 'zap', 'ormeus-coin', 'cappasity', 'deeponion', 
#			   'mintcoin', 'mothership', 'zoin', 'nolimitcoin', 'posw-coin', 'divi', 'alis', 'mybit-token', 
#	    	   'universal-currency', 'investfeed', 'phore', 'everus', 'spectrecoin', 'gobyte', 'asiacoin', 'decent-bet',
#			   'bismuth', 'blockcat', 'linda', 'luxcoin', 'dubaicoin-dbix', 'count']
# Cobinhood - ['universa', 'cobinhood', 'count']
# Kucoin - ['telcoin', 'jibrel-network', 'iot-chain', 'deepbrain-chain', 'utrust', 'kickico', 'data', 'decision-token',
#		    'trinity-network-credit', 'qlink', 'medical-chain', 'blockport', 'zeepin', 'latoken', 'swissborg', 
#	   	    'suncontract', 'iht-real-estate-protocol', 'selfkey', 'odyssey', 'dadi', 'restart-energy-mwat', 'covesting',
#		    'canyacoin', 'carvertical', 'snovio', 'chronobank', 'coinfi', 'hacken', 'axpire', 'ebtcnew', 'solaris', 
#			'sportyco', 'bounty0x', 'cargox', 'count']
# OKEx - ['smartmesh', 'naga', 'delphy', 'refereum', 'game', 'bankex', 'datum', 'internet-node-token', 'qunqun', 
#		  'trade-token', 'hi-mutual-society', 'swftcoin', 'encrypgen', 'all-sports', 'true-chain', 'olympus-labs', 
#	   	  'prochain', 'hydro-protocol', 'primas', 'measurable-data-token', 'oneroot-network', 'worldcore', 'aventus', 
#		  'leverj', 'count']
# HitBTC - ['c20', 'metaverse', 'indahash', 'hive-project', 'presearch', 'attention-token-of-media', 'paragon', 
#	   		'blackmoon', 'lamden', 'icos', 'ixledger', 'hackspace-capital', 'airtoken', 'life', 'count']
# Liqui - ['melon', 'mobilego', 'taas', 'wepower', 'tokencard', 'nimiq', 'propy', 'neumark', 'stox', 'mysterium', 'count']
# Bibox - ['medibloc', 'bibox-token', 'bottos', 'cpchain', 'bloomtoken', 'bitclave', 'change', 'spectre-utility', 'count']
# CoinExchange - ['experience-points', 'eccoin', 'uquid-coin', 'bitconnect', 'espers', 'elixir', 'b3coin', 'count']
# Huobi - ['medishares', 'linkeye', 'stk', 'coinmeet', 'echolink', 'count']
# Livecoin - ['namecoin', 'soarcoin', 'polybius', 'curecoin', 'count']
# CoinEgg - ['ink', 'energo', 'qbao', 'count']
# YoBit - ['newyorkcoin', 'e-dinar-coin', 'draftcoin', 'count']
# Tidex - ['waves-community-token', 'tiesdb', 'count']
# Qryptos - ['rock', 'eztoken', 'count']
