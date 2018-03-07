# CIB Cryptocurrency Trading Strategy Evaluation Software

About: This is a tool to help facilitate better strategy development.

Authors: Nick Catranis, Mitchell Chase

Disclaimer: Use this software entirely at your own risk, for educational purposes only. The authors assume no responsibility out of any use of this code. This is not production ready software.

# Structure Overview

1. fox.py - Contains game class and simulate function. The backbone of the system.
1. download-history.py - Downloads data from various sources and coerces them into a common format (more below)
1. TODO: chart.py - Functions for displaying graphics

Additional notes: The work for this was done using python 3, using the anaconda library. Not all packages in anaconda are necessary.

# File breakdowns

## download-history.py

Data is stored in two different formats
1. Price data - CSV with date, asset_type, id, open, high, low, close, volume, and possibly additional columns

Date - stored in the format "year, month, day, hour, minute" e.g. "2018, 03, 12, 17, 55" is 5:55pm on March 12th of 2018.
Asset_type - string denoting what kind of asset it is (currently only "stock", "crypto")
open, high, low, close, volume - split adjusted if applicable
Additional columns (optional) - volumefrom, volumeto, algorithm used, market (e.g. USD or CNY), market_cap, data_source (e.g. coinmarketcap, alphavantage, etc.)
2. TODO: Factor data - CSV vector with values that range on a linear scale of good (positive) to neutral (zero) to bad (negative). The scale is preferred to be normalized but is not strictly required.

