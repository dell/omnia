# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

import subprocess


def run_cmd(cmd):
    run = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if 'ERROR' in run.stderr:
        return False, run.stderr, run.stdout
    else:
        return True, run.stderr, run.stdout


def get_static_nodes():
    cmd = f'/opt/xcat/bin/lsdef -t group -o bmc_static | grep members | sed -n "/members=/s/    members=//p"'
    status, err, out = run_cmd(cmd)
    if status:
        return out.split(',')
    else:
        print(f" No group with bmc_static found, Error : {err} ")


def check_static_nodes(nodelist):
    bmc_list = list()
    for node in nodelist:
        node = node.strip()
        cmd = f'/opt/xcat/bin/lsdef {node} -i status -c | sed -n "/{node}: status=/s/{node}: status=//p"'
        status, err, out = run_cmd(cmd)
        if status:
            if len(out) == 1:
                bmc_list.append(node)

    bmc_string = ' '.join(map(str, bmc_list))
    print(bmc_string)


check_static_nodes(get_static_nodes())
