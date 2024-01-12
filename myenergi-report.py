# From https://myenergi.info/extracting-energy-data-t7445-s90.html
# User xtommy21

# Extract data from cgi-day call to myenergi server
# Chris Horne 04/12/2022
# Modified by Brad McGill 7/4/2023 to collect hourly data and export a slightly differnt format
#                                  Also added Timezone adjustment code
#                                  I did not complete the Eddi section as I do not have an Eddi to test with, removed section
#                                  New requirement for pytz package, run "pip install pytz" to install this.
# Modified by Mike Sanders 18/4/2023 to collect hourly data for Eddi and export as a CSV
#                                  Also modified so that Date/Time/number of hours are now user input rather than hard coded values.
#                                  I left Brad's Zappi section alone as I don't have an Zappi to test with
# Modified by Tamas Solymos 13/8/2023 refactored to read better, converted for monthly summaries (DST and timezone) aware
import requests
import json
import datetime
#import dateutil ## MJ: not required
from requests.auth import HTTPDigestAuth
#import numpy as np ## MJ: not required
import pytz
from calendar import monthrange

#------- Device information -------#
# Hub/gateway device serial number
username = "xxx"
# API key generated on https://myaccount.myenergi.com/location#products
password = "xxx"
# "E" for Eddi, "Z" for Zappi, and the serial number
ID = "Zxxx"

#------- Execution -------#

def extract_values(obj, key):
    """Pull all values of specified key from nested JSON."""
    arr = []
    def extract(obj, arr, key):
        """Recursively search for values of key in JSON tree."""
        if isinstance(obj, dict):
            v1 = 0
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract(v, arr, key)
                elif k == key:
                    v1 = v
            arr.append(v1)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    results = extract(obj, arr, key)
    return results

today = datetime.date.today()
local_year  = int(input("Year (default: this year): ") or today.year)
local_month = int(input("Month (default: this month): ") or today.month)

# Hardcoded starting day and hour for monthly reports, all in local timezone
local_day  = 1 #input("From Day (default: '1'): ") or 1
local_hour = 0 #input("From Hour (default: '0'): ") or 0

# Convert start date and time to UTC
timezone = pytz.timezone('Europe/Berlin')
start_datetime = datetime.datetime(local_year, local_month, local_day, local_hour)
start_datetime_local = timezone.localize(start_datetime)
start_datetime_utc = start_datetime_local.astimezone(pytz.utc)
utc_year  = start_datetime_utc.year
utc_month = start_datetime_utc.month
utc_day   = start_datetime_utc.day
utc_hour  = start_datetime_utc.hour

# Calculate hours in the month, which is not trivial with DST involved
start_next_month = datetime.datetime(local_year + (local_month // 12), (local_month % 12) + 1, local_day, local_hour)
start_next_month_local = timezone.localize(start_next_month)
num_hours = round((start_next_month_local - start_datetime_local).total_seconds() / 60 / 60)

# Echo setup
print()
print("Username/Hub Serial Number: " + username)
print("Password: " + str(len(password)) + " chars")
print("Device serial number: " + ID)
print("Collecting " + str(num_hours) + " hours starting from: " + str(local_year) + "-" + str(local_month).zfill(2) + "-" + str(local_day).zfill(2) + " " + str(local_hour).zfill(2) + ":00")
print("Timezone:", timezone)

filename = "MyEnergi_Data_" + str(local_year) + "-" + str(local_month).zfill(2) + ".csv"
print("Saving to: " + filename)

fo = open(filename,"w")
fo.write("Date (DD-MM-YYYY),Import (kWh),Export (kWh),Generation (kWh),Eddi Energy (kWh),Self Consumption (kWh),Total Property Usage (kWh),Green Percentage\n")

url = 'https://s18.myenergi.net/cgi-jdayhour-' + ID + '-' + str(utc_year) + '-' + str(utc_month) + '-' + str(utc_day) + '-' + str(utc_hour) + '-' + str(num_hours)
print("URL: " + url + "\n")

headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
r = requests.get(url, auth = HTTPDigestAuth(username,password), headers = headers, timeout = 60)

if r.status_code == 200:
    if ID[0] == 'E':
        print ('*** Success - Eddi ***')
        data = json.loads(r.content)
        data = data['U' + ID[1:]]
        for d in data:
            hr  = int(d.get('hr') or 0)
            yr  = int(d.get('yr') or 0)
            mon = int(d.get('mon') or 0)
            dom = int(d.get('dom') or 0)

            y_import = float(d.get('imp') or 0) / (60 * 1000)
            y_exp = float(d.get('exp') or 0) / (60 * 1000)
            y_gep = float(d.get('gep') or 0) / (60 * 1000)
            y_z1  = float(d.get('h1d') or 0) / (60 * 1000)
            y_z2  = float(d.get('h2d') or 0) / (60 * 1000)
            y_z3  = float(d.get('h3d') or 0) / (60 * 1000)
            y_z1b = float(d.get('h1b') or 0) / (60 * 1000)
            y_z2b = float(d.get('h2b') or 0) / (60 * 1000)
            y_z3b = float(d.get('h3b') or 0) / (60 * 1000)
            y_eddi = y_z1 + y_z2 + y_z3 + y_z1b + y_z2b + y_z3b

            hourly_import = y_import / 60
            hourly_export = y_exp / 60
            hourly_generation = y_gep / 60
            hourly_eddi = y_eddi / 60

            hourly_self_consumption = hourly_generation - hourly_export
            hourly_property_usage   = hourly_import + hourly_self_consumption
            hourly_green_percentage = (hourly_self_consumption / hourly_property_usage) * 100

            # Convert from UTC
            dt = datetime.datetime(yr,mon,dom,hr)
            dtutc = dt.replace(tzinfo = pytz.utc)
            localdt = dtutc.astimezone(timezone)

            str_out = f'{localdt.day}-{localdt.month}-{localdt.year} {localdt.hour:02d}:00,{hourly_import:.2f},{hourly_export:.2f},{hourly_generation:.2f},{hourly_eddi:.2f},{hourly_self_consumption:.2f},{hourly_property_usage:.2f},{hourly_green_percentage:.1f}'
            print(str_out)
            fo.write(str_out + "\n")
        if len(data) != num_hours:
            print("\nWARNING: wanted",num_hours,"hourly data points, but got",len(data),"!!!\n")
    elif ID[0] == 'Z':
        print ('*** Success - Zappi ***')
        data = json.loads(r.content)
        rec='U' + ID[1:] #No idea why my response is with a U and not a Z, this may be the case for everyone, or may need altering?
        for i in range(num_hours):
            if i >= len(data[rec]):     ## MJ: fixed, if hourly data for complete month isn't available
                break            
            hr=int(data[rec][i].get('hr') or 0)
            yr=int(data[rec][i].get('yr') or 0)
            mon=int(data[rec][i].get('mon') or 0)
            dom=int(data[rec][i].get('dom') or 0)
            y_import = float(data[rec][i].get('imp') or 0)/(60*1000)
            y_gep = float(data[rec][i].get('gep') or 0)/(60*1000)
            y_exp = float(data[rec][i].get('exp') or 0)/(60*1000)
            y_z1 = float(data[rec][i].get('h1d') or 0)/(60*1000)
            y_z2 = float(data[rec][i].get('h2d') or 0)/(60*1000)
            y_z3 = float(data[rec][i].get('h3d') or 0)/(60*1000)
            y_z1b = float(data[rec][i].get('h1b') or 0)/(60*1000)
            y_z2b = float(data[rec][i].get('h2b') or 0)/(60*1000)
            y_z3b = float(data[rec][i].get('h3b') or 0)/(60*1000)
            y_zappi = y_z1 + y_z2 + y_z3 + y_z1b + y_z2b + y_z3b

            daily_generation=y_gep/60
            daily_import=y_import/60
            daily_export=y_exp/60
            daily_EV=y_zappi/60

            daily_self_consumption = daily_generation-daily_export
            daily_property_usage=daily_import+daily_self_consumption
            daily_green_percentage = (daily_self_consumption / daily_property_usage)*100

            #Convert from UTC
            dt = datetime.datetime(yr,mon,dom,hr)
            dtutc = dt.replace(tzinfo=pytz.utc)
            # localdt = dtutc.astimezone(pytz.timezone(timezone))
            localdt = dtutc.astimezone(timezone) ## MJ: fixed, timezone was the result of pytz.timezone()

            print(f'{localdt.day}/{localdt.month}/{localdt.year} {localdt.hour}:00,{daily_import:.2f},{daily_export:.2f},{daily_generation:.2f},{daily_EV:.2f},{daily_self_consumption:.2f},{daily_property_usage:.2f},{daily_green_percentage:.1f}')
            fo.write(f'{localdt.day}/{localdt.month}/{localdt.year} {localdt.hour}:00,{daily_import:.2f},{daily_export:.2f},{daily_generation:.2f},{daily_EV:.2f},{daily_self_consumption:.2f},{daily_property_usage:.2f},{daily_green_percentage:.1f}\n')
    else:
        print ('Error: unknown ID prefix provided.')
else:
    print ("Failed to read ticket, errors are displayed below,")
    response = json.loads(r.content)
    print(response["errors"])
    print("x-request-id : " + r.headers['x-request-id'])
    print("Status Code : " + r.status_code)

fo.close()
