# Resets calculations

from xirr import xirr 
import datetime as datetime
from prefutils import *

import pandas_datareader as pdr
import datetime as datetime
import calendar as calendar
import pandas as pd
import numpy as np

import pandas_datareader.data as web
import requests_cache
import matplotlib.pyplot as plt
from datetime import date






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

    if maturity_date < reset_date :
        final_price = cur_price
    else:
        final_price = maturity_price
        
    add_maturity_sale_cashflow(cashflows, maturity_date, final_price)

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

# OK, here's the big YTM calculation for a given scenario


# Here we go: compute YTW from some GOC5 at some reset date
def compute_ytm(cur_date, curprice, curdiv, reset_date,
                  ir_spread_bips, 
                  mspread_percent, future_goc5_percent, 
                future_div,
                maturity_date, month_cycle, verbose=False) :
    
    # compute future price, which will be 
    
    future_price = share_price_given_ref_rate_and_market_spread(
        future_goc5_percent, mspread_percent, ir_spread_bips)
    
    
    flows = build_cashflow_list(cur_date, curprice, 
                            reset_date, 
                            maturity_date, future_price,
                            month_cycle,
                            curdiv, 
                            future_div)
    if verbose:
        # pp.pprint(flows)
        print("Future Div (int): ", future_div)
        print("Future Price : ", future_price)
    
    return xirr(flows, 0.2)



# ============

##  Fixed reset equivalents to all this

## Process
## 1. For a given market spread, calculate GOC5 scenarios
## 2. Adjust each ticker

GOC5_SCN = { 
    "Constant" :  (1.58,  0.10)
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

CURRENT_GOC5_PERCENT = 1.58

def create_freset_scenarios(df, scenarios, ms_model, enable_hack=False, minspread=MINIMUM_TBILL_MARKET_SPREAD) :
    df["EffMSpread"] = [max(x, minspread) for x in df["MSpread"]]
    
    if enable_hack:
        adjust_hack = df['Ticker'].map(SPREAD_ADJUST).fillna(value=0)
        df['EffMSpread'] += adjust_hack
        
    df["Expected_Gain"] = 0.0

    # for now, ignore 'which model'

    # For each scenario, compute yield to maturity

    today = datetime.datetime.today()
    maturity_date = today+datetime.timedelta(days=365*5)
    month_cycle = gwo_months # GLOBAL!
    
    
    for scn_name,(futgoc5_percent,probability) in scenarios.items() :
        scenario_ytm = 'YTM'+scn_name
        
        df[scenario_ytm] = [
            compute_ytm_cliff(30*6, # number of days before cliff
                              today ,
                              curprice, # Current price
                              curdiv, # Current div
                              reset_date,
                              reset_spread_bips, # Bips
                              mspread_percent,  # MSpread in Percent
                              futgoc5_percent,   # Future GOC5
                              maturity_date ,
                              month_cycle)
            for
            (curprice, curdiv, reset_date, reset_spread_bips, mspread_percent)
            in
            zip(df['Price'],df['Div'],df['ResetDT'],df['Spread'],df['MSpread'])
            ]
        
            
        df['Expected_Gain'] += (df[scenario_ytm] * probability)
        
    return df





