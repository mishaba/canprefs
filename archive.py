def next_month_in_list(x, lst):
    for i in lst:
        if (i >= x):
            return i
    # got here, so none higher
    # that means first in calendar list
    return lst[0]
        
#print(next_month_in_list(8, [1,4,7,10]))
#print(next_month_in_list(11, [1,4,7,10]))   
#print(next_month_in_list(11, [2,5,8,11]))   
#print(next_month_in_list(11, [3,6, 9,12])) 
#print(next_month_in_list(12, [2,5,8,11]))  

# If in the same month as me, check the day. If larger, than bump month and try again.
def which_month_by_day(curmonth, curday, curyear, monthlist, ex_day_of_month):
    listmonth = next_month_in_list(curmonth, monthlist)
    # print(listmonth)
    whichyear = curyear
    # usual case is that it's in a different month
    if listmonth != curmonth: 
        if listmonth < curmonth:
            whichyear += 1
        return dt.datetime(whichyear, listmonth, ex_day_of_month)
    
    # it's in the current month, need to check day
        
    # div date still later in current month, so return it    
    if curday < ex_day_of_month:
        return dt.datetime(curyear, curmonth, ex_day_of_month)
    
    # missed it, start search with in the sequence
    curmonth = curmonth + 1
    if curmonth > 12:
        curmonth = curmonth -12
        whichyear += 1
    listmonth = next_month_in_list(curmonth, monthlist)
      

    return dt.datetime(whichyear, listmonth, ex_day_of_month)
    # handle different month than this month (most common case)



print(which_month_by_day(8, 12, 2021, [1,4,7,10]  , 15)) 
print(which_month_by_day(11, 12, 2021, [1,4,7,10]  , 15)) 
print(which_month_by_day(8, 12, 2021, [2,5,8,11]  , 15)) 
print(which_month_by_day(8, 16, 2021, [2,5,8,11]  , 15))     
print(which_month_by_day(11, 16, 2021, [2,5,8,11]  , 15)) 


# This is overly complex; Construct a date including day of month and try it.


def next_payment_date(after_date, month_list, day_of_month) :
    ''' 
    Given a date and a payment rule (month list, date of month) 
    figures out the next  dividend date.

    Example, today is 11/3; dividends are 1,4,7,10, on the 10th. Next dividend 
    is on 1/3, next year

    '''

    after_month = after_date.month
    after_day = after_date.day
    after_year = after_date.year

    
    # if on last day of month, then search next month
    if after_date.day == calendar.monthrange(after_date.year,month)[1] :
        month = next_month(month)
    
    # search the next month
    while (not month in month_list) :
        month = next_month(month)
    
    # found month but it could be following year
    which_year = after_date.year if (month >= after_date.month) else after_date.year+1
    
    return payment_day_last_of_month(which_year, month)


