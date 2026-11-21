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

"""Minimal GitLab REST client used by the external GitLab modules (ER-BSM-003).

Secrets are never placed in error text; only the HTTP status, method and path
are reported.
"""

import json
import time
from typing import Any, Dict, Optional, Sequence, Tuple
from urllib.parse import quote

from ansible.module_utils.urls import open_url

RETRY_DELAYS = (5, 15, 45)
SUPPORTED_MAJOR_VERSIONS = (17, 18, 19)
REQUIRED_PAT_SCOPES = ("api", "write_repository")
MIN_NAMESPACE_ACCESS_LEVEL = 40
DEFAULT_TIMEOUT = 30


class GitLabApiError(Exception):
    """Raised when a GitLab API call fails; carries the HTTP status (0 when unreachable)."""

    def __init__(self, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.status = status


class GitLabClient:
    """Thin JSON client for the GitLab v4 API with optional custom CA and retries."""

    def __init__(
        self,
        base_url: str,
        token: str,
        ca_path: Optional[str] = None,
        sleep=time.sleep,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._ca_path = ca_path or None
        self._sleep = sleep
        self._timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        ok: Sequence[int] = (200,),
        retry: bool = True,
    ) -> Tuple[int, Any]:
        """Call the API and return (status, parsed JSON). Retries transport/5xx errors."""
        delays = RETRY_DELAYS if retry else ()
        attempt = 0
        while True:
            try:
                return self._once(method, path, body, ok)
            except GitLabApiError as exc:
                retriable = exc.status == 0 or exc.status >= 500
                if not retriable or attempt >= len(delays):
                    raise
                self._sleep(delays[attempt])
                attempt += 1

    def _once(self, method, path, body, ok) -> Tuple[int, Any]:
        data = json.dumps(body) if body is not None else None
        headers = {"PRIVATE-TOKEN": self._token, "Content-Type": "application/json"}
        try:
            resp = open_url(
                f"{self.base_url}/api/v4{path}",
                method=method,
                data=data,
                headers=headers,
                ca_path=self._ca_path,
                validate_certs=True,
                timeout=self._timeout,
            )
            status, raw = resp.getcode(), resp.read()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            status = getattr(exc, "code", 0) or 0
            if status in ok:
                return status, None
            reason = f"HTTP {status}" if status else exc.__class__.__name__
            raise GitLabApiError(f"{method} {path} failed: {reason}", status) from exc
        if status not in ok:
            raise GitLabApiError(f"{method} {path} failed: HTTP {status}", status)
        try:
            return status, json.loads(raw) if raw else None
        except ValueError:
            return status, None

    def get(self, path: str, ok: Sequence[int] = (200,), retry: bool = True) -> Tuple[int, Any]:
        """GET helper."""
        return self.request("GET", path, ok=ok, retry=retry)


def parse_major_minor(version: str) -> Optional[Tuple[int, int]]:
    """Parse '17.4.1-ee' into (17, 4); None when unparseable."""
    parts = version.split(".")
    try:
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        return None


def encode_namespace(namespace: str) -> str:
    """URL-encode a group path for use in an API path segment."""
    return quote(namespace, safe="")
