# Copyright 2023 Dell Inc. or its subsidiaries. All Rights Reserved.
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

'''
        Module to invoke all system commands
'''
import subprocess
import common_logging
import utility
import common_parser

def call_command(command, pipe = False, output=''):
    """
    Call a command using subprocess and return the output or log errors using syslog.

    Args:
        command (str or list): The command to be executed, as a string or a list of arguments.
        output (str): Output from previous command execution.

    Returns:
        str or None: The output of the command or None if an error occurred.
    """
    try:
        # Split the command by space into a list of tokens
        list_command_split_by_space_quote = common_parser.split_by_space_and_quote(command)
        output = subprocess.run(list_command_split_by_space_quote,input=output, \
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, \
                                timeout=float(utility.dict_telemetry_ini \
                                              ["metric_collection_timeout"]), \
                                                universal_newlines=True, check=False)
        # A return code of 0 means success,while a non-zero return code means failure.
        if output.returncode == 0 and output is not None:
            if pipe is False:
                return output.stdout.strip() if output.stdout else None
            if pipe is True:
                return output
        elif output.returncode != 0 and output is not None:
            common_logging.log_error('invoke_commands:call_command', f"Error : {output.stderr} Command : {command} ")
        else:
            common_logging.log_error('invoke_commands:call_command', f"Error output in: {command}")
       
    except subprocess.TimeoutExpired:
        common_logging.log_error('invoke_commands:call_command',
                                 f"Command invocation timeout: {command}")
    except Exception as exc:
        common_logging.log_error('invoke_commands:call_command', f"An error occurred: {exc}")
    return None

def call_command_with_pipe(command):
    """
    Call a command with pipe using subprocess and return the output or log errors using syslog.

    Args:
        command (str or list): The command to be executed, as a string or a list of arguments.

    Returns:
        str or None: The output of the command or None if an error occurred.
    """
    # Split the command by | into a list of subcommands
    command_split_by_pipe=common_parser.split_by_regex(command,"\|")
    first_subcommand = True
    for subcommand in command_split_by_pipe:
        if first_subcommand:
            output=call_command(subcommand,True)
            first_subcommand = False
        else:
            if output:
                output=call_command(subcommand,True,output.stdout)
            else:
                common_logging.log_error('invoke_commands:call_command_with_pipe',
                                         f"Error output: {command}")
                return None
    return output.stdout.strip() if output else None

def run_command(command):
    """
        Call a command using subprocess and return the output or log errors using syslog.
        Args:
            command (str): The command to be executed.
        Returns:
            str or None: The output of the command or None if an error occurred.
       """
    try:
        command = command.split()
        output = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, check=False)

        return output.stdout.strip() if output.stdout else None
    except Exception as exc:
        common_logging.log_error('invoke_commands:run_command', f"An error occurred: {exc}")
    return None