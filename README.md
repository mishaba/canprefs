# canprefs


Alpha vantage and yfinance pull data in different formats.

It is convenient to have a standard representation.

Let's use the Yahoo dataframe format since 

--------------

Update 8/29/2021

One quick sample of ENB shows that the 8 or so preferred shared trade
at the same YTM (if I computed the YTM) correctly.  That means the
buying public is applying the market spread to the YTM not CY (current
yield).

That YTM is computed conservatively at the current price, I believe.

This means that the market spread needs to be derived from the YTM
average for each ticker, which in turn implies calculation of YTM,
*without* a final price adjustment.


