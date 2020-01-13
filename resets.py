# Resets calculations

from xirr import xirr 
import datetime as datetime
from prefutils import *

import pandas_datareader as pdr
import datetime 
import pandas as pd
import numpy as np

import pandas_datareader.data as web
import requests_cache
import matplotlib.pyplot as plt
from datetime import date






# for now, ignore market holidays
def payment_day_last_of_month(year, month) :
    days_in_month = monthrange(year,month)[1]
    return datetime.datetime(year,month,days_in_month)

def next_month(x) :
    return 1 if x>= 12 else x+1

def next_payment_date_after_date(after_date, month_list) :
    month = after_date.month
    # if on last day of month, then search next month
    if after_date.day == monthrange(after_date.year,month)[1] :
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

    if eval_date < reset_date :
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
    yield_at_reset = (estimated_goc5_at_reset_decimal + issue_reset_spread_bips/10000) 
    return par*yield_at_reset



