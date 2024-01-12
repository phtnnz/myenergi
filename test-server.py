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

# ChangeLog
# Version 0.0 / 2024-01-12
#       Find server for Myenergi API

import argparse
import pytz
from configparser import ConfigParser
import requests
from requests.auth import HTTPDigestAuth

# The following libs must be installed with pip
from icecream import ic
# Disable debugging
ic.disable()
# Local modules
from verbose import verbose

global VERSION, AUTHOR, NAME
VERSION = "0.0 / 2024-01-12"
AUTHOR  = "Martin Junius"
NAME    = "test-server"



def main():
    arg = argparse.ArgumentParser(
        prog        = NAME,
        description = "Test: get Myenergi API server",
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

    # Read .ini file for secrets, same format as used by the pymyenergi library with some additions
    #
    # [hub]
    # serial=12345678
    # password=yourpassword
    # id=Z12345678      # "Z" for Zappi + serial
    # id=E12345678      # "E" for Eddit + serial
    # timezone=Europe/Berlin

    config = ConfigParser()
    config.read("./.myenergi.cfg")
    username = config.get("hub", "serial")
    password = config.get("hub", "password")
    id       = config.get("hub", "id")
    timezone = pytz.timezone(config.get("hub", "timezone"))
    verbose("Serial number", username)


    director_url = "https://director.myenergi.net"
    verbose("Director:", director_url)
    response = requests.get(director_url, auth=HTTPDigestAuth(username, password))
    verbose(response)
    api_server = response.headers['X_MYENERGI-asn']

    print("API server:", api_server)




if __name__ == "__main__":
    main()
