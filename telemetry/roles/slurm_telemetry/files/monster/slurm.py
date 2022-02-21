"""
MIT License
Copyright (c) 2022 Texas Tech University
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
This file is part of MonSter.
Author:
    Jie Li, jie.li@ttu.edu
"""

import time
import json
import logger
import requests
import subprocess

from requests.adapters import HTTPAdapter

log = logger.get_logger(__name__)


def read_slurm_token(slurm_config: dict):
    """read_slurm_token Read Slurm token

    Read the token file, if it is out of data, get a new token from Slurm

    Args:
        slurm_config (dict): Slurm Configuration
    """
    token = ""
    try:
        with open('./token.json', 'r') as f:
            token_record = json.load(f)
            time_interval = int(time.time()) - token_record['time']
            if time_interval >= 3600:
                token = get_slurm_token(slurm_config)
            else:
                token = token_record['token']
    except:
        token = get_slurm_token(slurm_config)
    return token


def get_slurm_token(slurm_config: dict):
    """get_slurm_token Get Slurm Token

    Get JWT token from Slurm. This requires the public key on this node to be 
    added to the target cluster headnode.

    Args:
        slurm_config (dict): Slurm Configuration

    Returns:
        srt: token
    """
    
    while True:
        try:
            # Setting command parameters
            slurm_headnode = slurm_config['headnode']
            
            print("Get a new token...")
            # The command used in cli
            command = [f"ssh {slurm_headnode} 'scontrol token lifespan=3600'"]
            # Get the string from command line
            rtn_str = subprocess.run(command, shell=True, stdout=subprocess.PIPE).stdout.decode('utf-8')
            # Get token
            token = rtn_str.splitlines()[0].split('=')[1]
            timestamp = int(time.time())

            token_record = {
                'time': timestamp,
                'token': token
            }

            with open('./token.json', 'w') as f:
                json.dump(token_record, f, indent = 4)
            
            return token
        except Exception as err:
            print("Get Slurm token error! Try in 60s.")
            time.sleep(60)
        else:
            break


def call_slurm_api(slurm_config: dict, token: str, url: str):
    """call_slurm_api Call Slurm API

    Call Slurm API and get the data from the specified url

    Args:
        slurm_config (dict): Slurm Configuration
        token (str): Slurm JWT token
        url (str): Url of Slurm API

    Returns:
        dict: slurm metrics
    """
  
    metrics = {}
    headers = {"X-SLURM-USER-NAME": slurm_config['user'], 
               "X-SLURM-USER-TOKEN": token}
    adapter = HTTPAdapter(max_retries=3)
    with requests.Session() as session:
        session.mount(url, adapter)
        try:
            response = session.get(url, headers=headers)
            metrics = response.json()
        except Exception as err:
            log.error(f"Fetch slurm metrics error: {err}")
    return metrics


def get_slurm_url(slurm_config: dict, url_type: str):
    """get_slurm_nodes_url Get Slurm Nodes Url

    Get the url for reading nodes info from slurm

    Args:
        slurm_config (dict): Slurm Configuration
        url_type: Url type. nodes or jobs
    """
    base_url = f"http://{slurm_config['ip']}:{slurm_config['port']}"
    url_types = ['nodes', 'jobs']
    if url_type not in url_types:
        raise ValueError(f"Invalid url type. Expected one of: {url_types}")

    if url_type == 'nodes':
        url = f"{base_url}{slurm_config['slurm_nodes']}"
    else:
        url = f"{base_url}{slurm_config['slurm_jobs']}"
    
    return url
