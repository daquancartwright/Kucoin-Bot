# -*- coding: utf-8 -*-
"""
Created on Wed Jul 27 20:54:30 2022

@author: daqua
"""

 # Import Libraries 
import time
import copy
import math
import requests
import numpy as np
import pandas as pd
import datetime as dt
from dateutil import tz
from datetime import timezone
from termcolor import colored
from indicator_functions import *
from strategy_indicators import *
# import matplotlib.pyplot as plt
# import matplotlib.dates as mpl_dates 
# from mpl_finance import candlestick_ohlc
from order_functions_v1 import *
from symbols_kucoin import get_symbols, symbols_to_remove
from colorama import Fore, Back, Style, init, AnsiToWin32
from kucoin_futures.client import User, Trade, Market, MarketData
from kucoin_config import futures_key, futures_secret, futures_passphrase
from data_organization import *

# URL
url = 'https://api-futures.kucoin.com'

# Establish Kucoin Futures Market Data Client Connection
mclient = Market(url)

# Establish Kucoin Futures Trade Account Client Connection
tclient = Trade(key=futures_key, secret=futures_secret, passphrase=futures_passphrase, is_sandbox=False, url=url)

# Establish Kucoin Futures Market Data Client Connection
uclient = User(futures_key, futures_secret, futures_passphrase)

# Strategy Setup
symbols = get_symbols()
# symbols_to_remove = get_symbols_to_remove(symbols, ohlcv, 200)
symbols = list(set(symbols) - set(symbols_to_remove))

granularity = 60
leverage = 5 
pos_risk = 100.0
pos_limit = 1

sl_atr = 1.5
tp_atr = 3
ts_sl_atr = 0.5
ts_tp_atr = 1

# Trailing Stop Dictionary
ts_dict = {}
for symbol in symbols:
    ts_dict[symbol] = pd.DataFrame()
    ts_dict[symbol]['Date'] = 0
    ts_dict[symbol].set_index('Date', inplace=True)
    ts_dict[symbol]['Trailing_Stop'] = np.zeros(1)

def df_merge(ohlcv):
    # Create Dictionary Motherboard
    data = copy.deepcopy(ohlcv)
    df_dict = {}
        # Calculate Indicator Values
    for key, value in ohlcv.items():
        # Money Management = Average True Range
        df_dict[key] = ATR(value, 30)
        # Baseline = Kaufman Adapted Moving Average (KAMA)
        df_dict[key]['KAMA'] = KAMA(value, 15, 2, 30)['KAMA']
        # Primary Confirmation = Detrended Price Oscillator (DPO)
        df_dict[key]['DPO'] = DPO(value, 21)['DPO']
        # Secondary Confirmation = Aroon
        df_dict[key]['Aroon_Up'] = Aroon(value, 25)['Aroon_Up']
        df_dict[key]['Aroon_Down'] = Aroon(value, 25)['Aroon_Down']
        # Volume/Volatility = On Balance Volume (OBV)
        df_dict[key]['OBV'] = OBV(value, 50)['OBV']
        df_dict[key]['OBV_MA'] = OBV(value, 50)['OBV_MA']
        # Exit Indicator = REX
        df_dict[key]['REX'] = REX(value, 'SMA', 32, 'SMA', 30)['REX']
        df_dict[key]['Signal'] = REX(value, 'SMA', 32, 'SMA', 30)['Signal']
        df_dict[key].dropna(inplace=True)
                
        # Buy_Long Entry Confirmations
        baseline_confirmation_1 = (df_dict[key]['Close'] > df_dict[key]['KAMA'])
        primary_confirmation_1 = (df_dict[key]['DPO'] > 0)
        secondary_confirmation_1 = (df_dict[key]['Aroon_Up'] > df_dict[key]['Aroon_Down'])
        volume_confirmation_1 = (df_dict[key]['OBV'] > df_dict[key]['OBV_MA'])
        
        # Sell_Short Confirmations
        baseline_confirmation_2 = (df_dict[key]['Close'] < df_dict[key]['KAMA'])
        primary_confirmation_2 = (df_dict[key]['DPO'] < 0)
        secondary_confirmation_2 = (df_dict[key]['Aroon_Up'] < df_dict[key]['Aroon_Down'])
        volume_confirmation_2 = (df_dict[key]['OBV'] < df_dict[key]['OBV_MA'])
        
        # Exit Trade Conditions
        exit_long_condition_1 = (df_dict[key]['REX'].iloc[-2] > df_dict[key]['Signal'].iloc[-2]) & (df_dict[key]['REX'].iloc[-1] < df_dict[key]['Signal'].iloc[-1])
        exit_short_condition_1 = (df_dict[key]['REX'].iloc[-2] < df_dict[key]['Signal'].iloc[-2]) & (df_dict[key]['REX'].iloc[-1] > df_dict[key]['Signal'].iloc[-1])
        
        # Buy_Long & Sell_Short Assignment
        df_dict[key]['Buy_Long'] = baseline_confirmation_1 & primary_confirmation_1 & secondary_confirmation_1 & volume_confirmation_1
        df_dict[key]['Sell_Short'] = baseline_confirmation_2 & primary_confirmation_2 & secondary_confirmation_2 & volume_confirmation_2
        
        # # Exit_Long & Exit_Short Assignment
        df_dict[key]['Exit_Long'] = exit_long_condition_1
        df_dict[key]['Exit_Short'] = exit_short_condition_1
        
    return df_dict

# Trade Signals
def trade_signal(merged_dict, l_s, ts_dict, price_df):
    signal = {}
    data = copy.deepcopy(merged_dict)
    for key, value in data.items():
        signal[key] = ''
        if l_s[key] == "":
            if value.iloc[-1].at['Buy_Long'] == True and value.iloc[-2].at['Buy_Long'] == False:
                signal[key] = 'Buy_Long'
            elif value.iloc[-1].at['Sell_Short'] == True and value.iloc[-2].at['Sell_Short'] == False:
                signal[key] = 'Sell_Short'
        elif l_s[key] == 'Long':
            if value.iloc[-1].at['Close'] >= ts_dict[key]["Take_Profit"].iloc[-1]:
                signal[key] = 'Trailing_Stop_Long'
            elif value.iloc[-1].at['Exit_Long'] == True:
                signal[key] = 'Close_Long_Positon'
        elif l_s[key] == 'Short':
            if value.iloc[-1].at['Close'] <= ts_dict[key]["Take_Profit"].iloc[-1]:
                signal[key] = 'Trailing_Stop_Short'
            elif value.iloc[-1].at['Exit_Short'] == True:
                signal[key] = 'Close_Short_Position'
            
    return signal

def main():
    # Data Organization
    ohlcv = {}
    for symbol in symbols:
        ohlcv[symbol] = get_futures_price_data(symbol, granularity)
        
    # Merged Dictionary
    merged_dict = df_merge(ohlcv)
    
    # Position Info 
    position_info = get_pos_df(symbols)
    price_df = position_info[0]
    open_df = position_info[1]
    pos_df = position_info[2]
    open_pos = position_info[3]
    entry_dict = position_info[4]
    pnl_dict = position_info[5]
    
    # Get Precision Dictionary
    precision_dict = get_precision_dict(symbols, price_df)
    
    # Cancel All Stop Loss and Take Profit Orders if No Longer in Trade
    sl_dict, tp_dict = get_stops(symbols)
    
    if len(sl_dict.items()) > 0 or len(tp_dict.items()) > 0:
        for key, value in sl_dict.items():
            if key not in open_pos:
                tclient.cancel_all_stop_order(key)
        for key, value in tp_dict.items():
            if key not in open_pos:
                tclient.cancel_all_stop_order(key)
                
    # Account Details
    account_details = uclient.get_account_overview('USDT')
    unreal_pnl = account_details['unrealisedPNL']
    account_bal = account_details['accountEquity']
    avail_bal = account_details['availableBalance']
    pos_margin = account_details['positionMargin']

    # Header Information Styling 
    print(f'Open Trades: {len(open_pos)} of {pos_limit}', end='                ')
    print(f'Time Frame:        {granularity_dict[granularity]}')
    print(f'Leverage:      {leverage}x\n')
    print(f'Position Risk:   $ {pos_risk}', end='           ')
    print(f'Position Margin:   $ {round(pos_margin,2)}')
    print(f'Account Balance: $ {round(account_bal,2)}', end='           ')
    print(f'Available Balance: $ {round(avail_bal,2)}\n')  
    if unreal_pnl > 0:
        print(f'Unrealised Profit/Loss: $'+Fore.GREEN,Style.BRIGHT+f'{round(unreal_pnl, 2)}\n'+Style.RESET_ALL)
    elif unreal_pnl < 0:
        print(f'Unrealised Profit/Loss: $'+Fore.RED,Style.BRIGHT+f'{round(unreal_pnl, 2)}\n'+Style.RESET_ALL)
    else:
        print(f'Unrealised Profit/Loss: $'+Fore.YELLOW,Style.BRIGHT+f'{round(unreal_pnl, 2)}\n'+Style.RESET_ALL)
    # print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    
    # Assign Long_Short Values
    l_s = {}
    for symbol in symbols:
        ohlcv[symbol] = get_futures_price_data(symbol, granularity)
        l_s[symbol] = ''
        for key, value in open_pos.items():
            if len(open_pos) > 0:
                if key == symbol and value > 0:
                    l_s[key] = 'Long'
                    if pnl_dict[key] > 0 and open_df.loc[key]["realisedPnl"] > 0:
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~  Entered At: {ts_dict[key].index[0]}  ~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                        print(f'Long Position Open for {pos_df.loc[key,"currentQty"] * price_df.loc[key, "multiplier"]} {key}  |'+Fore.GREEN,Style.BRIGHT+f'{round((price_df.loc[key, "markPrice_y"] - entry_dict[key]) / entry_dict[key] *100, 2)} %\n'+Style.RESET_ALL)
                        print(f'Target Price Level {ts_dict[key]["Trailing_Stop"][0]}\n')
                        print(f'Entry Price:   $ {entry_dict[key]}', end='     /     ')
                        print(f'Market Price:  $ {price_df.loc[key, "markPrice_y"]}')
                        print(f'Stop Price:    $ {ts_dict[key]["Stop_Loss"].iloc[-1]}', end='     /     ')
                        print(f'Target Price:  $ {ts_dict[key]["Take_Profit"].iloc[-1]}')
                        print(f'Stop/Loss Gap:  '+Fore.GREEN,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Stop_Loss"].iloc[-1], precision_dict[key])})'+Style.RESET_ALL, end='     /     ')
                        print(f'Target Gap:     '+Fore.RED,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Take_Profit"].iloc[-1], precision_dict[key])})\n'+Style.RESET_ALL)
                        print(f'Unrealised Profit/Loss: $'+Fore.GREEN,Style.BRIGHT+f'{round(pnl_dict[key], 2)}'+Style.RESET_ALL+f'  |  Realised Profit/Loss: $'+Fore.GREEN,Style.BRIGHT+f'{round(open_df.loc[key]["realisedPnl"], 2)}\n'+Style.RESET_ALL)
                    elif pnl_dict[key] < 0 and open_df.loc[key]["realisedPnl"] < 0:
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~  Entered At: {ts_dict[key].index[0]}  ~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                        print(f'Long Position Open for {pos_df.loc[key,"currentQty"] * price_df.loc[key, "multiplier"]} {key}  |'+Fore.RED,Style.BRIGHT+f'{round((price_df.loc[key, "markPrice_y"] - entry_dict[key]) / entry_dict[key] *100, 2)} %\n'+Style.RESET_ALL)
                        print(f'Target Price Level {ts_dict[key]["Trailing_Stop"][0]}\n')
                        print(f'Entry Price:   $ {entry_dict[key]}', end='     /     ')
                        print(f'Market Price:  $ {price_df.loc[key, "markPrice_y"]}')
                        print(f'Stop Price:    $ {ts_dict[key]["Stop_Loss"].iloc[-1]}', end='     /     ')
                        print(f'Target Price:  $ {ts_dict[key]["Take_Profit"].iloc[-1]}')
                        print(f'Stop/Loss Gap:  '+Fore.GREEN,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Stop_Loss"].iloc[-1], precision_dict[key])})'+Style.RESET_ALL, end='     /     ')
                        print(f'Target Gap:     '+Fore.RED,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Take_Profit"].iloc[-1], precision_dict[key])})\n'+Style.RESET_ALL)
                        print(f'Unrealised Profit/Loss: $'+Fore.RED,Style.BRIGHT+f'{round(pnl_dict[key], 2)}'+Style.RESET_ALL+f'  |  Realised Profit/Loss: $'+Fore.RED,Style.BRIGHT+f'{round(open_df.loc[key]["realisedPnl"], 2)}\n'+Style.RESET_ALL)
                    elif pnl_dict[key] < 0 and open_df.loc[key]["realisedPnl"] > 0:
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~  Entered At: {ts_dict[key].index[0]}  ~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                        print(f'Long Position Open for {pos_df.loc[key,"currentQty"] * price_df.loc[key, "multiplier"]} {key}  |'+Fore.RED,Style.BRIGHT+f'{round((price_df.loc[key, "markPrice_y"] - entry_dict[key]) / entry_dict[key] *100, 2)} %\n'+Style.RESET_ALL)
                        print(f'Target Price Level {ts_dict[key]["Trailing_Stop"][0]}\n')
                        print(f'Entry Price:   $ {entry_dict[key]}', end='     /     ')
                        print(f'Market Price:  $ {price_df.loc[key, "markPrice_y"]}')
                        print(f'Stop Price:    $ {ts_dict[key]["Stop_Loss"].iloc[-1]}', end='     /     ')
                        print(f'Target Price:  $ {ts_dict[key]["Take_Profit"].iloc[-1]}')
                        print(f'Stop/Loss Gap:  '+Fore.GREEN,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Stop_Loss"].iloc[-1], precision_dict[key])})'+Style.RESET_ALL, end='     /     ')
                        print(f'Target Gap:     '+Fore.RED,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Take_Profit"].iloc[-1], precision_dict[key])})\n'+Style.RESET_ALL)
                        print(f'Unrealised Profit/Loss: $'+Fore.RED,Style.BRIGHT+f'{round(pnl_dict[key], 2)}'+Style.RESET_ALL+f'  |  Realised Profit/Loss: $'+Fore.GREEN,Style.BRIGHT+f'{round(open_df.loc[key]["realisedPnl"], 2)}\n'+Style.RESET_ALL)
                    elif pnl_dict[key] > 0 and open_df.loc[key]["realisedPnl"] < 0:
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~  Entered At: {ts_dict[key].index[0]}  ~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                        print(f'Long Position Open for {pos_df.loc[key,"currentQty"] * price_df.loc[key, "multiplier"]} {key}  |'+Fore.GREEN,Style.BRIGHT+f'{round((price_df.loc[key, "markPrice_y"] - entry_dict[key]) / entry_dict[key] *100, 2)} %\n'+Style.RESET_ALL)
                        print(f'Target Price Level {ts_dict[key]["Trailing_Stop"][0]}\n')
                        print(f'Entry Price:   $ {entry_dict[key]}', end='     /     ')
                        print(f'Market Price:  $ {price_df.loc[key, "markPrice_y"]}')
                        print(f'Stop Price:    $ {ts_dict[key]["Stop_Loss"].iloc[-1]}', end='     /     ')
                        print(f'Target Price:  $ {ts_dict[key]["Take_Profit"].iloc[-1]}')
                        print(f'Stop/Loss Gap:  '+Fore.GREEN,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Stop_Loss"].iloc[-1], precision_dict[key])})'+Style.RESET_ALL, end='     /     ')
                        print(f'Target Gap:     '+Fore.RED,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Take_Profit"].iloc[-1], precision_dict[key])})\n'+Style.RESET_ALL)
                        print(f'Unrealised Profit/Loss: $'+Fore.GREEN,Style.BRIGHT+f'{round(pnl_dict[key], 2)}'+Style.RESET_ALL+f'  |  Realised Profit/Loss: $'+Fore.RED,Style.BRIGHT+f'{round(open_df.loc[key]["realisedPnl"], 2)}\n'+Style.RESET_ALL)    
                    elif pnl_dict[key] == 0 and open_df.loc[key]["realisedPnl"] > 0:
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~  Entered At: {ts_dict[key].index[0]}  ~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                        print(f'Long Position Open for {pos_df.loc[key,"currentQty"] * price_df.loc[key, "multiplier"]} {key}  |'+Fore.YELLOW,Style.BRIGHT+f'{round((price_df.loc[key, "markPrice_y"] - entry_dict[key]) / entry_dict[key] *100, 2)} %\n'+Style.RESET_ALL)
                        print(f'Target Price Level {ts_dict[key]["Trailing_Stop"][0]}\n')
                        print(f'Entry Price:   $ {entry_dict[key]}', end='     /     ')
                        print(f'Market Price:  $ {price_df.loc[key, "markPrice_y"]}')
                        print(f'Stop Price:    $ {ts_dict[key]["Stop_Loss"].iloc[-1]}', end='     /     ')
                        print(f'Target Price:  $ {ts_dict[key]["Take_Profit"].iloc[-1]}')
                        print(f'Stop/Loss Gap:  '+Fore.GREEN,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Stop_Loss"].iloc[-1], precision_dict[key])})'+Style.RESET_ALL, end='     /     ')
                        print(f'Target Gap:     '+Fore.RED,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Take_Profit"].iloc[-1], precision_dict[key])})\n'+Style.RESET_ALL)
                        print(f'Unrealised Profit/Loss: $'+Fore.YELLOW,Style.BRIGHT+f'{round(pnl_dict[key], 2)}'+Style.RESET_ALL+f'  |  Realised Profit/Loss: $'+Fore.GREEN,Style.BRIGHT+f'{round(open_df.loc[key]["realisedPnl"], 2)}\n'+Style.RESET_ALL)
                    else:
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~  Entered At: {ts_dict[key].index[0]}  ~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                        print(f'Long Position Open for {pos_df.loc[key,"currentQty"] * price_df.loc[key, "multiplier"]} {key}  |'+Fore.YELLOW,Style.BRIGHT+f'{round((price_df.loc[key, "markPrice_y"] - entry_dict[key]) / entry_dict[key] *100, 2)} %\n'+Style.RESET_ALL)
                        print(f'Target Price Level {ts_dict[key]["Trailing_Stop"][0]}\n')
                        print(f'Entry Price:   $ {entry_dict[key]}', end='     /     ')
                        print(f'Market Price:  $ {price_df.loc[key, "markPrice_y"]}')
                        print(f'Stop Price:    $ {ts_dict[key]["Stop_Loss"].iloc[-1]}', end='     /     ')
                        print(f'Target Price:  $ {ts_dict[key]["Take_Profit"].iloc[-1]}')
                        print(f'Stop/Loss Gap:  '+Fore.GREEN,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Stop_Loss"].iloc[-1], precision_dict[key])})'+Style.RESET_ALL, end='     /     ')
                        print(f'Target Gap:     '+Fore.RED,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Take_Profit"].iloc[-1], precision_dict[key])})\n'+Style.RESET_ALL)
                        print(f'Unrealised Profit/Loss: $'+Fore.YELLOW,Style.BRIGHT+f'{round(pnl_dict[key], 2)}'+Style.RESET_ALL+f'  |  Realised Profit/Loss: $'+Fore.RED,Style.BRIGHT+f'{round(open_df.loc[key]["realisedPnl"], 2)}\n'+Style.RESET_ALL)
               
                elif key == symbol and value < 0:
                    l_s[key] = 'Short'
                    if pnl_dict[key] > 0 and open_df.loc[key]["realisedPnl"] > 0:
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~  Entered At: {ts_dict[key].index[0]}  ~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                        print(f'Short Position Open for {round(pos_df.loc[key,"currentQty"] * price_df.loc[key, "multiplier"], precision_dict[key])} {key}  |'+Fore.GREEN,Style.BRIGHT+f'{round((price_df.loc[key, "markPrice_y"] - entry_dict[key]) / entry_dict[key] *-100, 2)} %\n'+Style.RESET_ALL)
                        print(f'Target Price Level {ts_dict[key]["Trailing_Stop"][0]}\n')
                        print(f'Entry Price:   $ {entry_dict[key]}', end='     /     ')
                        print(f'Market Price:  $ {price_df.loc[key, "markPrice_y"]}')
                        print(f'Stop Price:    $ {ts_dict[key]["Stop_Loss"].iloc[-1]}', end='     /     ')
                        print(f'Target Price:  $ {ts_dict[key]["Take_Profit"].iloc[-1]}')
                        print(f'Stop/Loss Gap:  '+Fore.RED,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Stop_Loss"].iloc[-1], precision_dict[key])})'+Style.RESET_ALL, end='     /     ')
                        print(f'Target Gap:     '+Fore.GREEN,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Take_Profit"].iloc[-1], precision_dict[key])})\n'+Style.RESET_ALL)
                        print(f'Unrealised Profit/Loss: $'+Fore.GREEN,Style.BRIGHT+f'{round(pnl_dict[key], 2)}'+Style.RESET_ALL+f'  |  Realised Profit/Loss: $'+Fore.GREEN,Style.BRIGHT+f'{round(open_df.loc[key]["realisedPnl"], 2)}\n'+Style.RESET_ALL)
                    elif pnl_dict[key] < 0 and open_df.loc[key]["realisedPnl"] < 0:
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~  Entered At: {ts_dict[key].index[0]}  ~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                        print(f'Short Position Open for {round(pos_df.loc[key,"currentQty"] * price_df.loc[key, "multiplier"], precision_dict[key])} {key}  |'+Fore.RED,Style.BRIGHT+f'{round((price_df.loc[key, "markPrice_y"] - entry_dict[key]) / entry_dict[key] *-100, 2)} %\n'+Style.RESET_ALL)
                        print(f'Target Price Level {ts_dict[key]["Trailing_Stop"][0]}\n')
                        print(f'Entry Price:   $ {entry_dict[key]}', end='     /     ')
                        print(f'Market Price:  $ {price_df.loc[key, "markPrice_y"]}')
                        print(f'Stop Price:    $ {ts_dict[key]["Stop_Loss"].iloc[-1]}', end='     /     ')
                        print(f'Target Price:  $ {ts_dict[key]["Take_Profit"].iloc[-1]}')
                        print(f'Stop/Loss Gap:  '+Fore.RED,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Stop_Loss"].iloc[-1], precision_dict[key])})'+Style.RESET_ALL, end='     /     ')
                        print(f'Target Gap:     '+Fore.GREEN,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Take_Profit"].iloc[-1], precision_dict[key])})\n'+Style.RESET_ALL)
                        print(f'Unrealised Profit/Loss: $'+Fore.RED,Style.BRIGHT+f'{round(pnl_dict[key], 2)}'+Style.RESET_ALL+f'  |  Realised Profit/Loss: $'+Fore.RED,Style.BRIGHT+f'{round(open_df.loc[key]["realisedPnl"], 2)}\n'+Style.RESET_ALL)
                    elif pnl_dict[key] < 0 and open_df.loc[key]["realisedPnl"] > 0:
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~  Entered At: {ts_dict[key].index[0]}  ~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                        print(f'Short Position Open for {round(pos_df.loc[key,"currentQty"] * price_df.loc[key, "multiplier"], precision_dict[key])} {key}  |'+Fore.RED,Style.BRIGHT+f'{round((price_df.loc[key, "markPrice_y"] - entry_dict[key]) / entry_dict[key] *-100, 2)} %\n'+Style.RESET_ALL)
                        print(f'Target Price Level {ts_dict[key]["Trailing_Stop"][0]}\n')
                        print(f'Entry Price:   $ {entry_dict[key]}', end='     /     ')
                        print(f'Market Price:  $ {price_df.loc[key, "markPrice_y"]}')
                        print(f'Stop Price:    $ {ts_dict[key]["Stop_Loss"].iloc[-1]}', end='     /     ')
                        print(f'Target Price:  $ {ts_dict[key]["Take_Profit"].iloc[-1]}')
                        print(f'Stop/Loss Gap:  '+Fore.RED,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Stop_Loss"].iloc[-1], precision_dict[key])})'+Style.RESET_ALL, end='     /     ')
                        print(f'Target Gap:     '+Fore.GREEN,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Take_Profit"].iloc[-1], precision_dict[key])})\n'+Style.RESET_ALL)
                        print(f'Unrealised Profit/Loss: $'+Fore.RED,Style.BRIGHT+f'{round(pnl_dict[key], 2)}'+Style.RESET_ALL+f'  |  Realised Profit/Loss: $'+Fore.GREEN,Style.BRIGHT+f'{round(open_df.loc[key]["realisedPnl"], 2)}\n'+Style.RESET_ALL)
                    elif pnl_dict[key] > 0 and open_df.loc[key]["realisedPnl"] < 0:
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~  Entered At: {ts_dict[key].index[0]}  ~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                        print(f'Short Position Open for {round(pos_df.loc[key,"currentQty"] * price_df.loc[key, "multiplier"], precision_dict[key])} {key}  |'+Fore.GREEN,Style.BRIGHT+f'{round((price_df.loc[key, "markPrice_y"] - entry_dict[key]) / entry_dict[key] *-100, 2)} %\n'+Style.RESET_ALL)
                        print(f'Target Price Level {ts_dict[key]["Trailing_Stop"][0]}\n')
                        print(f'Entry Price:   $ {entry_dict[key]}', end='     /     ')
                        print(f'Market Price:  $ {price_df.loc[key, "markPrice_y"]}')
                        print(f'Stop Price:    $ {ts_dict[key]["Stop_Loss"].iloc[-1]}', end='     /     ')
                        print(f'Target Price:  $ {ts_dict[key]["Take_Profit"].iloc[-1]}')
                        print(f'Stop/Loss Gap:  '+Fore.RED,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Stop_Loss"].iloc[-1], precision_dict[key])})'+Style.RESET_ALL, end='     /     ')
                        print(f'Target Gap:     '+Fore.GREEN,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Take_Profit"].iloc[-1], precision_dict[key])})\n'+Style.RESET_ALL)
                        print(f'Unrealised Profit/Loss: $'+Fore.GREEN,Style.BRIGHT+f'{round(pnl_dict[key], 2)}'+Style.RESET_ALL+f'  |  Realised Profit/Loss: $'+Fore.RED,Style.BRIGHT+f'{round(open_df.loc[key]["realisedPnl"], 2)}\n'+Style.RESET_ALL)    
                    elif pnl_dict[key] == 0 and open_df.loc[key]["realisedPnl"] > 0:
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~  Entered At: {ts_dict[key].index[0]}  ~~~~~~~~~~~~~~~~')
                        print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                        print(f'Short Position Open for {round(pos_df.loc[key,"currentQty"] * price_df.loc[key, "multiplier"], precision_dict[key])} {key}  |'+Fore.YELLOW,Style.BRIGHT+f'{round((price_df.loc[key, "markPrice_y"] - entry_dict[key]) / entry_dict[key] *-100, 2)} %\n'+Style.RESET_ALL)
                        print(f'Target Price Level {ts_dict[key]["Trailing_Stop"][0]}\n')
                        print(f'Entry Price:   $ {entry_dict[key]}', end='     /     ')
                        print(f'Market Price:  $ {price_df.loc[key, "markPrice_y"]}')
                        print(f'Stop Price:    $ {ts_dict[key]["Stop_Loss"].iloc[-1]}', end='     /     ')
                        print(f'Target Price:  $ {ts_dict[key]["Take_Profit"].iloc[-1]}')
                        print(f'Stop/Loss Gap:  '+Fore.RED,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Stop_Loss"].iloc[-1], precision_dict[key])})'+Style.RESET_ALL, end='     /     ')
                        print(f'Target Gap:     '+Fore.GREEN,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Take_Profit"].iloc[-1], precision_dict[key])})\n'+Style.RESET_ALL)
                        print(f'Unrealised Profit/Loss: $'+Fore.YELLOW,Style.BRIGHT+f'{round(pnl_dict[key], 2)}'+Style.RESET_ALL+f'  |  Realised Profit/Loss: $'+Fore.GREEN,Style.BRIGHT+f'{round(open_df.loc[key]["realisedPnl"], 2)}\n'+Style.RESET_ALL)
                    else:
                       print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                       print(f'~~~~~~~~~~~~~~~~  Entered At: {ts_dict[key].index[0]}  ~~~~~~~~~~~~~~~~')
                       print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
                       print(f'Long Position Open for {pos_df.loc[key,"currentQty"] * price_df.loc[key, "multiplier"]} {key}  |'+Fore.YELLOW,Style.BRIGHT+f'{round((price_df.loc[key, "markPrice_y"] - entry_dict[key]) / entry_dict[key] *100, 2)} %\n'+Style.RESET_ALL)
                       print(f'Target Price Level {ts_dict[key]["Trailing_Stop"][0]}\n')
                       print(f'Entry Price:   $ {entry_dict[key]}', end='     /     ')
                       print(f'Market Price:  $ {price_df.loc[key, "markPrice_y"]}')
                       print(f'Stop Price:    $ {ts_dict[key]["Stop_Loss"].iloc[-1]}', end='     /     ')
                       print(f'Target Price:  $ {ts_dict[key]["Take_Profit"].iloc[-1]}')
                       print(f'Stop/Loss Gap:  '+Fore.RED,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Stop_Loss"].iloc[-1], precision_dict[key])})'+Style.RESET_ALL, end='     /     ')
                       print(f'Target Gap:     '+Fore.GREEN,Style.BRIGHT+f'({round(price_df.loc[key, "markPrice_y"] - ts_dict[key]["Take_Profit"].iloc[-1], precision_dict[key])})\n'+Style.RESET_ALL)
                       print(f'Unrealised Profit/Loss: $'+Fore.YELLOW,Style.BRIGHT+f'{round(pnl_dict[key], 2)}'+Style.RESET_ALL+f'  |  Realised Profit/Loss: $'+Fore.RED,Style.BRIGHT+f'{round(open_df.loc[key]["realisedPnl"], 2)}\n'+Style.RESET_ALL)

    for symbol in symbols:
        signal = trade_signal(merged_dict, l_s, ts_dict, price_df)        
        
    #Place Orders
    for key, value in signal.items():
        
        if signal[key] == "Trailing_Stop_Long":
            trailing_stop_long(key, leverage, merged_dict, ts_dict, pos_df, precision_dict)
        
        elif signal[key] == "Trailing_Stop_Short":
            trailing_stop_short(key, leverage, merged_dict, ts_dict, pos_df, precision_dict)
            
        elif signal[key] == "Buy_Long":
            buy_long(key, merged_dict, price_df, open_pos, pos_risk, pos_limit, leverage, ts_dict, precision_dict)
                
        elif signal[key] == "Sell_Short":
            sell_short(key, merged_dict, price_df, open_pos, pos_risk, pos_limit, leverage, ts_dict, precision_dict)
                
        elif signal[key] == "Close_Long_Position":
            close_long_position(key)
            
        elif signal[key] == "Close_Short_Position":
            close_short_position(key)
            
            
    # We missed our trailing stop
    for key, value in open_pos.items():
        if ts_dict[key]['Trailing_Stop'][0] == 0 and abs(pos_df.loc[key,"currentQty"] * price_df.loc[key, "multiplier"]) < (abs(ts_dict[key]['Entry_Quantity'][0])) * .6:
            if pos_df.loc[key,"currentQty"] > 0:
                print(f'Update Trailing Stop Long for {key}\n')
                print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                # trailing_stop_long(key, leverage, merged_dict, ts_dict, pos_df, precision_dict)
            elif pos_df.loc[key,"currentQty"] < 0:
                # trailing_stop_short(key, leverage, merged_dict, ts_dict, pos_df, precision_dict)     
                print(f'Update Trailing Stop Short for {key}\n')
                print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            
    return merged_dict, signal, l_s, ts_dict

# Run Script With Loop
starttime=time.time()
timeout = time.time() + 60*60*8  # 60 seconds times 60 meaning the script will run for 1 hr
while time.time() <= timeout:
    tries = 10
    for i in range(tries):
        try:
            print(f"*******************************************************************\n**************  Passthrough At: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}  **************\n*******************************************************************\n")
            merged_dict, signal, l_s, ts_dict = main()
            time.sleep(300 - ((time.time() - starttime) % 300.0)) # 5 minute interval between each new execution
        except TimeoutError:
            print(f'Timeout Error. Restarting Bot')
            if i < tries - 1:
                tries -= 1
                continue
        except KeyboardInterrupt:
            print('\n\nKeyboard exception received. Exiting.')
            exit()
