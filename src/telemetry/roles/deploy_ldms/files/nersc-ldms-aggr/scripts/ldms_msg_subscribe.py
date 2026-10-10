#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
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
"""
LDMS Stream Message Subscriber

Subscribes to and displays LDMS daemon stream messages for monitoring.
"""

import time
import sys
import argparse

sys.path.append('/opt/ovis-ldms/lib/python3.6/site-packages')
from ovis_ldms import ldms  # pylint: disable=wrong-import-position,import-error

parser = argparse.ArgumentParser(description='Subscribe to LDMS stream messages')
parser.add_argument('--host', default='localhost', help='LDMS daemon host (default: localhost)')
parser.add_argument(
    '--port', type=int, default=10001,
    help='LDMS daemon port (default: 10001 for samplers, '
         'use 6001+ for aggregators, 60001 for stream daemon)'
)
args = parser.parse_args()

mc = ldms.MsgClient(".*", True)

x = ldms.Xprt("sock", "munge")
x.connect(args.host, args.port)
x.msg_subscribe("nersc", True)
print(f"Subscribed to {args.host}:{args.port}")

while True:
    d = mc.get_data()
    while d is None:
        time.sleep(0.25)
        d = mc.get_data()
    ts = time.strftime("%F %T") + f".{int((time.time() % 1) * 1e6):06}"
    print(ts, d.name, ":", d.data)
