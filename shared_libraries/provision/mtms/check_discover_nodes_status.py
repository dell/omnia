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
    """
    Executes a shell command and returns the result.

    Parameters:
        cmd (str): The shell command to execute.

    Returns:
        Tuple[bool, str, str]: A tuple containing the success status of the command,
                              the standard error output, and the standard output.
    """
    run = subprocess.run(cmd,shell=True, capture_output=True, text=True)
    if 'ERROR' in run.stderr:
        return False, run.stderr, run.stdout
    else:
        return True, run.stderr, run.stdout


def get_discover_nodes():
    """
    Retrieves the list of nodes that are part of the 'bmc_discover' group.

    Returns:
        list: A list of nodes.

    Raises:
        None

    Notes:
        - The function executes the command '/opt/xcat/bin/lsdef -t group -o bmc_discover | grep members | sed -n "/members=/s/    members=//p"'
        - The command retrieves the group members of the 'bmc_discover' group.
        - If the command is successful, the function splits the output on comma and returns the list of nodes.
        - If the command fails, the function prints an error message and returns None.
    """
    cmd = f'/opt/xcat/bin/lsdef -t group -o bmc_discover | grep members | sed -n "/members=/s/    members=//p"'
    status, err, out = run_cmd(cmd)
    if status:
        return out.split(',')
    else:
        print(f" No group with bmc_discover found, Error : {err} ")


def check_discover_nodes(nodelist):
    """
    This function checks the status of a list of nodes and returns a string of the nodes that are in the 'booted' status.

    Parameters:
        nodelist (list): A list of nodes to check.

    Returns:
        None

    Notes:
        - The function iterates over the `nodelist` and strips any leading/trailing whitespace from each node.
        - It then constructs a shell command using the `run_cmd` function to check the status of each node.
        - The command retrieves the status of the node from the xCAT database.
        - If the status is 'booted', the node is added to the `bmc_list`.
        - Finally, the function prints a string of the nodes in the `bmc_list`.
    """
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


check_discover_nodes(get_discover_nodes())
