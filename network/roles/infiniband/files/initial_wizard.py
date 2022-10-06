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
switch_ip=sys.argv[1]
switch_username=sys.argv[2]
switch_password=sys.argv[3]
admin_passwd=sys.argv[4]
monitor_passwd=sys.argv[5]
login_cmd="ssh "+switch_username+"@"+switch_ip
child = pexpect.spawn(login_cmd)
while True:
        i = child.expect(['(.*)assword: ', '(m?)Choice:', '(m?)Do you want to use the wizard for initial configuration\?','(m?)Step \d{1,2}: Hostname\?(.*)]', '(m?)Step \d{1,2}: Use DHCP on mgmt0(.*)]', '(m?)Step \d{1,2}: Enable IPv6 auto(.*)]', '(m?)Step \d{1,2}: Enable IPv6\?(.*)]', '(m?)Step \d{1,2}: (.*)DHCPv6 on mgmt0 interface(.*)]', '(m?)Step \d{1,2}: Update time\?', '(m?)Step \d{1,2}: Enable password hardening\?', '(.*)Fail(.*)', '(m?)Step \d{1,2}: Admin password(.*)\?', '(m?)Step \d{1,2}: Confirm admin password\?', '(m?)Step \d{1,2}: Monitor password(.*)\?', '(m?)Step \d{1,2}: Confirm monitor password\?', '(m?)[>]', '(m?)No route to host', '(m?)Permission denied', '(m?)Maximum number of failed logins reached, account locked.'])
        if i==0:
            child.sendline(switch_password)
            print('Loggedin')
        elif i==1:
            child.sendline('\n')
            print("Saving the Configuration Changes")
        elif i==2:
            child.sendline('y')
            print("Configuring Initial Wizard")
        elif i==3:
            child.sendline('\n')
            print("Successfully assigned Hostname")
        elif i==4:
            child.sendline('\n')
            print("Use DHCP on mgmt0 is configured")
        elif i==5:
            child.sendline('\n')
            print("Enabled IPv6 auto")
        elif i==6:
            child.sendline('\n')
            print("Enabled IPv6")
        elif i==7:
            child.sendline('\n')
            print("Enabled DHCPv6 on mgmt0 interfac")
        elif i==8:
            child.sendline('\n')
            print("Updated Time")
        elif i==9:
            child.sendline('\n')
            print("Enabled Password Hardening")
        elif i==10:
            print("Please make sure password constraints are met")
            break
        elif i==11:
            child.sendline(admin_passwd)
            print("Successfully Set Admin Password")
        elif i==12:
            child.sendline(admin_passwd)
            print("Successfully Re-entered Admin Password")
        elif i==13:
            child.sendline(monitor_passwd)
            print("Successfully Set Monitor Password")
        elif i==14:
            child.sendline(monitor_passwd)
            print("Successfully Re-entered Monitor Password")
        elif i==15:
            print("Initial Wizard of Switch is Configured Successfully")
            break
        elif i==16:
            print("Switch is not rechable at this time")
            break
        elif i==17:
            print("Switch login password is incorrect")
            break
        elif i==18:
            print("Incorrect password, maximum limit reached")
            break
        else:
            print("Please do initial configuration manually, Re-execute playbook.")
            break