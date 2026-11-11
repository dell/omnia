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
