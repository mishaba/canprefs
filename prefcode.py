# prefcode

import yfinance as yf
import json
import pandas as pd



def setup_databases(preffile="./floats.csv", ratingsfile="./ratingsdb.json", 
                        interestfile="./interest_rates.json"):
    df = pd.read_csv(preffile)
    # Read the ratings database
    with open (ratingsfile) as f:
        ratings_db = json.load(f)
    # Read the interest rate database
    with open (interestfile) as f:
        interest_db = json.load(f)
    update_ratings_from_db(df, ratings_db)
    # drop NVCC items. Hack for now
    df.drop(df[df['Rating'] == 'P2In'].index,inplace=True)
    return df, interest_db



# Update each ticker's ratings from ratings DB
# There may be a more string-comphensiony way of doing this


def lookup_rating_by_ticker(ticker, rating_database):
    company_ticker =  ticker.split(".",1)[0]
    return rating_database.get(company_ticker)


    
def update_ratings_from_db(df, rating_database):
    '''
    Updates a preferred database from the per0company database
    '''
    df["Rating"] = [lookup_rating_by_ticker(pref_ticker, rating_database) for pref_ticker in df["Ticker"]]
                    

    # Update closing prices
def fetch_prices(df, session, fetch=True):
    price_col = 'RefPrice'
    if fetch:
        update_closing_prices(df,session)
        df.drop(columns=['RefPrice'],inplace=True,errors='ignore')
    else:
        df.rename(columns={"RefPrice": "Price"})
        
    return df
        

# Update yields
def compute_annual_dividend(preftype, spread, mult, rates, faceval=25):
    if preftype == 'P':
        rate_percent = rates['prime']*mult
    else:  # assume spread
        rate_percent = rates['tbill'] + spread/100 
    dividend = round(rate_percent/100 * faceval, 4)
    return dividend


def update_div_and_yield(df, interest_db, price_column='Price'):
    '''
    Creates columns 'AnnualDiv' and 'CurYieldPct'.
    '''
    
    df["AnnualDiv"] = [compute_annual_dividend(ptype,spread,mult,interest_db)
                       for (ptype,spread,mult) in 
                       zip(df["Type"],df["Spread"],df["Mult"])]
    df["CurYieldPct"] = [round(div / price *100,4) for (div,price) in zip(df["AnnualDiv"],df[price_column])]

    return df



def convert_std_ticker_to_yahoo(ticker, exception_db={}):
    # check for exceptions here
    pieces = ticker.split(".")
    return pieces[0]+'-P'+pieces[2]+'.TO'


def extract_close_from_yfinance(data):
    return round(data.iloc[-1]['Close'],2)


def update_closing_prices(df, session):
    for i in df.index:
        pref_ticker = df.at[i,"Ticker"]
        yticker = convert_std_ticker_to_yahoo(pref_ticker)
        data = yf.download(tickers=yticker,
                       period='5d',interval='1d',
                           progress=False,
                           rounding=True,
                           session=session)
        if data.size > 0:
            close = extract_close_from_yfinance(data)
        else:
            close = 666
        df.at[i,'Price'] = close
        # print(pref_ticker, yticker, close)
    return df

## =======================================


def select_benchmark_rate(type, interest_db):
    if type == 'T':
        return interest_db['tbill']
    else:
        return interest_db['prime']

    

# Naming conventions: update_XXX means update data frame in place
#                   : calc means a pure math function that can be tested

def calc_market_spread(curyield, benchmark):
    return curyield - benchmark

def update_market_spread(df, interest_db):
    df['MSpread'] = [ calc_market_spread(curyield, select_benchmark_rate(type, interest_db))
                     for (curyield, type) in
                     zip(df["CurYieldPct"], df["Type"])]
    return df



def price_from_demand_yield(ref_rate_pct, mspread_pct, spread_bips, par=25):
    dividend = dividend_from_reference_and_issue_spread(ref_rate_pct, spread_bips)
    new_yield_pct = ref_rate_pct  + mspread_pct
    price = dividend / (new_yield_pct / 100)
    return price

# This is all for one year; we can get fancy and annualize later

PAR_OFFSET_LIMIT = 0.50

def eff_yield_inc_capgain(future_tbill_pct, spread_bips, mspread_pct, price, current_div, par=25, verbose=True):
    future_price = price_from_demand_yield(future_tbill_pct, mspread_pct, spread_bips)
    if future_price > (par + PAR_OFFSET_LIMIT):
        print("Future Price clamped: ", future_price)
        future_price = par + PAR_OFFSET_LIMIT
        
    cap_gain = future_price - price
    total_income = current_div + cap_gain
    effective_yield = total_income / price
    return effective_yield


# For now, keep as 1 year  
def update_effective_yield(tdf, future_tbill, scn_name):
    scn = scenario_to_label(scn_name)
    tdf[scn] = [round(eff_yield_inc_capgain(future_tbill, spread_bips,
                                                            mspread_pct, price, current_div)*100, 4) 
                        for (spread_bips, mspread_pct, price, current_div)
                            in
                            zip(tdf['Spread'],tdf['MSpread'],tdf['Price'], tdf['AnnualDiv'])]

# Generate one yield column per scenario
def update_columns_by_scenarios(mydf, scenarios):
    for scn_name, scenario in scenarios.items():
        scenario_rate = scenario[0]
        update_effective_yield(mydf, scenario_rate, scn_name)
    
    
def calc_weights(row, scen):
    weighted_sum = 0
    for code, scenario in scen.items():
        scn_name = code + "_Yield"
        prob = scenario[1]
        weighted_sum += (row[scn_name] * prob)
    return weighted_sum
  
def update_expected_yield_column_from_scen_columns(tdf, scen, colname='ExpYield'):   
    tdf[colname] = tdf.apply(lambda row: calc_weights(row, scen), axis=1)

# Put it all together
def update_expected_yield(df, scenarios):
    update_columns_by_scenarios(df, scenarios)
    update_expected_yield_column_from_scen_columns(df, scenarios)



def scenario_to_label(scn):
    return scn + '_Yield'


    
## ====================================

from prefutils import *



## ====================================

## Snippets

def calculate_avg_yield_per_rating(df):
    foo = pd.pivot_table(data=df,
                         index=['Rating'],
                         values='CurYieldPct',
                         aggfunc=['mean','count'])
    return foo


#==============

# Build up test functions. There is a bug in computing the .018 yield (same as today; should be no change)
def test_mspread():
    # Use PWF.PR.Q
    curyield_pct = 2.69
    preftype = "T"
    benchmark = select_benchmark_rate(preftype, {"prime": 666, "tbill": 0.183})
    mspread = calc_market_spread(curyield_pct, benchmark)
    
    result = (mspread == 2.507)
    print(mspread, result)    
    return result

#test_mspread()

def test_future_price():
    future_price = price_from_demand_yield(0.183, 2.4865, 160)
    future_price = round(future_price, 3)
    result = (future_price == 16.698)
    print(future_price, result)
    return result

# test_future_price()

# ================================
# Attempt at portfolio construction
# do not use. Turns out best answer is using the overall winner
# Now, is the best strategy to bet on the overall robust winner, or allocate to the best performer
# across the board, or perhaps a different mixture (goal optimized).
#
# We know the answer in the "Focus" scenario, we buy SLF.PR.J, and we have the expectation.
# Now, check out diversification

# First, build a portfolio from the best candidate in each scenario

def summarize_best_by_column(df, colname='CurYieldPct'):
    return  df[df[colname] == df.groupby('Rating')[colname].transform('max')]


def create_portfolio_best_in_class(mydf, rating, scenarios):
    portfolio = {}
    for name, config in scenarios.items():
        # down select by rating
        rdf = mydf[mydf['Rating'] == rating]
        scen_name = scenario_to_label(name)
        best_tickers = summarize_best_by_column(rdf,scen_name)
        best_ticker = best_tickers.iloc[0]['Ticker']
        # assign weight based on probability
        portfolio[best_ticker] = config[1] 
    return portfolio

# stress test portfolio
def portfolio_return(mydf, port, scenario):
    result = 0;
    scn_name = scenario_to_label(scenario)
    for ticker,weight in port.items():
        ticker_yield = ticker_return_scenario(mydf, ticker, scn_name)
#        print(ticker, ticker_yield)
        result = result + (ticker_yield * weight)
    return result
    

def ticker_return_scenario(df, ticker, scenario_name):
    tmp_df = df[df['Ticker'] == ticker]
    return tmp_df.iloc[0][scenario_name]

def calc_portfolio_returns_weighted(mydf, portfolio, scenarios):
    exp_return = 0;
    for name, config in scenarios.items():     
        result = portfolio_return(mydf, portfolio, name)
        probability = config[1]
 #       print(name, probability, result)
        exp_return += (result * probability)
    return exp_return


def make_portfolio_recommendation(tdf, rating, scenarios):
    portfolio = create_portfolio_best_in_class(tdf, rating, scenarios)
    diversified_return = calc_portfolio_returns_weighted(tdf, portfolio, scenarios)

    best_overall = summarize_best_by_column(tdf, 'ExpYield')
    best_overall_rating = best_overall[best_overall['Rating'] == rating]
    best_row = best_overall_rating.iloc[0]

    focus_return = best_row['ExpYield']
    focus_ticker = best_row['Ticker']

    print("Rating: ", rating)
    #print("Diversified return: ", portfolio, diversified_return)
    #print ("Focus return: ", focus_ticker, focus_return)

    if (focus_return > diversified_return):
        print("Allocate to only: ", focus_ticker, focus_return , " > " ,diversified_return)
    else:
        print("Allocate to diversified. ", portfolio, focus_return , " < " ,diversified_return)


        
# Evaluate different interest rate scenarios.
# Reuse some of the older code
# Algorithm:
# 1. Recalculate new dividend given a new T-bill rate.  
# 2. Create target yield rate (new T + market spread)
# 3. Calculate share price needed to achieve the yield
# 4. Compute resulting capital gain
# 5. Combine into "TotYield"
# For now, assume 1 year outlook to eliminate need for annualizing
