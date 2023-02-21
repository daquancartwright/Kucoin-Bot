############################ Import Packages #############################
import copy
import time
import numpy as np
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt

########################## Technical Indicators ##########################

# Aroon Oscillator
def Aroon(df, periods):
    df = df.copy()
    df['Aroon_Up'] = 100 * df['High'].rolling(periods + 1).apply(lambda x: x.argmax()) / periods
    df['Aroon_Down'] = 100 * df['Low'].rolling(periods + 1).apply(lambda x: x.argmin()) / periods
    df['Aroon_Oscillator'] = df['Aroon_Up'] - df['Aroon_Down']
    return df


# Absolute Strength Histogram 
def ASH(df, length, smooth, ma):
    df = df.copy()
    # Exponential Moving Average
    if ma == 'EMA':
        df['Price_1'] = df['Close'].ewm(span=1, min_periods=1).mean()
        df['Price_2'] = df['Close'].shift(1).ewm(span=1, min_periods=1).mean()
        df['Bulls_0'] = 0.5 * (abs(df['Price_1'] - df['Price_2']) + (df['Price_1'] - df['Price_2']))
        df['Bears_0'] = 0.5 * (abs(df['Price_1'] - df['Price_2']) - (df['Price_1'] - df['Price_2']))
        df['Avg_Bulls'] = df['Bulls_0'].ewm(span=length, min_periods=length).mean()
        df['Avg_Bears'] = df['Bears_0'].ewm(span=length, min_periods=length).mean()
        df['Smooth_Bulls'] = df['Avg_Bulls'].ewm(span=smooth, min_periods=smooth).mean()
        df['Smooth_Bears'] = df['Avg_Bears'].ewm(span=smooth, min_periods=smooth).mean()
        df['Difference'] = abs(df['Smooth_Bulls'] - df['Smooth_Bears'])
    # Simple Moving Average
    elif ma == 'SMA':
        df['Price_1'] = df['Close'].rolling(window=1).mean()
        df['Price_2'] = df['Close'].shift(1).rolling(window=1).mean()
        df['Bulls_0'] = 0.5 * (abs(df['Price_1'] - df['Price_2']) + (df['Price_1'] - df['Price_2']))
        df['Bears_0'] = 0.5 * (abs(df['Price_1'] - df['Price_2']) - (df['Price_1'] - df['Price_2']))
        df['Avg_Bulls'] = df['Bulls_0'].rolling(window=length).mean()
        df['Avg_Bears'] = df['Bears_0'].rolling(window=length).mean()
        df['Smooth_Bulls'] = df['Avg_Bulls'].rolling(window=smooth).mean()
        df['Smooth_Bears'] = df['Avg_Bears'].rolling(window=smooth).mean()
        df['Difference'] = abs(df['Smooth_Bulls'] - df['Smooth_Bears'])
    return df


# Average True Range (ATR)
def ATR(DF,n):
    "function to calculate True Range and Average True Range"
    df = DF.copy()
    df['H-L']=abs(df['High']-df['Low'])
    df['H-PC']=abs(df['High']-df['Close'].shift(1))
    df['L-PC']=abs(df['Low']-df['Close'].shift(1))
    df['TR']=df[['H-L','H-PC','L-PC']].max(axis=1,skipna=False)
    df['ATR'] = df['TR'].rolling(n).mean()
    #df['ATR'] = df['TR'].ewm(span=n,adjust=False,min_periods=n).mean()
    df2 = df.drop(['H-L','H-PC','L-PC', 'TR'],axis=1)
    return df2


# Bollinger Bands
def BB(DF, n):
    "function to calculate Bollinger Band"
    df = DF.copy()
    df["MA"] = df['Close'].rolling(n).mean()
    df["BB_Upper"] = df["MA"] + 2*df['Close'].rolling(n).std(ddof=0) #ddof=0 is required since we want to take the standard deviation of the population and not sample
    df["BB_Lower"] = df["MA"] - 2*df['Close'].rolling(n).std(ddof=0) #ddof=0 is required since we want to take the standard deviation of the population and not sample
    df["BB_Width"] = df["BB_Up"] - df["BB_Down"]
    df.dropna(inplace=True)
    return df


# Chandelier Exit
def CE(df, n, multiplier, ATR):
    df = ATR(df, n)
    df['CE_long'] = (df['Close'].rolling(window=n).max() - (df['ATR'] * multiplier))
    df['CE_short'] = (df['Close'].rolling(window=n).min() + (df['ATR'] * multiplier))
    return df


# Detrended Price Oscillator(DPO)
def DPO(df, period):
    df = df.copy()
    lookback = int((period / 2) + 1)
    df = SMA(df, period)
    df['DPO'] = df['Close'] - df[f'sma_{period}'].shift(lookback)
    return df


# Elder's Force Index (EFI) 
def EFI(df, slow_ma, fast_ma):
    df.copy()
    df['X_Value'] = df['Volume'] * (df['Close'] - df['Close'].shift(1))
    df['Slow_MA'] = df['X_Value'].ewm(span=slow_ma).mean()
    df['Force_Index'] = df['X_Value'].ewm(span=fast_ma).mean()
    return df


# Exponential Moving Average (EMA) 
def EMA(df,a,b):
    "function to calculate stochastic"
    df = df.copy()
    df["EMA_Fast"]=df["Close"].ewm(span=a,min_periods=a).mean()
    df["EMA_Slow"]=df["Close"].ewm(span=b,min_periods=b).mean()
    return df


# Guppy Multiple Moving Averages (GMMA)
def Guppy(df):
    Trader_MAs = [3, 5, 8, 10, 12, 15]
    Investor_MAs = [30, 35, 40, 45, 50, 60]
    df = df.copy()
    for i in Trader_MAs:
        df['EMA_'+str(i)] = df['Close'].ewm(span=i, min_periods=i).mean()
    for i in Investor_MAs:
        df['EMA_'+str(i)] = df['Close'].ewm(span=i, min_periods=i).mean()
    return df


# Ichimoku Cloud
def Ichimoku(df):
    # Tenkan-sen (Conversion Line): (9-period_high + 9-period_low) / 2
    df = df.copy()
    period_9_high = df['High'].rolling(window=9).max()
    period_9_low = df['Low'].rolling(window=9).min()
    df['Tenkan'] = (period_9_high + period_9_low) / 2
    # Kijun-sen (Conversion Line): (26-period_high + 26-period_low) / 2
    period_26_high = df['High'].rolling(window=26).max()
    period_26_low = df['Low'].rolling(window=26).min()
    df['Kijun'] = (period_26_high + period_26_low) / 2
    # The most current closing price plotted 26 time periods behind
    df['Chikou'] = df['Close'].shift(-26)
    # Senkou Span A (Leading Span A): (Conversion Line + Base Line) / 2
    df['Senkou_A'] = ((df['Tenkan'] + df['Kijun']) / 2).shift(26)
    # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2)
    period_52_high = df['High'].rolling(window=52).max()
    period_52_low = df['Low'].rolling(window=52).min()
    df['Senkou_B'] = ((period_52_high + period_52_low) / 2).shift(26)
    # Create Cloud Top and Bottom
    df['Cloud_Top'] = df[["Senkou_A", "Senkou_B"]].max(axis=1)
    df['Cloud_Bottom'] = df[['Senkou_A', 'Senkou_B']].min(axis=1)
    # Create Cloud Top and Bottom 26 periods ahead
    df['Lead_Senkou_A'] = ((df['Tenkan'] + df['Kijun']) / 2)
    df['Lead_Senkou_B'] = ((period_52_high + period_52_low) / 2)
    return df


# Kaufman's Adaptive Moving Average (KAMA) 
def KAMA(df, length, f_periods, s_periods):
    df = df.copy()
    df['Abs_Diff_X'] = abs(df['Close'] - df['Close'].shift(1))
    df['ER_Num'] = abs(df['Close'] - df['Close'].shift(length))
    df['ER_Den'] = df['Abs_Diff_X'].rolling(length).sum()
    df['Efficiency_Ratio'] = df['ER_Num'] / df['ER_Den']
    df['Smoothing_Constant'] = (df['Efficiency_Ratio'] * 2 / (f_periods + 1) - 2 / (s_periods + 1) + 2 / (s_periods + 1)) ** 2
    # df['Smoothing_Constant'] = df['Efficiency_Ratio'] * (fast_end - slow_end) + (slow_end) ** 2
    # df['Smoothing_Constant'] = (df['Efficiency_Ratio'] * (2/(2+1) - 2/(30+1))) + (df['Efficiency_Ratio'] * (2/(2+1) - 2/(30+1))) + (df['Efficiency_Ratio'] * (2/(2+1) - 2/(30+1))) + (df['Efficiency_Ratio'] * (2/(2+1) - 2/(30+1))) + (df['Efficiency_Ratio'] * (2/(2+1) - 2/(30+1)))
    
    df['KAMA'] = np.zeros(df['Smoothing_Constant'].size)
    N = len(df['KAMA'])
    first_value = True
    
    for i in range(N):
        if df['Smoothing_Constant'][i] != df['Smoothing_Constant'][i]:
            df['KAMA'][i] = np.nan
        else:
            if first_value:
                df['KAMA'][i] = df['Close'][i]
                first_value = False
            else:
                df['KAMA'][i] = df['KAMA'][i-1] + df['Smoothing_Constant'][i] * (df['Close'][i] - df['KAMA'][i-1])
    return df


# Money Flow Index (MFI)
def MFI(df):
    df = copy.deepcopy(df)
    df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['Raw_Money_Flow'] = df['Typical_Price'] * df['Volume']
    positive_flow = []
    negative_flow = []
    for i in range(len(df['Typical_Price'])):
        if df['Typical_Price'][i] > df['Typical_Price'][i - 1]:
            positive_flow.append(df['Raw_Money_Flow'][i])
            negative_flow.append(0)
        elif df['Typical_Price'][i] < df['Typical_Price'][i - 1]:
            positive_flow.append(0)
            negative_flow.append(df['Raw_Money_Flow'][i])
        else:
            positive_flow.append(0)
            negative_flow.append(0)   
    period = 14
    positive_mf = []
    negative_mf = []
    for i in range(len(positive_flow)):
        positive_mf.append(sum(positive_flow[i + 1 - period: i + 1]))
    for i in range(len(negative_flow)):
        negative_mf.append(sum(negative_flow[i + 1 - period: i + 1]))
    df['Positive_Mf'] = np.array(positive_mf)
    df['Negative_Mf'] = np.array(negative_mf)
    df['Money_Flow_Ratio'] = df['positive_mf'] / df['Negative_Mf']
    df['Money_Flow_Index'] = 100 - (100 / (1 + df['Money_Flow_Ratio']))
    return df


# Moving Average Convergence Divergence (MACD)
def MACD(DF,a,b,c):
    """function to calculate MACD
       typical values a = 12; b =26, c =9"""
    df = DF.copy() # Don't want to mess up the original df
    df["MA_Fast"]=df["Close"].ewm(span=a,min_periods=a).mean()
    df["MA_Slow"]=df["Close"].ewm(span=b,min_periods=b).mean()
    df["MACD"]=df["MA_Fast"]-df["MA_Slow"]
    df["Signal"]=df["MACD"].ewm(span=c,min_periods=c).mean()
    df["Hist"]=df['MACD']-df['Signal']
    #df.dropna(inplace=True)
    return df


# On Balance Volume (OBV)
def OBV(df, ma_periods):
    """function to calculate On Balance Volume"""
    df = df.copy()
    df['Daily_Return'] = df['Close'].pct_change()
    df['Direction'] = np.where(df['Daily_Return']>=0,1,-1)
    # df['direction'][0] = 0
    df['Effective_Volume'] = df['Volume'] * df['Direction']
    df['OBV'] = df['Effective_Volume'].cumsum()
    # df2 = df.drop(['daily_ret','direction','vol_adj'],axis=1)
    df['OBV_MA'] = df['OBV'].rolling(ma_periods).mean()
    return df


# REX Oscillator 
def REX(df, rex_ma_type, smooth, sig_ma_type, smooth_sig):
    df['TVB'] = (3 * df['Close']) - (df['Low'] + df['Open'] + df['High'])
    if rex_ma_type == 'SMA':
        df['REX'] = df['TVB'].rolling(smooth).mean()
    elif rex_ma_type == 'EMA':
        df['REX'] = df['TVB'].ewm(span=smooth,min_periods=smooth).mean()
    
    if sig_ma_type == 'SMA':
        df['Signal'] = df['REX'].rolling(smooth_sig).mean()
    elif sig_ma_type == 'EMA':
        df['Signal'] = df['REX'].ewm(span=smooth_sig,min_periods=smooth_sig).mean()
    return df


# Relative Strength Index (RSI)
def RSI(df, n):
    "function to calculate RSI"
    df = df.copy()
    delta = df["Close"].diff().dropna()
    u = delta * 0
    d = u.copy()
    u[delta > 0] = delta[delta > 0]
    d[delta < 0] = -delta[delta < 0]
    u[u.index[n-1]] = np.mean( u[:n]) # first value is average of gains
    u = u.drop(u.index[:(n-1)])
    d[d.index[n-1]] = np.mean( d[:n]) # first value is average of losses
    d = d.drop(d.index[:(n-1)])
    rs = u.ewm(com=n,min_periods=n).mean()/d.ewm(com=n,min_periods=n).mean()
    df['RSI'] = 100 - 100 / (1+rs)
    return df


# Stochastic Oscillator
def Stochastic(df,a,b,c):
    "function to calculate stochastic"
    df['k']=((df['c'] - df['l'].rolling(a).min())/(df['h'].rolling(a).max()-df['l'].rolling(a).min()))*100
    df['K']=df['k'].rolling(b).mean() 
    df['D']=df['K'].rolling(c).mean()
    return df


# Simple Moving Average (SMA)
def SMA(df,a):
    "function to calculate stochastic"
    df = df.copy()
    df[f'sma_{a}']=df['Close'].rolling(a).mean()
    df.dropna(inplace=True)
    return df
     
   
# SMI Ergodic
def SMI_Ergodic(df, short_len, long_len, sig_len):
    df.copy()
    df['Ergodic'] = TSI(df, short_len, long_len)
    df['Signal'] = df['Ergodic'].ewm(span=sig_len, min_periods=sig_len).mean()
    return df


# True Strength Index (TSI)
def TSI(df, period_1, period_2):
    df = df.copy()
    df['Price_Change'] = df['Close'] - df['Close'].shift(1)
    df['SM1_Simple'] = df['Price_Change'].ewm(span=period_1, min_periods=period_1).mean()
    df['SM1_Double'] = df['SM1_Simple'].ewm(span=period_2, min_periods=period_2).mean()
    df['SM2_Simple'] = abs(df['Price_Change']).ewm(span=period_1, min_periods=period_1).mean()
    df['SM2_Double'] = df['SM2_Simple'].ewm(span=period_2, min_periods=period_2).mean()
    df['TSI'] = 100 * (df['SM1_Double'] / df['SM2_Double'])
    return df['TSI']


# Volume Weighted Average Price (VWAP)
def VWAP(df,a,b): # df = ohlcv, a = short time period, b = long time period
    df['Avg Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['PV'] = df['Avg Price'] * df['Volume']
    df['VWAP_a'] = df['PV'].rolling(a).mean() / df['Volume'].rolling(a).mean()
    df['VWAP_b'] = df['PV'].rolling(b).mean() / df['Volume'].rolling(b).mean()
    return df


# Waddah Attar Explosion (WAE)
def WAE(df, sensitivity, fast_ema, slow_ema, bb_channel):
    df = df.copy()
    df['Fast_Ema'] = EMA(df, fast_ema, slow_ema)['EMA_Fast']
    df['Slow_Ema'] = EMA(df, fast_ema, slow_ema)['EMA_Slow']
    df['MACD'] = df['Fast_Ema'] - df['Slow_Ema']
    df['BB_Up'] = BB(df, bb_channel)['BB_Up']
    df['BB_Down'] = BB(df, bb_channel)['BB_Down']
    df['T1'] = (df['MACD'] - df['MACD'].shift(1)) * sensitivity
    df['T2'] = (df['MACD'].shift(2) - df['MACD'].shift(3)) * sensitivity
    df['Explosion_Line'] = df['BB_Up'] - df['BB_Down']
    df['Up_Trend'] = np.where(df['T1'] >= 0, df['T1'], 0)
    df['Down_Trend'] = np.where(df['T1'] < 0, df['T1'] * -1, 0)
    return df


# # Average Directional Index
# def ADX(DF,n):
#     "function to calculate ADX"
#     df2 = DF.copy()
#     df2['TR'] = ATR(df2,n)['TR'] #the period parameter of ATR function does not matter because period does not influence TR calculation
#     df2['DMplus']=np.where((df2['High']-df2['High'].shift(1))>(df2['Low'].shift(1)-df2['Low']),df2['High']-df2['High'].shift(1),0)
#     df2['DMplus']=np.where(df2['DMplus']<0,0,df2['DMplus'])
#     df2['DMminus']=np.where((df2['Low'].shift(1)-df2['Low'])>(df2['High']-df2['High'].shift(1)),df2['Low'].shift(1)-df2['Low'],0)
#     df2['DMminus']=np.where(df2['DMminus']<0,0,df2['DMminus'])
#     TRn = []
#     DMplusN = []
#     DMminusN = []
#     TR = df2['TR'].tolist()
#     DMplus = df2['DMplus'].tolist()
#     DMminus = df2['DMminus'].tolist()
#     for i in range(len(df2)):
#         if i < n:
#             TRn.append(np.NaN)
#             DMplusN.append(np.NaN)
#             DMminusN.append(np.NaN)
#         elif i == n:
#             TRn.append(df2['TR'].rolling(n).sum().tolist()[n])
#             DMplusN.append(df2['DMplus'].rolling(n).sum().tolist()[n])
#             DMminusN.append(df2['DMminus'].rolling(n).sum().tolist()[n])
#         elif i > n:
#             TRn.append(TRn[i-1] - (TRn[i-1]/n) + TR[i])
#             DMplusN.append(DMplusN[i-1] - (DMplusN[i-1]/n) + DMplus[i])
#             DMminusN.append(DMminusN[i-1] - (DMminusN[i-1]/n) + DMminus[i])
#     df2['TRn'] = np.array(TRn)
#     df2['DMplusN'] = np.array(DMplusN)
#     df2['DMminusN'] = np.array(DMminusN)
#     df2['DIplusN']=100*(df2['DMplusN']/df2['TRn'])
#     df2['DIminusN']=100*(df2['DMminusN']/df2['TRn'])
#     df2['DIdiff']=abs(df2['DIplusN']-df2['DIminusN'])
#     df2['DIsum']=df2['DIplusN']+df2['DIminusN']
#     df2['DX']=100*(df2['DIdiff']/df2['DIsum'])
#     ADX = []
#     DX = df2['DX'].tolist()
#     for j in range(len(df2)):
#         if j < 2*n-1:
#             ADX.append(np.NaN)
#         elif j == 2*n-1:
#             ADX.append(df2['DX'][j-n+1:j+1].mean())
#         elif j > 2*n-1:
#             ADX.append(((n-1)*ADX[j-1] + DX[j])/n)
#     df2['ADX']=np.array(ADX)
#     return df2['ADX']


# # Renko Bars

# def renko_DF(DF):
#     "function to convert ohlc data into renko bricks"
#     df = DF.copy()
#     df.reset_index(inplace=True)
#     #df = df.iloc[:,[0,1,2,3,5]]
#     # Rename columns in this order: date, open, high, low, close
#     df.rename(columns = {"Date" : "date", "High" : "high", "Low" : "low", "Open" : "open", "Close" : "close", "Volume" : "volume"}, inplace = True)
#     df2 = Renko(df)
#     df2.brick_size = round(ATR(DF,120)["ATR"][-1],0)
#     renko_df = df2.get_ohlc_data() 
#     return renko_df


# def slope(ser,n):
#     "function to calculate the slope of regression line for n consecutive points on a plot"
#     ser = (ser - ser.min())/(ser.max() - ser.min())
#     x = np.array(range(len(ser)))
#     x = (x - x.min())/(x.max() - x.min())
#     slopes = [i*0 for i in range(n-1)]
#     for i in range(n,len(ser)+1):
#         y_scaled = ser[i-n:i]
#         x_scaled = x[:n]
#         x_scaled = sm.add_constant(x_scaled)
#         model = sm.OLS(y_scaled,x_scaled)
#         results = model.fit()
#         slopes.append(results.params[-1])
#     slope_angle = (np.rad2deg(np.arctan(np.array(slopes))))
#     return np.array(slope_angle)


# def take_profit(df, entry_price, tier_1, tier_2, tier_3):
#     tier_1 = tier_1 / 100
#     tier_2 = tier_2 / 100
#     tier_3 = tier_3 / 100
#     df['long_tp_1'] = entry_price + (entry_price * tier_1)
#     df['long_tp_2'] = entry_price + (entry_price * tier_2)
#     df['long_tp_3'] = entry_price + (entry_price * tier_3)
#     df['short_tp_1'] = entry_price - (entry_price * tier_1)
#     df['short_tp_2'] = entry_price - (entry_price * tier_2)
#     df['short_tp_3'] = entry_price - (entry_price * tier_3)
#     return df

"""
def slope(ser,n):
    '''function to calculate the slope of line connecting a point with n-previous point
     slope assumes a frame with 22 units in the x axis and span of min to max in y axis'''
    y_span = ser.max() - ser.min()
    x_span = 22
    slopes = [i*0 for i in range(n-1)]
    for i in range(n-1,len(ser)):
        y2 = ser[i]
        y1 = ser[i-n+1]
        slope = ((y2-y1)/y_span)/(n/x_span)
        slopes.append(slope)
    slope_angle = (np.rad2deg(np.arctan(np.array(slopes))))
    return np.array(slope_angle)

"""
