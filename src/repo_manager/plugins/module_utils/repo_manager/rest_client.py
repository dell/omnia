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
"""Provide a small CA-verified HTTPS client for Pulp operations."""

import json
import http.client
import os
import ssl
import base64
from urllib.parse import urlparse

from ansible.module_utils.repo_manager.config import PULP_SSL_CA_CERT


class RestClient:
    """
    REST client to interact with HTTP(S) endpoints using JSON-based POST and GET requests.
    HTTPS peers are verified with the configured Pulp CA bundle.

    Args:
        base_url (str): The base URL of the server (e.g., https://localhost:443).
        username (str): Username for basic authentication.
        password (str): Password for basic authentication.
    """

    def __init__(self, base_url, username, password, ca_bundle=None):
        self.base_url = base_url
        self.ca_bundle = (
            ca_bundle
            or os.environ.get("PULP_CA_BUNDLE")
            or PULP_SSL_CA_CERT
        )
        auth = f"{username}:{password}"
        auth_encoded = base64.b64encode(auth.encode()).decode()
        self.headers = {
            "Content-type": "application/json",
            "Authorization": f"Basic {auth_encoded}"
        }

    def get_connection(self):
        """
        Create a certificate- and hostname-verified HTTPS connection.

        Returns:
            http.client.HTTPConnection or http.client.HTTPSConnection: A connection instance.
        """
        parsed_url = urlparse(self.base_url)

        if (
                parsed_url.scheme != "https"
                or not parsed_url.hostname
                or parsed_url.username is not None
                or parsed_url.password is not None
        ):
            raise ValueError("Pulp base URL must be an HTTPS origin without credentials")

        context = ssl.create_default_context(cafile=self.ca_bundle)
        context.check_hostname = True
        return http.client.HTTPSConnection(
            parsed_url.hostname,
            parsed_url.port or 443,
            context=context,
            timeout=60,
        )

    def post(self, uri, data):
        """
        Sends a POST request with a JSON body to the specified URI.

        Args:
            uri (str): The endpoint URI.
            data (dict): Data to send as JSON.

        Returns:
            dict or None: Parsed JSON response if successful, None otherwise.
        """
        conn = None
        try:
            conn = self.get_connection()
            conn.request("POST", uri, body=json.dumps(data), headers=self.headers)
            response = conn.getresponse()
            if response.status != 202:
                return None
            return json.loads(response.read())
        except Exception:
            return None
        finally:
            if conn is not None:
                conn.close()

    def get(self, uri):
        """
        Sends a GET request and parses the response as JSON.

        Args:
            uri (str): The endpoint URI.

        Returns:
            dict or None: Parsed JSON response if status is 200, None otherwise.
        """
        conn = None
        try:
            conn = self.get_connection()
            conn.request("GET", uri, headers=self.headers)
            response = conn.getresponse()
            if response.status != 200:
                return None
            return json.loads(response.read())
        except Exception:
            return None
        finally:
            if conn is not None:
                conn.close()

    def raw_get(self, uri):
        """
        Sends a GET request and returns the raw HTTP response.

        Args:
            uri (str): The endpoint URI.

        Returns:
            http.client.HTTPResponse or None: Response object if request succeeds, None otherwise.
        """
        conn = None
        try:
            conn = self.get_connection()
            conn.request("GET", uri, headers=self.headers)
            return conn.getresponse()
        except Exception:
            if conn is not None:
                conn.close()
            return None
