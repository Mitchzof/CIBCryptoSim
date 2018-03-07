import pandas as pd
import json, os

class Coin:
    coin_id = '';
    team_score = 0
    roadmap_score = 0
    impact_score = 0

    keywords = []

    def __init__(self, coin_id):
        self.coin_id = coin_id

    def set_team_score(self, score):
        assert(score <= 4 and score > 0)
        self.team_score = score

    def set_roadmap_score(self, score):
        assert(score <= 4 and score > 0)
        self.roadmap_score = score

    def set_impact_score(self, score):
        assert(score <= 4 and score > 0)
        self.impact_score = score

    def add_keyword(self, word):
        self.keywords.append(word)

DATA_FOLDER = "./data"

if not os.path.exists(DATA_FOLDER):
  os.makedirs(DATA_FOLDER)

fundamentals_dir = os.path.join(DATA_FOLDER, 'fundamentals')
if not os.path.exists(fundamentals_dir):
  os.makedirs(fundamentals_dir)

def get_tickers():
    path = os.path.join(DATA_FOLDER, 'cryptotickers.csv')
    if not os.path.exists(path):
        return []
    tickers = pd.read_csv(path)['id'].tolist()
    return tickers

def store_as_json(coin):
    path = os.path.join('./data/fundamentals', coin.coin_id + '.json')
    data = {}
    data['team_score'] = coin.team_score
    data['roadmap_score'] = coin.roadmap_score
    data['impact_score'] = coin.impact_score
    data['keywords'] = coin.keywords

    with open(path, 'w') as outfile:
        json.dump(data, outfile)

if __name__ == "__main__":
    running = True
    tickers = get_tickers()
    print('\033[01m' + 'CIB Crypto Fundamentals: Type \'quit\' to exit' + '\x1b[0m')
    print('')
    while running:
        index = input('Enter coin ranking\n')

        if index == 'quit':
            running = False;
        elif index.isdigit():
            index = int(index)-1
            coin_id = tickers[index]
            coin = Coin(coin_id)
            print('Writing fundementals for {}'.format(coin_id))
            coin.team_score = int(input('Enter team score (1-4)\n'))
            coin.roadmap_score = int(input('Enter roadmap score (1-4)\n'))
            coin.impact_score = int(input('Enter impact score (1-4)\n'))
            print('Enter keywords, type \'done\' when finished')
            waiting = True
            while waiting:
                keyword = input()
                if keyword == 'done':
                    waiting = False
                else:
                    coin.add_keyword(keyword)
            store_as_json(coin)
            print('Added {}'.format(coin_id))
        else:
            print('Input is not an integer ranking\n')
