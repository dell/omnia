# Copyright 2022 Dell Inc. or its subsidiaries. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

#!/usr/bin/python3
import logging
import sys
import time
import datetime
import inspect
import easysnmp
from easysnmp import Session
from collections import defaultdict

# Define global variables
temp_decimal_oids=[]
hexa_mac=defaultdict(list)
final_mac={}

def collect_dec_oid():
        # Create an SNMP session to be used for all our requests
        session = Session(hostname='100.96.28.y', community='public', version=2)

        # Run snmp walk on the created session
        description = session.walk('.1.3.6.1.2.1.17.7.1.2.2.1.2')

        # Collect information about the temp decimal MACs/oids
        for item in description:
                temp_decimal_oids.append(item.oid);
        filter_dec_oid()

def filter_dec_oid():
        count=1;
        temp_oids=[]

        # Extract the last 6 digit that forms the decimal MAC
        for item in temp_decimal_oids:
                temp_oids.append(item.split('-')[1])

        for item in temp_oids:
                temp_nos=[]
        # Convert decimal to hexadecimal numbers
                for i in item.split('.'):
                        number=format(int(i),'x')
        # To append 0 as MAC has 00 instead of 0
                        if number=="0":
                                number=number+"0"
                        temp_nos.append(number);
                hexa_mac[count].append(temp_nos[-6:])
                count=count+1;
        print(hexa_mac)

collect_dec_oid()
