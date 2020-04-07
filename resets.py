# Resets calculations

from xirr import xirr 
import datetime as datetime
from prefutils import *

import pandas_datareader as pdr

import calendar as calendar
import pandas as pd
import numpy as np

import pandas_datareader.data as web
import requests_cache
import matplotlib.pyplot as plt
from datetime import date

import pprint as pp

def month_cycle_from_start_month(letter):
    if letter == "J":
        return [1,4,7,10]
    elif letter == "F":
        return [2,5,8,11]
    else:
        return [3,6,9,12]
    



# for now, ignore market holidays
def payment_day_last_of_month(year, month) :
    days_in_month = calendar.monthrange(year,month)[1]
    return datetime.datetime(year,month,days_in_month)

def next_month(x) :
    return 1 if x>= 12 else x+1

def next_payment_date_after_date(after_date, month_list) :
    month = after_date.month
    # if on last day of month, then search next month
    if after_date.day == calendar.monthrange(after_date.year,month)[1] :
        month = next_month(month)
    
    # search the next month
    while (not month in month_list) :
        month = next_month(month)
    
    # found month but it could be following year
    which_year = after_date.year if (month >= after_date.month) else after_date.year+1
    
    return payment_day_last_of_month(which_year, month)


# Expects final price to be determined externally

def build_cashflow_list(purchase_date, purchase_price, reset_date, maturity_date, maturity_price,
                        payment_months, 
                        current_dividend_annual, reset_dividend_annual) :
    group = []
    next_date = next_payment_date_after_date(purchase_date, payment_months)

    while (next_date < maturity_date) :
        group.append(next_date)
        next_date = next_payment_date_after_date(next_date, payment_months)   
    
    # walk date list; if before reset, use current, otherwise reset
    div_q = current_dividend_annual/4
    pr_div_q = reset_dividend_annual/4

    def which_payment(pbefore, pafter, curdate, breakdate) :
        return pbefore if curdate <= breakdate else pafter

    cashflows = [ (x, which_payment(div_q, pr_div_q, x, reset_date)) for x in group ]

    def add_initial_purchase_cashflow(date_cash_list, purchase_date, purchase_price):
        date_cash_list.insert(0,(purchase_date, -1 * purchase_price))
    
    def add_maturity_sale_cashflow(date_cash_list, maturity_date, maturity_price):
        date_cash_list.append((maturity_date, maturity_price))

    add_initial_purchase_cashflow(cashflows, purchase_date, purchase_price)

    add_maturity_sale_cashflow(cashflows, maturity_date, maturity_price)

    return cashflows

# ======================================================================================
    


def csv_to_date(dstr) :
    ds = dstr.split('/')  
    if len(ds[1]) < 4 :
        ds[1] = "20" + ds[1]
    isoformat = ds[1] + "-" + ds[0] + "-15"
    return datetime.datetime.fromisoformat(isoformat)


def year_frac_from_today(reset_date_str) :
    reset_date = csv_to_date(reset_date_str)
    today = datetime.datetime.today()
    time_diff = reset_date - today
    num_days = time_diff.days
    return num_days/365


def dividend_after_reset(issue_reset_spread_bips, goc5_at_reset_decimal, par=25) :
    yield_at_reset = (goc5_at_reset_decimal + issue_reset_spread_bips/10000) 
    return par*yield_at_reset



# ======================================================================================

# Here we go: compute YTM from some GOC5 at some reset date

# Approach:

# 1. Compute share price at maturity.  Assume that price stays constant prior to reset date. After the reset
#    date, share price will adjust based on the new dividend, prevailing GOC5 at the time, and the demanded
#    market spread at maturity


def compute_ytm(cur_date, curprice, curdiv, reset_date,
                  ir_spread_bips, 
                  mspread_percent, maturity_goc5_percent, 
                future_div,
                maturity_date, month_cycle, verbose=False) :

    if maturity_date < reset_date:
        maturity_price = curprice
    else:
        maturity_price = share_price_given_ref_rate_and_market_spread(
            maturity_goc5_percent, mspread_percent, ir_spread_bips)
    
    
    flows = build_cashflow_list(cur_date, curprice, 
                            reset_date, 
                            maturity_date,
                            maturity_price,
                            month_cycle,
                            curdiv, 
                            future_div)
    if verbose:
        pp.pprint(flows)
        print("Future Div (int): ", future_div)
        print("Maturity Price : ", maturity_price)
        print("Maturity Date: ", maturity_date)
        print("Reset  Date: ", reset_date)
    
    return xirr(flows, 0.2)



# ============
# Notice:
# cliffdays = 0 means always use current spread (zero predictive power)
# cliffdays = 10 years, means always use future div for market

def compute_ytm_cliff(cliff_days,cur_date,curprice, curdiv, 
                     reset_date, ir_spread_bips,
                    mspread_percent, future_goc5_percent,
                      maturity_date, month_cycle, curgoc5_percent, verbose=False): 
    
    future_div = dividend_after_reset(ir_spread_bips, future_goc5_percent/100)
    
    if ((reset_date-cur_date).days > cliff_days)  :
        # Too far away; use current market spread
        which_mspread_percent = mspread_percent
    else:
        # Anticipated: use future dividend to compute market spread
        # notice the alternate Market Spread is computed using the CURRENT GOC5
        # the assumption is that participants aren't guessing as to the future GOC5.      

        which_mspread_percent = market_spread_from_dividend_in_percent(
                            curprice, future_div, curgoc5_percent)  

    if verbose:
        print("MSpread: ", which_mspread_percent)
    ytm = compute_ytm(cur_date,
                      curprice, # Current price
                      curdiv, # Current div
                      reset_date,
                      ir_spread_bips,
                      which_mspread_percent,  # MSpread in Percent
                      future_goc5_percent,   # Future GOC5
                      future_div,
                      maturity_date,
                      month_cycle,
                      verbose)
    return ytm


##  Fixed reset equivalents to all this

## Process
## 1. For a given market spread, calculate GOC5 scenarios
## 2. Adjust each ticker

GOC5_SCN = { 
    "Constant" :  (0.88,  0.10)
#   "SlightRise": (1.80,  0.10),
#    "Drop":       (1.30,  0.30) ,
#    "Panic":      (0.90,  0.20)
}



# Resets are odd: their market spread is dependent on a variety of fields, rather than
# the current market spread.
#
# Model C6 : 6-month cliff.   
# Model C0:  0-month cliff
# Model M:   reversion to mean
#
# Generalize:  cliff = 0: means only 
# CURRENT_GOC5_PERCENT = 1.58



def create_freset_scenarios(df, maturity_date, scenarios, ms_model, cliff_days,
                            current_goc5_percent,
                            enable_hack=False, minspread=MINIMUM_TBILL_MARKET_SPREAD) :
    df["EffMSpread"] = [max(x, minspread) for x in df["MSpread"]]
    
    if enable_hack:
        adjust_hack = df['Ticker'].map(SPREAD_ADJUST).fillna(value=0)
        df['EffMSpread'] += adjust_hack

        
    df["Expected_YTM"] = 0.0

    today = datetime.datetime.today()


    # configure parameters based on model type
    # C means Cliff
    if ms_model == "C":
        eff_cliff_days = cliff_days
        which_mspread_col = "MSpread"
    # M means market_spread mean reversion
    elif ms_model == "M":
        eff_cliff_days = 0 # use given mspread
        which_mspread_col = "AvgSpread"
    else:
        print("Unknown Model: ", ms_model)
        return
    

    # Tag for aggregating
    df["Model"] = ms_model + str(cliff_days)   
    
    for scn_name,(futgoc5_percent,probability) in scenarios.items() :
       
            
        df[scn_name] = [
            compute_ytm_cliff(eff_cliff_days, # number of days before cliff
                              today ,
                              curprice, # Current price
                              curdiv, # Current div
                              reset_date,
                              reset_spread_bips, # Bips
                              mspread_percent,  # MSpread in Percent
                              futgoc5_percent,   # Future GOC5
                              maturity_date ,
                              month_cycle,
                              current_goc5_percent
            )
            for
            (curprice, curdiv, reset_date, reset_spread_bips, mspread_percent, month_cycle)
            in
            zip(df['Price'],df['Div'],df['ResetDT'],df['Spread'],
                df[which_mspread_col],df['Cycle'])
            ]
        
        df['Expected_YTM'] += (df[scn_name] * probability)
        
    return df




# This version is more manual than the tbill
    
def create_freset_scenarios_per_market_spreads(df, maturity_date, current_goc5, goc5_scenarios, freset_models) :

    foo = pd.concat([
        create_freset_scenarios(df.copy(), maturity_date,  goc5_scenarios, ms_model, cliff_days, current_goc5) 
        for (ms_model,cliff_days)
        in  freset_models], axis=0)
        
    foo.reset_index(drop=True, inplace=True)
    return foo



# Ranking section

def do_the_ranking_freset(xdf, goc5_scenarios, ranks_to_keep):

    scenario_names = goc5_scenarios.keys()
    # print(scenario_names)
    rank_names = ['Rank' + x for x in scenario_names]
    #  print(rank_names)
    
    def rank_group(df):
        for rank_name,scenario_name in zip(rank_names, scenario_names):
            list_of_largest_n_values = df[scenario_name].nlargest(n=ranks_to_keep).values
            df[rank_name] = [1 if x in list_of_largest_n_values else 0 
                             for x in df[scenario_name]]
        df['RankSum'] = df[rank_names].sum(axis=1)
        return df

    ranked = xdf.groupby(['Model']).apply(rank_group)
    ranked[(ranked['RankSum']) > 0 ][
       ['Ticker','Model','RankSum'] + rank_names].sort_values(
           by='Ticker')

     
    baz = ranked[['Ticker','RankSum','Expected_YTM']].groupby(['Ticker']).agg(
       TotalRankSum=('RankSum','sum'),AvgExpectedYTM=('Expected_YTM','mean')).reset_index().sort_values(by='AvgExpectedYTM',ascending=False)

    return baz

# Wait, something is wrong. Why does AIM.PR.A increase YTM as GOC5 falls??? Ditto TRP.PR.G

# Why does TRP.PR.E not care about scenario (oh, reset date is 4 years out)

## Manual debugging section

