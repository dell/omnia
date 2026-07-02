#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDMS Stream Message Publisher

Publishes messages to LDMS daemon stream for testing and monitoring.
"""

import sys
import argparse

sys.path.append('/opt/ovis-ldms/lib/python3.6/site-packages')
from ovis_ldms import ldms  # pylint: disable=wrong-import-position,import-error

parser = argparse.ArgumentParser(description='Publish LDMS stream message')
parser.add_argument('--host', default='localhost', help='LDMS daemon host (default: localhost)')
parser.add_argument(
    '--port', type=int, default=10001,
    help='LDMS daemon port (default: 10001 for samplers, '
         'use 6001+ for aggregators, 60001 for stream daemon)'
)
parser.add_argument('--message', default='This is a test', help='Message to publish')
args = parser.parse_args()

ldms.init(16 * 1024 * 1024)
x = ldms.Xprt("sock", "munge")
x.connect(args.host, args.port)
x.msg_publish("nersc", args.message)
print(f"Published to {args.host}:{args.port} - {args.message}")
