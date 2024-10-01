#!/usr/bin/env python

# Copyright 2024 Contributors, see below
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Based on script from https://myenergi.info/extracting-energy-data-t7445-s90.html
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

# ChangeLog Martin Junius
# Version 0.1 / 2024-01-12
#       First overhauled version of the script posted to the myenergi forum
#       Zappi-only version of modified original script
# Version 0.2 / 2024-01-12
#       With proper command line interface
# Version 0.3 / 2024-07-21
#       Refactored to use zoneinfo, tzdata instead of pytz
# Version 0.4 / 2024-08-01
#       Use new module csvoutput

import requests
import json
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
from requests.auth import HTTPDigestAuth
from configparser import ConfigParser
import csv
import locale
import argparse
import re

# The following libs must be installed with pip
# tzdata required on Windows for IANA timezone names!
import tzdata
from icecream import ic
# Disable debugging
ic.disable()
# Local modules
from verbose import verbose, warning, error
from csvoutput import CSVOutput


global VERSION, AUTHOR, NAME
VERSION = "0.4 / 2024-08-01"
AUTHOR  = "Martin Junius"
NAME    = "myenergi-zappi2"



# Read .ini file for secrets, same format as used by the pymyenergi library with some additions
#
# [hub]
# serial=12345678
# password=yourpassword
# id=Z12345678      # "Z" for Zappi + serial
# id=E12345678      # "E" for Eddi + serial
# timezone=Europe/Berlin
# locale=

class Config(ConfigParser):
    filename = None
    username = None
    password = None
    id       = None
    timezone = None

    def __init__(self, file=None):
        super().__init__()
        if file:
            self.read(file)
            

    def read(self, file):
        Config.filename = file
        super().read(file)
        Config.username = self.get("hub", "serial")
        Config.password = self.get("hub", "password")
        Config.id       = self.get("hub", "id")
        Config.timezone = ZoneInfo(self.get("hub", "timezone"))
        CSVOutput.set_default_locale(self.get("hub", "locale"))
        ic(Config.username, Config.password, Config.id, Config.timezone, locale.getlocale(), locale.localeconv())



def retrieve_api_server():
    # Based on code snippet from https://myenergi.info/viewtopic.php?p=29050#p29050, user DougieL
    director_url = "https://director.myenergi.net"
    verbose("Director:", director_url)
    response = requests.get(director_url, auth=HTTPDigestAuth(Config.username, Config.password))
    verbose(response)
    api_server = response.headers['X_MYENERGI-asn']

    verbose("API server:", api_server)
    return api_server



def retrieve_month_hourly(api_server, year, month):
    # Start first day of month at 0h *local* time
    local_year  = year
    local_month = month
    local_day   = 1
    local_hour  = 0

    # Convert start date and time to UTC
    start_datetime_local = datetime(local_year, local_month, local_day, local_hour, tzinfo=Config.timezone)
    start_datetime_utc   = start_datetime_local.astimezone(tz=timezone.utc)
    utc_year             = start_datetime_utc.year
    utc_month            = start_datetime_utc.month
    utc_day              = start_datetime_utc.day
    utc_hour             = start_datetime_utc.hour

    start_next_month_local = datetime(local_year + (local_month // 12), (local_month % 12) + 1, local_day, local_hour, tzinfo=Config.timezone)
    start_next_month_utc = start_next_month_local.astimezone(tz=timezone.utc)
  
    # Calculate hours in the month, which is tricky with DST involved
    # Always calculate ABSOLUTE delta using UTC, otherwise DST switching incurs a wrong result!
    # The old pytz library works differently with local timezone than zoneinfo used here!
    num_hours = (start_next_month_utc - start_datetime_utc).total_seconds() / 3600
    ic(start_next_month_local, start_datetime_local, start_next_month_utc, start_datetime_utc, num_hours)

    ##MJ: API only allows a certain numbe of hours, 9999 was too much

    id = Config.id
    verbose("Collecting", num_hours, "hours starting from:", start_datetime_local, "(local),", start_datetime_utc, "(UTC)")

    url = "https://" + api_server + "/cgi-jdayhour-" + id + '-' + str(utc_year) + '-' + str(utc_month) + '-' + str(utc_day) + '-' + str(utc_hour) + '-' + str(num_hours)
    verbose("URL:", url)

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    r = requests.get(url, auth = HTTPDigestAuth(Config.username,Config.password), headers = headers, timeout = 60)

    if r.status_code == 200:
        if id[0] == 'Z':
            verbose("success - Zappi")
            data = json.loads(r.content)
            ##DEBUG: received JSON
            # print("JSON =", json.dumps(data, indent=4))
            rec='U' + id[1:] #No idea why my response is with a U and not a Z, this may be the case for everyone, or may need altering?
            for data1 in data[rec]:
                # if i >= len(data[rec]):     ## MJ: fixed, if hourly data for complete month isn't available
                #     break            
                hr       = int(data1.get('hr') or 0)
                yr       = int(data1.get('yr') or 0)
                mon      = int(data1.get('mon') or 0)
                dom      = int(data1.get('dom') or 0)
                y_import = float(data1.get('imp') or 0)/(60*1000)
                y_gep    = float(data1.get('gep') or 0)/(60*1000)
                y_exp    = float(data1.get('exp') or 0)/(60*1000)
                y_z1     = float(data1.get('h1d') or 0)/(60*1000)
                y_z2     = float(data1.get('h2d') or 0)/(60*1000)
                y_z3     = float(data1.get('h3d') or 0)/(60*1000)
                y_z1b    = float(data1.get('h1b') or 0)/(60*1000)
                y_z2b    = float(data1.get('h2b') or 0)/(60*1000)
                y_z3b    = float(data1.get('h3b') or 0)/(60*1000)
                # from original script, Zappi charging only fills h1d, h2d, h3d
                y_zappi  = y_z1 + y_z2 + y_z3 + y_z1b + y_z2b + y_z3b

                daily_import=y_import/60
                daily_export=y_exp/60
                daily_EV=y_zappi/60
                ## doesn't work for me as generation is always 0, my Zappi can only measure import/export
                # daily_generation=y_gep/60
                # daily_self_consumption = daily_generation - daily_export
                # daily_property_usage=daily_import + daily_self_consumption
                # daily_green_percentage = (daily_self_consumption / daily_property_usage)*100

                # convert from UTC date/time in JSON output
                localdt = datetime(yr, mon, dom, hr, tzinfo=timezone.utc).astimezone(tz=Config.timezone)
                # ic(localdt, daily_import, daily_export, daily_EV)
                CSVOutput.add_row([localdt.strftime("%x %X"), daily_import, daily_export, daily_EV])
        else:
            print ('Error: unknown ID prefix provided.')
    else:
        print ("Failed to read ticket, errors are displayed below,")
        response = json.loads(r.content)
        print(response["errors"])
        print("x-request-id : " + r.headers['x-request-id'])
        print("Status Code : " + r.status_code)



def main():
    arg = argparse.ArgumentParser(
        prog        = NAME,
        description = "Retrieve Zappi data from Myenergi portal",
        epilog      = "Version " + VERSION + " / " + AUTHOR)
    arg.add_argument("-v", "--verbose", action="store_true", help="verbose messages")
    arg.add_argument("-d", "--debug", action="store_true", help="more debug messages")
    arg.add_argument("-s", "--start", help="start YYYY-MM for report (default this month)")
    arg.add_argument("-e", "--end", help="end YYYY-MM for report (default this month)")
    arg.add_argument("-o", "--output", help="output CSV file (default MyEnergi_Data.csv)")

    args = arg.parse_args()

    # Standard command line options
    if args.verbose:
        verbose.set_prog(NAME)
        verbose.enable()
    if args.debug:
        ic.enable()
    ic(args)

    # Additional command line options
    today = date.today()
    year_s  = year_e  = today.year
    month_s = month_e = today.month
    if args.start:
        m = re.match(r'^(\d\d\d\d)-(\d\d)$', args.start)
        if m:
            year_s = int(m.group(1))
            month_s = int(m.group(2))
        else:
            error("illegal format for --start option:", args.start)
    if args.end:
        m = re.match(r'^(\d\d\d\d)-(\d\d)$', args.end)
        if m:
            year_e = int(m.group(1))
            month_e = int(m.group(2))
        else:
            error("illegal format for --end option:", args.end)
    filename = args.output or "MyEnergi_Data.csv"
    ic(filename, year_s, month_s, year_e, month_e)

    # Actions starts here ...
    Config(".myenergi.cfg")
    CSVOutput.add_fields(["Date", "Import (kWh)", "Export (kWh)", "BEV (kWh)"])

    api_server = retrieve_api_server()
    for year in range(year_s, year_e+1):
        month1 = month_s if year == year_s else 1
        month2 = month_e if year == year_e else 12
        for month in range(month1, month2+1):
            ic(year, month)
            retrieve_month_hourly(api_server, year, month)

    verbose("saving to", filename)
    CSVOutput.write(filename)



if __name__ == "__main__":
    main()
