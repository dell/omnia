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
    This module contains all the parsing related methods.
    For parsing any command prompt output, 
    this module should be imported and relevant methods should be used.
'''

import re
import json
import configparser
from io import StringIO
import yaml
import pandas as pd
import common_logging

def query_from_txt(input_txt,pattern):
    '''
    Query a value from a text.
    Example: 
        Need to find the value of "healthz check" from bellow text. The value should be "passed".

        input_txt=  "[+]poststarthook/apiservice-openapi-controller ok
                     [+]shutdown ok
                     healthz check passed"

        pattern= "healthz check (\\w+)"
    '''
    status_match = re.search(pattern, input_txt)
    if status_match:
        return status_match.group(1)
    else:
        return None

#dataframe parser
def get_df_format(command_input):
    '''
    i/p: gets csv format output of any command as input and the column name whose data is required
    o/p: convert df to dict of list and return.
    '''
    try:
        csv_string = StringIO(command_input)
        dataframe = pd.read_csv(csv_string, sep=",", header=0)
        dataframe.columns = dataframe.columns.str.strip()
        return dataframe
    except Exception as err:
        common_logging.log_error("common_parser:get_df_format",
                                 "could not convert csv to dataframe." + str(err))
        return None

def get_col_from_df(dataframe, col_name):
    '''
    i/p: gets dataframe and column name as input
    o/p: extract column data from dataframe into a list and return
    '''
    try:
        return dataframe[col_name].tolist()
    except Exception as err:
        common_logging.log_error("common_parser:get_col_from_df",
                                 "could not fetch required column from dataframe." + str(err))
        return None

def parse_yaml_file(filedata):

    '''
    This module parses yaml file data and provides the dictionary output

    Args:
        filedata (str): The yaml file data in string format
    '''

    cfg = {}
    try:
        cfg = yaml.safe_load(filedata)
        return cfg
    except Exception as ex:
        # Log the error message with the error output
        common_logging.log_error("common_parser:parse_yaml_file",
                                 "Error in parsing inputs for timescaledb connection" + str(ex))
        return cfg

def split_by_regex(input_data, regex):
    '''
    Split the input text w.r.t passed regex delimiter and return the list of tokens
    '''
    return re.split(regex,input_data)

#custom delimiter parser
def get_custom_header(delimited_text, delimiter):
    '''
    Generates n custom headers where n is the number of tokens in the delimited_text
    Header index starts with 1
    Example:  header1, header2, header3
    '''
    values_split=split_by_regex(delimited_text, delimiter)
    headers=["header{}".format(i) for i in range (1,len(values_split)+1)]
    return headers

def get_dict_list_format_parser_output(command_output, delimiter, with_header=0):
    '''
    i/p:Tabular format input with or without header
    o/p:
        Returns dictionary with values as list format data of the input.
        Keys will be the headers and value will be a list with all entried under that header
    '''
    dict_output={}
    command_output_lines = split_by_regex(command_output,"\n")
    #get the headers
    if with_header==1:
        header_list=split_by_regex(command_output_lines[0], delimiter)
        #skip the top header row for tabular output with header
        start_index=1
    else:
        header_list=get_custom_header(command_output_lines[0], delimiter)
        start_index=0
    #initialization: set the headers as ditionary key and empty list as values
    for values in header_list:
        dict_output[values]=[]

    #fill the dictionary with values
    for index in range(start_index,len(command_output_lines)):
        #split and put into lists
        command_output_line_splited=split_by_regex(command_output_lines[index], delimiter)
        for key_index, header in enumerate(header_list):
            dict_output[header].append(command_output_line_splited[key_index])
    return dict_output

#json parser
def get_json_format(command_input):
    '''
    i/p: gets json format output of any command as input
    o/p: python json object for the input.
    '''
    try:
        return json.loads(command_input)
    except Exception as err:
        common_logging.log_error("common_parser:get_json_format","Exception in json parsing: "+str(type(err)) +" "+ str(err))
        return None

#ini parser
def get_ini_dict(ini_file_path):
    '''
    i/p: Path to a ini file
        Example Format for ini file:
            [omnia_telemetry]
            omnia_telemetry_collection_interval=5
            collect_regular_metrics=true
            collect_health_check_metrics=true
            collect_gpu_metrics=true
            fuzzy_offset=60
    o/p: A dictionary with key value pairs from the ini
    '''
    config_object = configparser.ConfigParser()
    try:
        with open(ini_file_path, 'r', encoding='utf-8') as file:
            # Read the content of the file
            config_object.read_file(file)
        # Read the ini into a dictionary
        output_dict={s:dict(config_object.items(s)) for s in config_object.sections()}
        return output_dict
    except FileNotFoundError:
        common_logging.log_error("common_parser:get_ini_dict",f"File '{ini_file_path}' not found")
    except IOError:
        common_logging.log_error("common_parser:get_ini_dict",f"Error reading file '{ini_file_path}'")
    except Exception as err:
        common_logging.log_error("common_parser:get_ini_dict","Exception in ini parsing: "+str(type(err)) +" "+ str(err))
    return None

def split_by_space_and_quote(command):
    """
    Split commands with whitespaces and quotations.

    Args:
        command (str or list): The command to be executed, as a string or a list of arguments.

    Returns:
        list: List of tokens in command after splitting.
    """
    command_list=[]
    start_index=0
    flag=False
    for index in range(len(command)):
        if command[index] == '"' and flag is False:
            flag=True
            start_index=index+1

        elif command[index]=='"' and flag is True:
            command_list.append(command[start_index:index])
            start_index=index+1
            flag=False

        elif command[index]==' ' and flag is False:
            command_list.append(command[start_index:index])
            start_index=index+1

        elif index==len(command)-1:
            command_list.append(command[start_index:index+1])
        else:
            pass
    return command_list

def get_unit(key, combined_unit_dict):
    key = split_by_regex(key, ':')[0]
    for metric, metric_dict in combined_unit_dict.items():
        if metric_dict:
            if key in metric_dict.keys():
                return metric_dict[key]
    return None