import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

import requests

URL = "https://api.scryfall.com/cards/named?fuzzy=aust+com"
page = requests.get(URL)

print("\n")
print(page.json()['name'])
print("\n")

# cards = pd.read_csv('data/AllPrintingsCSVFiles/cards.csv')

# # print(cards.head())
# print(cards.name.head())