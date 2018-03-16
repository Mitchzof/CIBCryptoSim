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
preffered_ex = ['Binance'] #higher priority towards the end
blacklist_ex = ['Bittrex','Cryptopia','OKEx']
# Filter out bad exchanges
raw_data = dict(ex_coins)
data = {}
for d in raw_data.keys():
	if hasattr(ccxt,d.lower()) and d not in blacklist_ex:
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
	blacklist = list(data[exchange].keys())
	if 'count' in blacklist:
		blacklist.remove('count')
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

# Binance - 15
# HitBTC - 40
# Kucoin - 28
# Poloniex - 21
# Liqui - 7
# Bibox - 7
# CoinExchange - 7
# Livecoin - 5

# Binance - ['poa-network', 'bluzelle', 'sonm', 'simple-token', 'vibe', 'amber', 'singulardtv', 'wabi', 'appcoins', 'etherparty', 'gifto', 'blox', 'triggers', 'monetha', 'aeron', 'agrello-delta']
# HitBTC - ['envion', 'c20', 'origintrail', 'eidoo', 'utrust', 'universa', 'naga', 'metaverse', 'kickico', 'tierion', 'centra', 'hive-project', 'indahash', 'presearch', 'paragon', 'attention-token-of-media', 'nimiq', 'swissborg', 'suncontract', 'domraider', 'blackmoon', 'lamden', 'latoken', 'icos', 'propy', 'ixledger', 'coinpoker', 'chronobank', 'hackspace-capital', 'quantum', 'stox', 'airtoken', 'lockchain', 'ebtcnew', 'polybius', 'matryx', 'sportyco', 'hellogold', 'worldcore', 'life']
# Kucoin - ['telcoin', 'jibrel-network', 'red-pulse', 'deepbrain-chain', 'data', 'modum', 'trinity-network-credit', 'decision-token', 'qlink', 'medical-chain', 'blockport', 'zeepin', 'stk', 'iht-real-estate-protocol', 'odyssey', 'restart-energy-mwat', 'covesting', 'canyacoin', 'carvertical', 'snovio', 'coinfi', 'hacken', 'axpire', 'solaris', 'bounty0x', 'change', 'cargox', 'elixir']
# Poloniex - ['peercoin', 'burst', 'library-credit', 'counterparty', 'viacoin', 'synereo', 'potcoin', 'steem-dollars', 'vericoin', 'blackcoin', 'omni', 'florincoin', 'expanse', 'primecoin', 'pascal-coin', 'clams', 'neoscoin', 'nexium', 'foldingcoin', 'pinkcoin', 'bitcrystals']
# Liqui - ['melon', 'mobilego', 'taas', 'wepower', 'tokencard', 'neumark', 'mysterium']
# Bibox - ['medibloc', 'bibox-token', 'bottos', 'cpchain', 'bloomtoken', 'bitclave', 'spectre-utility']
# CoinExchange - ['experience-points', 'eccoin', 'uquid-coin', 'bitconnect', 'shield-xsh', 'b3coin', 'espers']
# Livecoin - ['namecoin', 'soarcoin', 'insurepal', 'rialto', 'curecoin']


