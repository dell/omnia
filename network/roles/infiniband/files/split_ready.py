# Copyright 2022 Dell Inc. or its subsidiaries. All Rights Reserved.
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

import pexpect
import sys
import time
switch_ip=sys.argv[1]
switch_username=sys.argv[2]
switch_password=sys.argv[3]
login_cmd="ssh "+switch_username+"@"+switch_ip
child = pexpect.spawn(login_cmd)
while True:
        i = child.expect(['(.*)assword: ', "Type 'yes' (.*): ", '(m?)No route to host', '(m?)Permission denied', '(.*)current profile is already in use', '(m?)[>]', '(m?)[#]'])
        if i==0:
            child.sendline(switch_password)
            print('Login Successful')
        elif i==1:
            child.sendline('yes')
            print("Applied configuration for Split-Ready, Wait for 4 mins for switch to comeup")
            time.sleep(240)
            print("Successfully changed switch to split-ready mode")
            break
        elif i==2:
            print("Switch is not rechable at this time")
            break
        elif i==3:
            print("Switch login password is incorrect")
            break
        elif i==4:
            print("Switch is already in split ready mode")
            break
        elif i==5:
            child.sendline('enable')
            print("Switch is in enabled mode")
        elif i==6:
            child.sendline('configure terminal')
            child.sendline('system profile ib split-ready')
        else:
            break