# -*- coding: utf-8 -*-
"""
Created on Fri Jul 29 14:43:58 2022

@author: daqua
"""
# Import Libraries
import numpy as np
import pandas as pd
import datetime as dt
from datetime import timezone
from symbols_kucoin import get_symbols, symbols_to_remove
from data_organization import *
from colorama import Fore, Back, Style, init, AnsiToWin32
from termcolor import colored
init()

# Get Symbols
symbols = get_symbols()
symbols = list(set(symbols) - set(symbols_to_remove))

# Buy Long 
def buy_long(key, merged_dict, price_df, open_pos, pos_risk, pos_limit, leverage, ts_dict, precision_dict):
    market_price = price_df.loc[key, 'markPrice_y']
    multiplier = price_df.loc[key, 'multiplier']
    quantity = pos_risk / market_price
    tp_qty = quantity / 2
    open_positions = len(get_open_pos(symbols)[0])
    tp_price = round(merged_dict[key]['Close'][-1] + (merged_dict[key]['ATR'][-1] * 2.5), precision_dict[key])
    sl_price = round(merged_dict[key]['Close'][-1] - (merged_dict[key]['ATR'][-1] * 1.25), precision_dict[key])
    
    #Evaluate the conditions required to enter trade
    if open_positions < pos_limit:
        
        tries = 100
        for i in range(tries):
            try:
                #Place Buy Long Order
                tclient.create_market_order(symbol=key, side='buy', lever=leverage, size=(quantity/multiplier), client0id='')
                print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                
            except Exception as error_message:
                print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                print(f'\nPlace Buy Long Order Failed. {tries} Attempts Left!')
                if i < tries - 1:
                    tries -= 1
                    continue
            else:
                
                print(f'\nBuy Long Order for {key} Excecuted Succesfully!')
                break
            
        tries = 100
        for i in range(tries):
            try:
                #Place Stop Loss Order
                tclient.create_market_order(symbol=key, side='sell', lever=leverage, size=(quantity/multiplier), stop='down', stopPrice=str(sl_price), stopPriceType='MP', client0id='',) 
            
            except Exception as error_message:
                print(f'\nPlace Stop Loss Order Failed! {tries} Attempts Left!')
                if i < tries - 1:
                    tries -= 1
                    continue
                    
            else:
                print(f'\nStop Loss Order for {key} Excecuted Succesfully!')
                break
        
        tries = 100
        for i in range(tries):            
            try:
                #Place Take Profit Order
                tclient.create_market_order(symbol=key, side='sell', lever=leverage, size=(tp_qty/multiplier), stop='up', stopPrice=str(tp_price), stopPriceType='MP',  client0id='')
            
            except Exception as error_message:
                print(f'\nPlace Take Profit Order Failed! {tries} Attempts Left!')
                if i < tries - 1:
                    tries -= 1
                    continue
                
            else:
                print(f'\nTake Profit Order for {key} Excecuted Succesfully!\n')
                print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                break

        # Print Order Details
        print(f'\nLong Position Entered for {round(quantity,2)} {key}\n')
        print(f'Entry Price:  ${market_price}')
        print(f'Stop Loss:    ${sl_price}')
        print(f'Take Profit:  ${tp_price}\n')
        
        #Update Trailing Stop Dictionary
        ts_dict[key]['Entry_Price'] = market_price
        ts_dict[key]['Entry_Quantity'] = quantity
        ts_dict[key]['Trailing_Stop'] = np.zeros(1)
        ts_dict[key]['Stop_Loss'] = sl_price
        ts_dict[key]['Stop_Loss_1'] = sl_price
        ts_dict[key]['Take_Profit'] = tp_price
        ts_dict[key]['Take_Profit_1'] = tp_price
        ts_dict[key]['Entered_At'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        ts_dict[key].set_index('Entered_At', inplace=True)
    
    else:
        print(f'-------------------------------------------------------------------')
        print(f'\nThe {open_positions} Open Positions equals or exceeds The Max Position Size of {pos_limit}\nCannot Enter Long Trade for {key} at ${market_price}.\n')
        
    return ts_dict
        
# Sell Short 
def sell_short(key, merged_dict, price_df, open_pos, pos_risk, pos_limit, leverage, ts_dict, precision_dict):
    market_price = price_df.loc[key, 'markPrice_y']
    multiplier = price_df.loc[key, 'multiplier']
    quantity = pos_risk / market_price 
    tp_qty = quantity / 2
    open_positions = len(get_open_pos(symbols)[0])
    tp_price = round(merged_dict[key]['Close'][-1] - (merged_dict[key]['ATR'][-1] * 2.5), precision_dict[key])
    sl_price = round(merged_dict[key]['Close'][-1] + (merged_dict[key]['ATR'][-1] * 1.25), precision_dict[key])
    
    #Evaluate the conditions required to enter trade
    if open_positions < pos_limit:
        
        tries = 100
        for i in range(tries):
            try:
                #Place Sell Short Order
                tclient.create_market_order(symbol=key, side='sell', lever=leverage, size=(quantity/multiplier), client0id='')
                print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                
            except Exception as error_message:
                print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                print(f'\nPlace Sell Short Order Failed. {tries} Attempts Left!')
                if i < tries - 1:
                    tries -= 1
                    continue
            else:
                print(f'\nSell Short Order for {key} Excecuted Succesfully!')
                break
            
        tries = 100
        for i in range(tries):
            try:
                #Place Stop Loss Order
                tclient.create_market_order(symbol=key, side='buy', lever=leverage, size=(quantity/multiplier), stop='up', stopPrice=str(sl_price), stopPriceType='MP', client0id='')
            
            except Exception as error_message:
                print(f'\nPlace Stop Loss Order Failed! {tries} Attempts Left!')
                if i < tries - 1:
                    tries -= 1
                    continue
                    
            else:
                print(f'\nStop Loss Order for {key} Excecuted Succesfully!')
                break
        
        tries = 100
        for i in range(tries):            
            try:
                #Place Take Profit Order
                tclient.create_market_order(symbol=key, side='buy', lever=leverage, size=(tp_qty/multiplier), stop='down', stopPrice=str(tp_price), stopPriceType='MP',  client0id='')
            
            except Exception as error_message:
                print(f'\nPlace Take Profit Order Failed! {tries} Attempts Left!')
                if i < tries - 1:
                    tries -= 1
                    continue
                
            else:
                print(f'\nTake Profit Order for {key} Excecuted Succesfully!\n')
                print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
                break

        # Print Order Details
        print(f'\nShort Position Entered for {round(quantity,2)} {key}\n')
        print(f'Entry Price:  ${market_price}')
        print(f'Stop Loss:    ${sl_price}')
        print(f'Take Profit:  ${tp_price}\n')
        
        #Update Trailing Stop Dictionary
        ts_dict[key]['Entry_Price'] = market_price
        ts_dict[key]['Entry_Quantity'] = quantity
        ts_dict[key]['Trailing_Stop'] = np.zeros(1)
        ts_dict[key]['Stop_Loss'] = sl_price
        ts_dict[key]['Stop_Loss_0'] = sl_price
        ts_dict[key]['Take_Profit'] = tp_price
        ts_dict[key]['Take_Profit_0'] = tp_price
        ts_dict[key]['Entered_At'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        ts_dict[key].set_index('Entered_At', inplace=True)
               
    else:
        print(f'-------------------------------------------------------------------')
        print(f'\nThe {open_positions} Open Positions equals or exceeds The Max Position Size of {pos_limit}\nCannot Enter Short Trade for {key} at {market_price}.\n')

    return ts_dict
    
# Trailing Stop Long
def trailing_stop_long(key, leverage, merged_dict, ts_dict, pos_df, precision_dict):
    mark_price = pos_df.loc[key, 'markPrice_y']
    quantity = abs(pos_df.loc[key, 'currentQty'])
    tp_price = round(merged_dict[key]['Close'][-1] + (merged_dict[key]['ATR'][-1] * 1.5), precision_dict[key])
    sl_price = round(merged_dict[key]['Close'][-1] - (merged_dict[key]['ATR'][-1] * 1), precision_dict[key])
    
    # Update Trailing Stop Dictionary
    ts_dict[key]['Trailing_Stop'] += 1
    ts_dict[key]['Stop_Loss'] = sl_price
    ts_dict[key][f'Stop_Loss_{ts_dict[key]["Trailing_Stop"][0]}'] = sl_price
    ts_dict[key]['Take_Profit'] = tp_price
    ts_dict[key][f'Take_Profit_{ts_dict[key]["Trailing_Stop"][0]}'] = tp_price
    ts_dict[key][f'Target_{ts_dict[key]["Trailing_Stop"][0]}_Hit_At'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    
    # Cancel all Existing Stops
    tclient.cancel_all_stop_order(key)
    print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
    print(f'Target {ts_dict[key]["Trailing_Stop"][0]} for {key} Reached!\n')
    print(f'Cancelling all Existing Stop Orders and Updating the Trailing Stop.\n')
    
    tries = 100
    for i in range(tries):
        try:
             # Place New Trailing Stop Long Order
             tclient.create_market_order(symbol=key, side='sell', lever=leverage, size=int(quantity), stop='down', stopPrice=str(sl_price), stopPriceType='MP', client0id='')
            
        except Exception as error_message:
            print(f'Trailing Stop Order for {key} Failed. {tries} Retries Left!\n')
            if i < tries - 1:
                tries -= 1
                continue
        else:
            print(f'Trailing Stop Order for {key} Excecuted Succesfully!\n')
            print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
            break
        
    # Print Order Details
    print(f'New Target Profit:  ${tp_price}\n')
    print(f'New Trailing Stop:  ${sl_price}.\n')
    print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
   
    return ts_dict
    
# Trailing Stop Short
def trailing_stop_short(key, leverage, merged_dict, ts_dict, pos_df, precision_dict):
    mark_price = pos_df.loc[key, 'markPrice_y']
    quantity = abs(pos_df.loc[key, 'currentQty'])
    tp_price = round(merged_dict[key]['Close'][-1] - (merged_dict[key]['ATR'][-1] * 1.5), precision_dict[key])
    sl_price = round(merged_dict[key]['Close'][-1] + (merged_dict[key]['ATR'][-1] * 1), precision_dict[key])
    
    # Update Trailing Stop Dictionary
    ts_dict[key]['Trailing_Stop'] += 1
    ts_dict[key]['Stop_Loss'] = sl_price
    ts_dict[key][f'Stop_Loss_{ts_dict[key]["Trailing_Stop"][0]}'] = sl_price
    ts_dict[key]['Take_Profit'] = tp_price
    ts_dict[key][f'Take_Profit_{ts_dict[key]["Trailing_Stop"][0]}'] = tp_price
    ts_dict[key][f'Target_{ts_dict[key]["Trailing_Stop"][0]}_Hit_At'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    
    # Cancel all Existing Stops
    tclient.cancel_all_stop_order(key)
    print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
    print(f'Target {ts_dict[key]["Trailing_Stop"][0]} for {key} Reached!\n')
    print(f'Cancelling all Existing Stop Orders and Updating the Trailing Stop.\n')
    
    tries = 100
    for i in range(tries):
        try:
             # Place New Trailing Stop Short Order
             tclient.create_market_order(symbol=key, side='buy', lever=leverage, size=int(quantity), stop='up', stopPrice=str(sl_price), stopPriceType='MP', client0id='')
            
        except Exception as error_message:
            print(f'Trailing Stop Order for {key} Failed. {tries} Retries Left!\n')
            if i < tries - 1:
                tries -= 1
                continue
        else:
            print(f'Trailing Stop Order for {key} Excecuted Succesfully!\n')
            print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
            break
        
    # Print Order Details
    print(f'New Target Profit:  ${tp_price}\n')
    print(f'New Trailing Stop:  ${sl_price}.\n')
    print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
    
    return ts_dict

# Close Long Position
def close_long_position(key):
    tclient.cancel_all_stop_order(key)
    
    print('Exit Long ')
    tries = 100
    for i in range(tries):
        try:
            # Close Long Position Order
            tclient.create_market_order(symbol=key, side='sell', lever=5, closeOrder=True)
            
        except Exception as error_message:
            print(f'\nClose Long Position Order Failed. {tries} Attempts Left!')
            if i < tries - 1:
                tries -= 1
                continue
        else:
            print(f'\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            print(f'\nExit Indicator Triggered.')
            print('Close Long Position Order for {key} Excecuted Succesfully!\n')
            print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
            break
    

# Close Short Position
def close_short_position(key):
    tclient.cancel_all_stop_order(key)
    
    tries = 100
    for i in range(tries):
        try:
            # Close Short Position Order
            tclient.create_market_order(symbol=key, side='buy', lever=5, closeOrder=True)
            
        except Exception as error_message:
            print(f'\nClose Short Position Order Failed. {tries} Attempts Left!')
            if i < tries - 1:
                tries -= 1
                continue
        else:
            print(f'\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            print(f'\nExit Indicator Triggered.')
            print(f'Close Short Position for {key} Excecuted Succesfully!\n')
            print(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
            break
    

# # Place Stop Loss Long
# def place_sl_long(key, leverage, merged_dict, ts_dict, pos_df, price_df):
#     mark_price = pos_df.loc[key, 'markPrice_y']
#     multiplier = price_df.loc[key, 'multiplier']
#     quantity = abs(pos_df.loc[key, 'currentQty'])
#     tp_qty = quantity/2
#     tp_price = merged_dict[key]['Close'][-1] + (merged_dict[key]['ATR'][-1] * 0.5)
#     sl_price = merged_dict[key]['Close'][-1] - (merged_dict[key]['ATR'][-1] * 0.25)

#     #Set the price precision
#     sl_price, tp_price = set_price_precision(key, sl_price, tp_price)
    
#     # Cancel all Existing Stops
#     tclient.cancel_all_stop_order(key)
#     print(f'Target {ts_dict[key]["Trailing_Stop"]} Reached, Cancelling Existing Stop Orders')
#     print(f'New Target Profit:  ${tp_price}')

    
#     # Means we entered into a trade, but didn't set the stop loss or take profit didn't execute
#     if ts_dict[key]['Trailing_Stop'][0] == 0 and ts_dict[key].index[0] == 0:
        
#         # Place New Trailing Stop
#         tclient.create_market_order(key=key, side='sell', lever=leverage, size=int(quantity), stop='down', stopPrice=str(sl_price), stopPriceType='MP', client0id='')
#         print(f'New Trailing Stop: ${sl_price}.\n')
        
#         # Place Take Profit Order
#         tclient.create_market_order(key=key, side='sell', lever=leverage, size=(tp_qty/multiplier), stop='up', stopPrice=str(tp_price), stopPriceType='MP',  client0id='')
#         print(f'Take Profit:  ${tp_price}\n')
    
#         # Update Trailing Stop Dictionary
#         ts_dict[key]['Trailing_Stop'] += 0
#         ts_dict[key]['Stop_Loss'] = sl_price
#         ts_dict[key][f'Stop_Loss_{ts_dict[key]["Trailing_Stop"][0]}'] = sl_price
#         ts_dict[key]['Take_Profit'] = tp_price
#         ts_dict[key][f'Take_Profit_{ts_dict[key]["Trailing_Stop"][0]}'] = tp_price
#         ts_dict[key]['Entered_At'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
#         ts_dict[key].set_index('Entered_At', inplace=True)
        
#     # Means we entered into a trade and hit our take profit level, but the new trailing stop didn't execute
#     elif ts_dict[key]['Trailing_Stop'][0] == 0 and ts_dict[key].index[0] != 0:
        
#         # Place New Trailing Stop
#         tclient.create_market_order(symbol=key, side='sell', lever=leverage, size=int(quantity), stop='down', stopPrice=str(sl_price), stopPriceType='MP', client0id='')
#         print(f'New Trailing Stop: ${sl_price}.\n')
        
#         # Update Trailing Stop Dictionary
#         ts_dict[key]['Trailing_Stop'] += 1
#         ts_dict[key]['Stop_Loss'] = sl_price
#         ts_dict[key][f'Stop_Loss_{ts_dict[key]["Trailing_Stop"][0]}'] = sl_price
#         ts_dict[key]['Take_Profit'] = tp_price
#         ts_dict[key][f'Take_Profit_{ts_dict[key]["Trailing_Stop"][0]}'] = tp_price
#         ts_dict[key][f'Target_{ts_dict[key]["Trailing_Stop"][0]}_Hit_At'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        
#     return ts_dict

# # Place Stop Loss Short
# def place_sl_short(key, leverage, merged_dict, ts_dict, pos_df, price_df):
#     mark_price = pos_df.loc[key, 'markPrice_y']
#     multiplier = price_df.loc[key, 'multiplier']
#     quantity = abs(pos_df.loc[key, 'currentQty'])
#     tp_qty = quantity/2
#     tp_price = merged_dict[key]['Close'][-1] - (merged_dict[key]['ATR'][-1] * 0.5)
#     sl_price = merged_dict[key]['Close'][-1] + (merged_dict[key]['ATR'][-1] * 0.25)

#     #Set the price precision
#     sl_price, tp_price = set_price_precision(key, sl_price, tp_price)
    
#     # Cancel all Existing Stops
#     tclient.cancel_all_stop_order(key)
#     print(f'Target {ts_dict[key]["Trailing_Stop"]} Reached, Cancelling Existing Stop Orders')
#     print(f'New Target Profit:  ${tp_price}')

    
#     # Means we entered into a trade, but didn't set the stop loss or take profit didn't execute
#     if ts_dict[key].index[0] == 0:
        
#         # Place New Trailing Stop Short
#         tclient.create_market_order(symbol=key, side='buy', lever=leverage, size=int(quantity), stop='up', stopPrice=str(sl_price), stopPriceType='MP', client0id='')
#         print(f'New Trailing Stop: ${sl_price}.\n')
        
#         # Place Take Profit Order
#         tclient.create_market_order(symbol=key, side='buy', lever=leverage, size=(tp_qty/multiplier), stop='down', stopPrice=str(tp_price), stopPriceType='MP',  client0id='')
#         print(f'Take Profit:  ${tp_price}\n')
    
#         # Update Trailing Stop Dictionary
#         ts_dict[key]['Trailing_Stop'] += 0
#         ts_dict[key]['Stop_Loss'] = sl_price
#         ts_dict[key][f'Stop_Loss_{ts_dict[key]["Trailing_Stop"][0]}'] = sl_price
#         ts_dict[key]['Take_Profit'] = tp_price
#         ts_dict[key][f'Take_Profit_{ts_dict[key]["Trailing_Stop"][0]}'] = tp_price
#         ts_dict[key]['Entered_At'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
#         ts_dict[key].set_index('Entered_At', inplace=True)
        
#     # Means we entered into a trade and hit our take profit level, but the new trailing stop didn't execute
#     elif ts_dict[key].index[0] != 0:
        
#         # Place New Trailing Stop
#         tclient.create_market_order(symbol=key, side='buy', lever=leverage, size=int(quantity), stop='up', stopPrice=str(sl_price), stopPriceType='MP', client0id='')
#         print(f'New Trailing Stop: ${sl_price}.\n')
        
#         # Update Trailing Stop Dictionary
#         ts_dict[key]['Trailing_Stop'] += 1
#         ts_dict[key]['Stop_Loss'] = sl_price
#         ts_dict[key][f'Stop_Loss_{ts_dict[key]["Trailing_Stop"][0]}'] = sl_price
#         ts_dict[key]['Take_Profit'] = tp_price
#         ts_dict[key][f'Take_Profit_{ts_dict[key]["Trailing_Stop"][0]}'] = tp_price
#         ts_dict[key][f'Target_{ts_dict[key]["Trailing_Stop"][0]}_Hit_At'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    
#     return ts_dict

# # Place Take Profit Long
# def place_tp_long(key, leverage, merged_dict, ts_dict, pos_df, price_df):
#     mark_price = pos_df.loc[key, 'markPrice_y']
#     multiplier = price_df.loc[key, 'multiplier']
#     quantity = abs(pos_df.loc[key, 'currentQty'])
#     tp_qty = quantity/2
#     tp_price = merged_dict[key]['Close'][-1] + (merged_dict[key]['ATR'][-1] * 0.5)
#     sl_price = merged_dict[key]['Close'][-1] - (merged_dict[key]['ATR'][-1] * 0.25)

#     #Set the price precision
#     sl_price, tp_price = set_price_precision(key, sl_price, tp_price)
        
#     # Place Take Profit Order
#     tclient.create_market_order(symbol=key, side='sell', lever=leverage, size=(tp_qty/multiplier), stop='up', stopPrice=str(tp_price), stopPriceType='MP',  client0id='')
#     print(f'Take Profit:  ${tp_price}\n')

#     # Update Trailing Stop Dictionary
#     ts_dict[key]['Trailing_Stop'] += 0
#     ts_dict[key]['Stop_Loss'] = sl_price
#     ts_dict[key][f'Stop_Loss_{ts_dict[key]["Trailing_Stop"][0]}'] = sl_price
#     ts_dict[key]['Take_Profit'] = tp_price
#     ts_dict[key][f'Take_Profit_{ts_dict[key]["Trailing_Stop"][0]}'] = tp_price
#     ts_dict[key]['Entered_At'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
#     ts_dict[key].set_index('Entered_At', inplace=True)
        
#     return ts_dict

# # Place Take Profit Short
# def place_tp_short(key, leverage, merged_dict, ts_dict, pos_df, price_df):
#     mark_price = pos_df.loc[key, 'markPrice_y']
#     multiplier = price_df.loc[key, 'multiplier']
#     quantity = abs(pos_df.loc[key, 'currentQty'])
#     tp_qty = quantity/2
#     tp_price = merged_dict[key]['Close'][-1] - (merged_dict[key]['ATR'][-1] * 0.5)
#     sl_price = merged_dict[key]['Close'][-1] + (merged_dict[key]['ATR'][-1] * 0.25)

#     #Set the price precision
#     sl_price, tp_price = set_price_precision(key, sl_price, tp_price)
        
#     # Place Take Profit Order
#     tclient.create_market_order(symbol=key, side='buy', lever=leverage, size=(tp_qty/multiplier), stop='down', stopPrice=str(tp_price), stopPriceType='MP',  client0id='')
#     print(f'Take Profit:  ${tp_price}\n')

#     # Update Trailing Stop Dictionary
#     ts_dict[key]['Trailing_Stop'] += 0
#     ts_dict[key]['Stop_Loss'] = sl_price
#     ts_dict[key][f'Stop_Loss_{ts_dict[key]["Trailing_Stop"][0]}'] = sl_price
#     ts_dict[key]['Take_Profit'] = tp_price
#     ts_dict[key][f'Take_Profit_{ts_dict[key]["Trailing_Stop"][0]}'] = tp_price
#     ts_dict[key]['Entered_At'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
#     ts_dict[key].set_index('Entered_At', inplace=True)
        
#     return ts_dict
        
