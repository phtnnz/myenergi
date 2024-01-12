# From https://myenergi.info/extracting-energy-data-t7445-s90.html
# User healthily

import requests
from requests.auth import HTTPDigestAuth
import pandas as pd
from datetime import datetime as dt

today = pd.Timestamp.today().floor('D') # The start of today's date (midnight)
yesterday = today - pd.tseries.offsets.Day(1) # The start of yesterday's date

# Credentials
server = 's18' # Server number allocation is a mystery to me
username = 'xxx' # Numerical username provided as a string
password = 'xxx'
ID = 'Z' + username # 'E' because I have an Eddi; this may need changing to a 'Z' for a Zappi

headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

def process_df(df):
    date_cols = ['yr','mon','dom','hr','min'] # Columns in the order that generates the date
    df['datetime'] = df[date_cols].fillna(0).astype(int).apply(lambda x:dt(*x),axis=1)

    # Energy diverted into our two Eddi heaters, which may not be present in the download if not used
    eddi_cols = [c for c in ['h1d','h2d'] if c in df.columns]
    if len(eddi_cols):
        df['Eddi'] = df[eddi_cols].sum(axis=1)
    else:
        df['Eddi'] = 0

    # Renaming columns to be more user-friendly
    cols = {
        'gep': 'Generation',
        'imp': 'Imported',
        'exp': 'Export',
        'Eddi':'Eddi'
    }

    return (df.rename(columns=cols) # Rename columns
        # .drop(date_cols + eddi_cols + ['dow','gen','hsk','v1','frq'],axis=1) # Remove those not required
        .drop(date_cols + eddi_cols + ['dow','v1','frq'],axis=1) ## MJ: fixed KeyError: "['gen', 'hsk'] not found in axis"
        .set_index('datetime') # Set the time as the index column, leaving only energy in the dataframe
        .fillna(0) # Fill any blank cells with zero
        .div(3600000) # Convert the energy from Watt-seconds to kWH
    )

def get_data(session,day):
    url = f'https://{server}.myenergi.net/cgi-jday-{ID}-{day:%Y-%m-%d}'
    r = session.get(url, timeout=20)
    df = pd.DataFrame(r.json()[f'U{username}'])
    df = process_df(df)
    return df

with requests.Session() as s:
    s.auth = HTTPDigestAuth(username,password)
    s.headers.update(headers)

    # Collects dataframes for each day from yesterday to today (part-complete) and combines them
    df = pd.concat([get_data(s,day) for day in pd.date_range(yesterday,today,freq='D')])

# Aggregates data into half-hour chunks and exports as a CSV
# df.resample('30min').sum().to_csv("./test.csv")

# Dates written to CSV are UTC!
df.resample('1H').sum().to_csv("./test.csv")

# Other summarisation options include S for seconds, T/min for minutes, H for hours, D for days, W for weeks, etc