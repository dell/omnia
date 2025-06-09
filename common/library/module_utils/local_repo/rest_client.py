# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

import json
import http.client
import ssl
import base64
from urllib.parse import urlparse

class RestClient:
    """
    REST client to interact with HTTP(S) endpoints using JSON-based POST and GET requests.
    SSL verification is disabled for all requests.

    Args:
        base_url (str): The base URL of the server (e.g., https://localhost:443).
        username (str): Username for basic authentication.
        password (str): Password for basic authentication.
    """

    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        auth = f"{username}:{password}"
        auth_encoded = base64.b64encode(auth.encode()).decode()
        self.headers = {
            "Content-type": "application/json",
            "Authorization": f"Basic {auth_encoded}"
        }

    def get_connection(self):
        """
        Creates an HTTP or HTTPS connection to the server.
        For HTTPS, SSL verification is disabled.
 
        Returns:
            http.client.HTTPConnection or http.client.HTTPSConnection: A connection instance.
        """
        parsed_url = urlparse(self.base_url)
 
        if parsed_url.scheme == 'https':
            context = ssl._create_unverified_context()
            return http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=context, timeout=60)
        elif parsed_url.scheme == 'http':
            return http.client.HTTPConnection(parsed_url.hostname, parsed_url.port, timeout=60)
        return None

    def post(self, uri, data):
        """
        Sends a POST request with a JSON body to the specified URI.

        Args:
            uri (str): The endpoint URI.
            data (dict): Data to send as JSON.

        Returns:
            dict or None: Parsed JSON response if successful, None otherwise.
        """
        conn = self.get_connection()
        try:
            conn.request("POST", uri, body=json.dumps(data), headers=self.headers)
            response = conn.getresponse()
            if response.status != 202:
                return None
            return json.loads(response.read())
        except Exception:
            return None
        finally:
            conn.close()

    def get(self, uri):
        """
        Sends a GET request and parses the response as JSON.

        Args:
            uri (str): The endpoint URI.

        Returns:
            dict or None: Parsed JSON response if status is 200, None otherwise.
        """
        conn = self.get_connection()
        try:
            conn.request("GET", uri, headers=self.headers)
            response = conn.getresponse()
            if response.status != 200:
                return None
            return json.loads(response.read())
        except Exception:
            return None
        finally:
            conn.close()

    def raw_get(self, uri):
        """
        Sends a GET request and returns the raw HTTP response.

        Args:
            uri (str): The endpoint URI.

        Returns:
            http.client.HTTPResponse or None: Response object if request succeeds, None otherwise.
        """
        conn = self.get_connection()
        try:
            conn.request("GET", uri, headers=self.headers)
            return conn.getresponse()
        except Exception:
            return None
