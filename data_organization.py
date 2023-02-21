# -*- coding: utf-8 -*-
"""
Created on Mon Jul 25 19:33:30 2022

@author: daqua
"""

###################### Import Libraries ######################
import time
import pytz
import requests
import numpy as np
import pandas as pd
import datetime as dt
from dateutil import tz
from datetime import timezone
from kucoin_futures.client import User, Trade, Market, MarketData
from kucoin_config import futures_key, futures_secret, futures_passphrase

#URL
url = 'https://api-futures.kucoin.com'

#Establish Kucoin Futures Market Client Connection
mclient = Market(url)

#Establish Kucoin Futures Trade Account Client Connection
tclient = Trade(key=futures_key, secret=futures_secret, passphrase=futures_passphrase, is_sandbox=False, url=url)

#Establish Kucoin Futures User Client Connection
uclient = User(futures_key, futures_secret, futures_passphrase)

#Establish Kucoin Futures Market Data Client Connection
mdclient = MarketData(futures_key, futures_secret, futures_passphrase)

############ Data Organization ############

# Granularity
granularity_dict= {
    1: '1 Minute',
    5: '5 Minutes',
    15: '15 Minutes',
    30: '30 Minutes',
    60: 'Hourly',
    120: '2 Hour',
    240: '4 Hour',
    480: '8 Hour',
    720: '12 Hour',
    1440: 'Daily',
    10080: 'Weekly'}

# Market Data Organization DataFrame 
def get_futures_price_data(symbol, granularity):
    data = mclient.get_kline_data(symbol=symbol, granularity=granularity)
    df = pd.DataFrame(data)
    df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    # df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
    df = df.astype('float')
    df.set_index('Date', inplace=True)
    df.index = pd.to_datetime(df.index, unit='ms')
    return df

# Get Symbols 
def get_symbols():
    contracts = mclient.get_contracts_list()
    symbols_list = []
    for i in contracts:
        if i['symbol'][-5:] == 'USDTM':
            symbols_list.append(i['symbol'])
    return symbols_list

# Get Symbols to Remove
def get_symbols_to_remove(symbols, ohlcv, periods):
    symbols_to_remove = []
    for key, value in ohlcv.items():
        if len(value) < periods:
            symbols_to_remove.append(key)
    return symbols_to_remove

# Get Precision Dictionary
def get_precision_dict(symbols, price_df):
    ohlcv = {}
    precision_dict = {}
    for symbol in symbols:
        ohlcv[symbol] = get_futures_price_data(symbol, 1440)
        precision_dict[symbol] = len(str(price_df.loc[symbol]['markPrice_y']).split('.')[1])   
    return precision_dict

# Get Open Positions
def get_open_pos(symbols):
    position_details = {}
    pos_dict = {}
    open_pos = {}
    entry_dict = {}
    pnl_dict = {}
    for symbol in symbols:
        position_details[symbol] = tclient.get_position_details(symbol)
        for key, value in position_details.items():
            if value['isOpen'] is True:
                open_pos[key] = value['currentQty']
                entry_dict[key] = value['avgEntryPrice']
                pnl_dict[key] = value['unrealisedPnl']       
    return open_pos, entry_dict, pnl_dict

# Get Stops
def get_stops(symbols):
    sl_dict = {}
    tp_dict = {}
    stop_orders = tclient.get_open_stop_order()['items']
    for symbol in symbols:
        for i in stop_orders:
            if i['symbol'] == symbol and i['side'] == 'sell' and i['stop'] == 'down':
                sl_dict[symbol] = i['stopPrice']
            elif i['symbol'] == symbol and i['side'] == 'sell' and i['stop'] == 'up':
                tp_dict[symbol] = i['stopPrice']
            elif i['symbol'] == symbol and i['side'] == 'buy' and i['stop'] =='down':
                tp_dict[symbol] = i['stopPrice']
            elif i['symbol'] == symbol and i['side'] == 'buy' and i['stop'] =='up':
                sl_dict[symbol] = i['stopPrice']
    return sl_dict, tp_dict

# Positions DataFrame    
def get_pos_df(symbols):   
    all_pos = {}
    for symbol in symbols:
        all_pos[symbol] = tclient.get_position_details(symbol)
    pos_values = list(all_pos.values())
    pos_df = pd.DataFrame(pos_values)
    pos_df.set_index('symbol', inplace=True)
    #Details DataFrame
    details = {}
    # multiplier_dict = {}
    for symbol in symbols:
        details[symbol] = mclient.get_contract_detail(symbol)
    detail_values = list(details.values())  
    details_df = pd.DataFrame(detail_values)
    details_df.set_index('symbol', inplace=True)
    #Merge the DFs
    merged_df = pd.merge(pos_df, details_df, on='symbol')
    price_df = merged_df[['markPrice_y', 'multiplier', 'avgEntryPrice',
                            'unrealisedPnlPcnt', 'unrealisedPnl', 'unrealisedRoePcnt',
                            'markValue', 'isOpen'
                            ]]
    isOpen = merged_df[merged_df['isOpen'] == True]
    #Get Open Positions
    open_pos = {}
    entry_dict = {}
    pnl_dict = {}
    for key, value in all_pos.items():
        if value['isOpen'] is True:
            open_pos[key] = value['currentQty']
            entry_dict[key] = value['avgEntryPrice']
            pnl_dict[key] = value['unrealisedPnl']  
    return price_df, isOpen, merged_df, open_pos, entry_dict, pnl_dict