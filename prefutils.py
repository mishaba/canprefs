import scipy.optimize as optimize

import pandas_datareader as pdr
import datetime 
import pandas as pd
import numpy as np

import pandas_datareader.data as web
import requests_cache
from datetime import date

def bond_ytm(price, par, T, coup, freq=2, guess=0.05):
    freq = float(freq)
    periods = T*freq
    coupon = coup/100.*par/freq
    dt = [(i+1)/freq for i in range(int(periods))]
    def ytm_func(y):
        return(sum([coupon/(1+y/freq)**(freq*t) for t in dt]) +
               par/(1+y/freq)**(freq*T) - price)
        
    return optimize.newton(ytm_func, guess)


def float_dividend_tbill(tbill_rate_in_percent, 
                                 issue_spread_in_bips, par=25.00):
    rate_in_percent = tbill_rate_in_percent + issue_spread_in_bips/100.0;
    dividend = par * rate_in_percent / 100.0
    return dividend

assert(float_dividend_tbill(1.5, 137)== 25 * (1.5 + 137/100)/100)

def float_current_yield(stock_price, tbill_rate_in_percent, issue_spread_in_bips, par=25):
    current_yield =  float_dividend_tbill(tbill_rate_in_percent, issue_spread_in_bips, par)/stock_price
    
    return current_yield


assert(float_current_yield(10.00, 1.6, 340, 25) == 0.125)

def float_market_spread_in_percent(stock_price, tbill_rate_in_percent, 
                                   issue_spread_in_bips, par=25):
    spread = float_current_yield(stock_price, tbill_rate_in_percent, 
                                 issue_spread_in_bips, par) *100 \
               - (tbill_rate_in_percent )
    return spread



float_market_spread_in_percent(15.00, 1.6, 340, 25)

# Predict price of FloatingReset given a new Tbill rate
# with an existing market spread

def declared_dividend(tbill_rate_in_percent, issue_spread_in_bips, par=25):
    declared_yield = (tbill_rate_in_percent + issue_spread_in_bips/100)
    yearly_dividend = declared_yield / 100 * par
    return yearly_dividend

# disallow any market spread below 1%. Otherwise people will just buy Tbills

MINIMUM_MARKET_SPREAD = 0.9

def float_price_given_tbill_and_market_spread(tbill_rate_in_percent,
                                              market_spread_in_percent, 
                                              issue_spread_in_bips, par=25, refi_max=0.75):

  
    # Clamp market spread to 0.9
    eff_market_spread_in_percent = max(market_spread_in_percent,MINIMUM_MARKET_SPREAD)
    
    yearly_dividend = declared_dividend(tbill_rate_in_percent, issue_spread_in_bips, par)
    demanded_yield_in_percent = tbill_rate_in_percent + eff_market_spread_in_percent
    price = yearly_dividend/demanded_yield_in_percent*100
   #  print(yearly_dividend, demanded_yield_in_percent, price)

    # Clamp price at a point at which a CFO would refinance
    price = min(price,par+refi_max)
    return price


# float_price_given_tbill_and_market_spread(1.4, 6.2, 418,25)

def float_capital_gain_given_tbill_and_market_spread(current_price, 
                                                    tbill_rate_in_percent,
                                                     market_spread_in_percent,
                                                    issue_spread_in_bips,
                                                    par=25):
    new_price = float_price_given_tbill_and_market_spread(tbill_rate_in_percent,
                                                          market_spread_in_percent,
                                                         issue_spread_in_bips,
                                                         par)
    capital_gain_in_dollars = (new_price - current_price)
    return capital_gain_in_dollars

    
# cap_gain = float_capital_gain_given_tbill_and_market_spread(18.60, 1.4, 6.1943, 418,25)

def net_gain_cg_and_dividend(num_years, current_price, tbill_rate_in_percent,
                            market_spread_in_percent, issue_spread_in_bips, par=25) :
    cap_gain = float_capital_gain_given_tbill_and_market_spread(current_price,
                                                                tbill_rate_in_percent,
                                                                market_spread_in_percent,
                                                                issue_spread_in_bips,
                                                                par=25)
    dividend_gain= num_years * declared_dividend(tbill_rate_in_percent,
                                                 issue_spread_in_bips,par)
    # print("Cap Gain: ", cap_gain)
    # print("Div Gain:", dividend_gain)
    return cap_gain + dividend_gain


# net_gain = net_gain_cg_and_dividend(1, 18.60, 1.4, 6.1943, 418,25)

# computes total gain of a preferred share over a number of years.
# this includes the predicted capital gain (or loss), plus the dividend income

def annualized_gain_cg_and_dividend_decimal(num_years, current_price, tbill_rate_in_percent,
                            market_spread_in_percent, issue_spread_in_bips, par=25) :
    net_gain =  net_gain_cg_and_dividend(num_years, current_price,
                                                                tbill_rate_in_percent,
                                                                market_spread_in_percent,
                                                                issue_spread_in_bips,
                                                                par=25)
    # print("Net Gain: ", net_gain)
    net_gain_decimal = net_gain/current_price;
    # print("Net Gain Decimal", net_gain_decimal)
    annualized_gain = (1+net_gain_decimal) ** (1/num_years) - 1
    # print("Annualized", annualized_gain)
    return annualized_gain


# annualized_gain_cg_and_dividend_decimal(2,18.6,1.4,6.2,418)




# define 3 scenarios, with corresponding probabilities and names.
# Name: {tbillrate, number of years, probability}
TBILL_SCN = { 
    "Constant" :  (1.66, 1, 0.15),
    "SlightDrop": (1.40, 1, 0.45),
    "BigDrop":    (1.10, 1, 0.25) ,
    "Panic":      (0.70, 1, 0.15)}


SPREAD_ADJUST = {
    "SLF.PR.J" : -0.2,
    "SLF.PR.K" : -0.2
}


# Apply a constant market spread delta to each value. 
# Enable hack mode which adjusts on a per-security basis

def create_tbill_scenarios_from_mspread(mspread_delta,df, enable_hack=False) :
    df["EffMSpread"] = [max(x  + mspread_delta, MINIMUM_MARKET_SPREAD) for x in df["MSpread"]]
    
   
    
    if enable_hack:
        adjust_hack = df['Ticker'].map(SPREAD_ADJUST).fillna(value=0)
        df['EffMSpread'] += adjust_hack
        
        
    df["MSpread_Delta"] = mspread_delta
    df["Expected_Gain"] = 0.0
    
    for scn_name,(rate,years,probability) in TBILL_SCN.items() :
        
        df[scn_name] = [annualized_gain_cg_and_dividend_decimal(years, price, rate, 
                                                 mspread,spread) for (price,mspread,spread) in
                zip(df['Price'], df['EffMSpread'], df['Spread'])]
        df['Expected_Gain'] += (df[scn_name] * probability)
        
        
        df['Price'+scn_name] =[float_price_given_tbill_and_market_spread(rate,
                                              effmspread, spread) for (effmspread,spread) in
                               zip(df['EffMSpread'],df['Spread'])]
    return df


  

def convert_ticker_to_yahoo(orig): 
    splits = orig.split('.')
    result = splits[0] + "-p" + splits[2] + ".TO"
    return result


def fetch_last_close_in_dollars(standard_ticker) :
    ticker = convert_ticker_to_yahoo(standard_ticker)
    df = pdr.get_data_yahoo(ticker, start=datetime.datetime(2019,12,31),end= date.today())
    last_close = pd.Series(df['Adj Close'])[-1]
    return round(last_close,2)



