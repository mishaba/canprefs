
import datetime
import pandas as pd
import pprint
pp = pprint.PrettyPrinter(indent=4)
import json

# Utilities
def is_NVCC(rating):
    return rating.endswith('n')
# Numeric scale for ratings:
# ZR = 99
# Remove 'p'; then NM => 3 * (N-1) + M where M = 0 for H, 1 for I, 2 for L
#  P2H => 3*1 + 0 = 3
#  P3I => 3*2 + 1 = 7
def map_rating_string_to_number(str):
    # print(str)
    if str == 'ZR':
        return 99
    
    if len(str) < 3:
        str += 'I'
        
    level = int(str[1])
    sublevel = str[2]
    if sublevel == 'H':
        offset = 0
    elif sublevel == 'I':
        offset = 1
    elif sublevel == 'L':
        offset = 2
    return (level-1)*3 + offset




# # Warning: grabs historical quotes from file
# def initialize_fr_db_from_file(filename):
#     dfraw = pd.read_pickle(filename)
#     # dfraw.set_index('Ticker', inplace=True)
#     # dfraw.reindex()
#     # Cleanup: remove NVCC
#     df = dfraw.copy()
#     df = df[[not is_NVCC(x) for x in dfraw['Rating'] ]]
#     df['NumRat'] = [map_rating_string_to_number(x) for x in df['Rating']]
#     # Drop Reerence, Par, Mat
#     df.drop(['Reference', 'Par', 'Mat'], axis=1, inplace=True,errors='ignore')
#     df['BidYield']  = [ div/price for (div,price) in zip(df['Div'],df['Bid'])]
#     df['AskYield']  = [ div/price for (div,price) in zip(df['Div'],df['Ask'])]
#     return df



def initialize_fr_db_from_file(pref_json_path):
    df = pd.read_json(pref_json_path,orient='records',lines=True)
    fr = df[df['Class'] == 'Reset'].copy()
    fr.drop(['Maturity Date','Notes 2', 'Class','Code', 'Reference','Mat','Par'], inplace=True, axis=1, errors='ignore')

    return fr


