#!/usr/bin/env python

# Copyright 2024 Martin Junius
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
# Version 0.0 / 2024-07-21
#       Test timezone handling zoneinfo ./. pytz

import sys
import argparse
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from zoneinfo import ZoneInfo

# The following libs must be installed with pip
# required on Windows!
import tzdata
# for comparison only!
import pytz
from icecream import ic
# Disable debugging
ic.enable()

tzname = "Europe/Berlin"
# DST switch end of Mar, end of Oct

loc = ZoneInfo(tzname)
utc = ZoneInfo("UTC")

ic("--- wrong absolute delta with local datetime (timedelta ist wall clock!) ---")
# not DST
dt1 = datetime(2024, 3, 1, 0, 0, 0, tzinfo=loc)
ic(dt1, dt1.dst(), dt1.utcoffset(), dt1.isoformat())
# DST, switch on 2024-03-31
dt2 = datetime(2024, 4, 1, 0, 0, 0, tzinfo=loc)
ic(dt2, dt2.dst(), dt2.utcoffset(), dt2.isoformat())

delta = dt2 - dt1
ic(delta, delta.total_seconds()/3600)

ic("--- correct delta with UTC datetime ---")
utc1 = dt1.astimezone(utc)
utc2 = dt2.astimezone(utc)
udelta = utc2 - utc1
ic(utc1, utc2, udelta, udelta.total_seconds()/3600)

ic("--- behavior with pytz, does result in absolute delta! ---")
loc = pytz.timezone(tzname)
utc = pytz.utc
# not DST
dt1 = loc.localize(datetime(2024, 3, 1, 0, 0, 0))
ic(dt1, dt1.dst(), dt1.utcoffset(), dt1.isoformat())

# DST
dt2 = loc.localize(datetime(2024, 4, 1, 0, 0, 0))
ic(dt2, dt2.dst(), dt2.utcoffset(), dt2.isoformat())

delta = dt2 - dt1
ic(delta, delta.total_seconds()/3600)
