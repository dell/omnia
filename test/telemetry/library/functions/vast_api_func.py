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

"""Authenticated VAST notification API operations for Telemetry FVT."""

import ipaddress
import re
import time
import warnings

import requests
from urllib3.exceptions import InsecureRequestWarning

from ..vars.common_vars import (
    VAST_API_LOGIN_STATUS,
    VAST_API_PATHS,
    VAST_API_READ_STATUS,
    VAST_API_SCHEME,
    VAST_API_TIMEOUT_SECONDS,
    VAST_API_TRIGGER_STATUS,
    VAST_API_UPDATE_STATUS,
    VAST_SYSLOG_PROTOCOL,
    VAST_SYSLOG_REQUIRED_SETTINGS,
)


class VastApiError(RuntimeError):
    """Safe failure raised by VAST API operations."""


def _validated_endpoint(value):
    """Return a safe IP address or DNS hostname for URL construction."""
    endpoint = str(value or "").strip()
    if not endpoint or len(endpoint) > 253:
        raise VastApiError("VAST endpoint is missing or too long")
    if any(char in endpoint for char in ("/", "\\", "@", "#", "?")):
        raise VastApiError(
            "VAST endpoint must be an IP address or hostname without a URL"
        )
    try:
        address = ipaddress.ip_address(endpoint)
    except ValueError as exc:
        hostname_pattern = (
            r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
            r"[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:"
            r"[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*"
        )
        if not re.fullmatch(hostname_pattern, endpoint):
            raise VastApiError(
                "VAST endpoint is not a valid IP or hostname"
            ) from exc
        return endpoint
    return f"[{address}]" if address.version == 6 else str(address)


def _validated_port(value):
    """Return a valid TCP port."""
    if isinstance(value, bool):
        raise VastApiError("VAST API port must be an integer")
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise VastApiError("VAST API port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise VastApiError("VAST API port must be between 1 and 65535")
    return port


class _VastApiClient:
    """Small authenticated client for VAST notification configuration."""

    def __init__(self, context):
        """Initialize the client from validated in-memory settings."""
        endpoint = _validated_endpoint(context.get("endpoint"))
        port = _validated_port(context.get("port"))
        self.username = context.get("username", "")
        self.password = context.get("password", "")
        if not self.username or not self.password:
            raise VastApiError("VAST API credentials are incomplete")
        self.base_url = f"{VAST_API_SCHEME}://{endpoint}:{port}"
        self.verify_tls = context.get("verify_tls", True)
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def __enter__(self):
        """Authenticate and return this client for a bounded session."""
        try:
            token_payload, _ = self._request(
                "POST",
                VAST_API_PATHS["token"],
                VAST_API_LOGIN_STATUS,
                payload={
                    "username": self.username,
                    "password": self.password,
                },
            )
            access_token = (
                token_payload.get("access")
                if isinstance(token_payload, dict) else ""
            )
            if not isinstance(access_token, str) or not access_token:
                raise VastApiError("VAST token response did not contain access")
            self.session.headers["Authorization"] = f"Bearer {access_token}"
        except VastApiError:
            self.username = ""
            self.password = ""
            self.session.close()
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Drop authentication references and close the HTTP session."""
        self.session.headers.pop("Authorization", None)
        self.username = ""
        self.password = ""
        self.session.close()

    def _request(self, method, path, expected_status, payload=None):
        """Issue one API request and return parsed content plus status."""
        request_args = {
            "method": method,
            "url": f"{self.base_url}{path}",
            "timeout": VAST_API_TIMEOUT_SECONDS,
            "verify": self.verify_tls,
            "allow_redirects": False,
        }
        if payload is not None:
            request_args["json"] = payload
        try:
            with warnings.catch_warnings():
                if self.verify_tls is False:
                    warnings.simplefilter("ignore", InsecureRequestWarning)
                response = self.session.request(  # nosec B501
                    **request_args,
                )
        except requests.RequestException as exc:
            raise VastApiError(
                f"VAST API request failed for {method} {path}: "
                f"{exc.__class__.__name__}"
            ) from exc

        if response.status_code not in expected_status:
            raise VastApiError(
                f"VAST API returned HTTP {response.status_code} for "
                f"{method} {path}"
            )
        if not response.content:
            return {}, response.status_code
        try:
            return response.json(), response.status_code
        except requests.JSONDecodeError as exc:
            raise VastApiError(
                f"VAST API returned invalid JSON for {method} {path}"
            ) from exc

    def list_notification_configs(self):
        """List VAST default notification configurations."""
        return self._request(
            "GET", VAST_API_PATHS["config_list"], VAST_API_READ_STATUS,
        )

    def get_notification_config(self, config_id):
        """Read one VAST default notification configuration."""
        path = VAST_API_PATHS["config_detail"].format(config_id=config_id)
        return self._request("GET", path, VAST_API_READ_STATUS)

    def update_notification_config(self, config_id, payload):
        """Partially update one VAST notification configuration."""
        path = VAST_API_PATHS["config_detail"].format(config_id=config_id)
        return self._request(
            "PATCH", path, VAST_API_UPDATE_STATUS, payload=payload,
        )

    def trigger_test_notification(self, config_id):
        """Ask VAST to emit a test notification using saved settings."""
        path = VAST_API_PATHS["config_test"].format(config_id=config_id)
        return self._request(
            "PATCH", path, VAST_API_TRIGGER_STATUS, payload={},
        )


def _config_items(payload):
    """Normalize paginated and direct-list VAST API responses."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload["results"]
    raise VastApiError("VAST notification list has an unexpected structure")


def _select_config_id(payload):
    """Select the same first configuration used by the VAST management UI."""
    items = _config_items(payload)
    if not items:
        raise VastApiError("VAST returned no default notification configuration")
    config_id = items[0].get("id") if isinstance(items[0], dict) else None
    if isinstance(config_id, bool) or not isinstance(config_id, int):
        raise VastApiError("VAST notification configuration has no numeric ID")
    return config_id


def _normalized_setting(name, value):
    """Normalize one API setting before comparing readback."""
    if name == "syslog_port":
        return _validated_port(value)
    if name == "syslog_protocol":
        return str(value or "").strip().lower()
    if name == "syslog_host":
        return str(value or "").strip()
    return value


def _reconcile_syslog_settings(client, config_id, desired):
    """Apply changed syslog settings and verify the saved readback."""
    current, _ = client.get_notification_config(config_id)
    if not isinstance(current, dict):
        raise VastApiError(
            "VAST notification configuration has an unexpected structure"
        )
    unavailable = [
        name for name, required in VAST_SYSLOG_REQUIRED_SETTINGS.items()
        if current.get(name) is not required
    ]
    if unavailable:
        raise VastApiError(
            "VAST notification prerequisites are disabled: "
            + ", ".join(unavailable)
        )

    changed = any(
        _normalized_setting(name, current.get(name)) != value
        for name, value in desired.items()
    )
    if changed:
        client.update_notification_config(config_id, desired)

    readback, readback_status = client.get_notification_config(config_id)
    if not isinstance(readback, dict):
        raise VastApiError(
            "VAST notification readback has an unexpected structure"
        )
    mismatches = [
        name for name, value in desired.items()
        if _normalized_setting(name, readback.get(name)) != value
    ]
    if mismatches:
        raise VastApiError(
            "VAST syslog readback differs for: " + ", ".join(mismatches)
        )
    return changed, readback_status


def configure_event_notifications(context, syslog_host, syslog_port):
    """Configure VAST syslog, verify readback, and emit one test event."""
    target = _validated_endpoint(syslog_host).strip("[]")
    port = _validated_port(syslog_port)
    desired = {
        "syslog_host": target,
        "syslog_port": port,
        "syslog_protocol": VAST_SYSLOG_PROTOCOL,
    }

    with _VastApiClient(context) as client:
        listing, _ = client.list_notification_configs()
        config_id = _select_config_id(listing)
        changed, readback_status = _reconcile_syslog_settings(
            client, config_id, desired,
        )
        trigger_epoch = time.time()
        _, trigger_status = client.trigger_test_notification(config_id)

    return {
        "config_id": config_id,
        "changed": changed,
        "readback_status": readback_status,
        "trigger_status": trigger_status,
        "trigger_epoch": trigger_epoch,
        "syslog_host": target,
        "syslog_port": port,
        "syslog_protocol": VAST_SYSLOG_PROTOCOL,
    }
