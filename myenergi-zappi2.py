#!/usr/bin/env python

# Copyright 2023 Martin Junius
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

# ChangeLog
# Version 0.1 / 2024-01-12
#       First overhauled version of the script posted to the myenergi forum
#       Zappi-only version of modified original script
# Version 0.2 / 2024-01-12
#       With proper command line interface

import requests
import json
import datetime
from requests.auth import HTTPDigestAuth
import pytz
from configparser import ConfigParser
import csv
import locale
import sys
import os
import argparse

# The following libs must be installed with pip
from icecream import ic
# Disable debugging
ic.disable()
# Local modules
from verbose import verbose

global VERSION, AUTHOR, NAME
VERSION = "0.2 / 2024-01-15"
AUTHOR  = "Martin Junius"
NAME    = "myenergi-zappi2"



# Read .ini file for secrets, same format as used by the pymyenergi library with some additions
#
# [hub]
# serial=12345678
# password=yourpassword
# id=Z12345678      # "Z" for Zappi + serial
# id=E12345678      # "E" for Eddit + serial
# timezone=Europe/Berlin
# locale=deu_deu

config = ConfigParser()
config.read("./.myenergi.cfg")
username = config.get("hub", "serial")
password = config.get("hub", "password")
id       = config.get("hub", "id")
timezone = pytz.timezone(config.get("hub", "timezone"))
locale.setlocale(locale.LC_ALL, config.get("hub", "locale"))
ic(username, password, id, timezone, locale.getlocale(), locale.localeconv())



class CSVOutput:
    csv_cache = []
    fields = None

    def add_csv_row(obj):
        CSVOutput.csv_cache.append(obj)

    def add_csv_fields(fields):
        CSVOutput.fields = fields

    def write_csv(file):
        with open(file, 'w', newline='') as f:
            ##FIXME: check  locale.RADIXCHAR
            if locale.localeconv()['decimal_point'] == ",":
                # Use ; as the separator and quote all fields for easy import in "German" Excel
                writer = csv.writer(f, dialect="excel", delimiter=";", quoting=csv.QUOTE_ALL)
            else:
                writer = csv.writer(f, dialect="excel")
            if CSVOutput.fields:
                writer.writerow(CSVOutput.fields)
            writer.writerows(CSVOutput.csv_cache)



def retrieve_api_server():
    # Based on code snippet from https://myenergi.info/viewtopic.php?p=29050#p29050, user DougieL
    director_url = "https://director.myenergi.net"
    verbose("Director:", director_url)
    response = requests.get(director_url, auth=HTTPDigestAuth(username, password))
    verbose(response)
    api_server = response.headers['X_MYENERGI-asn']

    print("API server:", api_server)
    return api_server



def retrieve_month_hourly(api_server, year, month):
    # Start first day of month at 0h *local* time
    local_year  = year
    local_month = month
    local_day   = 1
    local_hour  = 0

    # Convert start date and time to UTC
    start_datetime_local = timezone.localize(datetime.datetime(local_year, local_month, local_day, local_hour))
    start_datetime_utc   = start_datetime_local.astimezone(pytz.utc)
    utc_year             = start_datetime_utc.year
    utc_month            = start_datetime_utc.month
    utc_day              = start_datetime_utc.day
    utc_hour             = start_datetime_utc.hour

    # Calculate hours in the month, which is not trivial with DST involved
    start_next_month = datetime.datetime(local_year + (local_month // 12), (local_month % 12) + 1, local_day, local_hour)
    start_next_month_local = timezone.localize(start_next_month)
    num_hours = round((start_next_month_local - start_datetime_local).total_seconds() / 60 / 60)
    ##MJ: API only allows a certain numbe of hours, 9999 was too much

    # Echo setup
    print("Collecting", num_hours, "hours starting from:", start_datetime_local, "(local),", start_datetime_utc, "(UTC)")

    url = "https://" + api_server + "/cgi-jdayhour-" + id + '-' + str(utc_year) + '-' + str(utc_month) + '-' + str(utc_day) + '-' + str(utc_hour) + '-' + str(num_hours)
    print("URL: " + url + "\n")

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    r = requests.get(url, auth = HTTPDigestAuth(username,password), headers = headers, timeout = 60)

    if r.status_code == 200:
        if id[0] == 'Z':
            print ('*** Success - Zappi ***')
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
                localdt = datetime.datetime(yr,mon,dom,hr) .replace(tzinfo=pytz.utc) .astimezone(timezone)
                ic(localdt, daily_import, daily_export, daily_EV)
                CSVOutput.add_csv_row([localdt.strftime("%x %X"),
                                       locale.format_string("%.3f", daily_import),
                                       locale.format_string("%.3f", daily_export),
                                       locale.format_string("%.3f", daily_EV)
                                       ])
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
    # arg.add_argument("-n", "--name", help="example option name")
    # arg.add_argument("-i", "--int", type=int, help="example option int")
    # arg.add_argument("dirname", help="directory name")
    # # nargs="+" for min 1 filename argument
    # arg.add_argument("filename", nargs="*", help="filename")

    args = arg.parse_args()

    if args.verbose:
        verbose.set_prog(NAME)
        verbose.enable()
    if args.debug:
        ic.enable()
    ic(args)

    print("Serial number:", username)
    print("API key:", len(password), " chars")
    print("Device id:", id)
    print("Timezone:", timezone)

    CSVOutput.add_csv_fields(["Date", "Import (kWh)", "Export (kWh)", "BEV (kWh)"])

    api_server = retrieve_api_server()
    retrieve_month_hourly(api_server, 2023, 11)
    retrieve_month_hourly(api_server, 2023, 12)
    retrieve_month_hourly(api_server, 2024, 1)

    filename = "MyEnergi_Data.csv"
    print("Saving to:", filename)
    CSVOutput.write_csv(filename)



if __name__ == "__main__":
    main()
