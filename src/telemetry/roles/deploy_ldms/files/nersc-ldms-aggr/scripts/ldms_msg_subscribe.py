#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
