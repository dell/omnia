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

# pylint: disable=missing-function-docstring,too-few-public-methods,too-many-arguments,too-many-positional-arguments
"""Small, dependency-free HTTP clients for the OpenCHAMI gateway.

The clients deliberately use the public HAProxy routes.  They do not connect
to container-private HTTP ports and they never disable TLS verification.
"""

import json
import ssl
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


class OpenChamiError(RuntimeError):
    """Base error for OpenCHAMI client operations."""


class OpenChamiTransportError(OpenChamiError):
    """Raised when the gateway cannot be reached or TLS validation fails."""


class OpenChamiAPIError(OpenChamiError):
    """Raised when an OpenCHAMI API returns an unexpected response."""

    def __init__(self, method, url, status, message):
        super().__init__(f"{method} {url} returned HTTP {status}: {message}")
        self.method = method
        self.url = url
        self.status = status


@dataclass(frozen=True)
class APIResponse:
    """Normalized HTTP response."""

    status: int
    body: Any
    content_type: str


class OpenChamiClient:
    """Authenticated JSON client for one OpenCHAMI gateway."""

    _RETRYABLE_STATUS = frozenset((429, 500, 502, 503, 504))
    _RETRYABLE_METHODS = frozenset(("GET", "HEAD", "PUT", "DELETE"))
    _MAX_RESPONSE_BYTES = 16 * 1024 * 1024

    def __init__(
        self,
        base_url: str,
        token: str | None,
        ca_cert: str | None = None,
        timeout: int = 15,
        retries: int = 3,
        retry_delay: float = 1.0,
    ):
        if not base_url:
            raise ValueError("OpenCHAMI base URL is required")
        parsed = parse.urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("OpenCHAMI base URL must use HTTPS")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError(
                "OpenCHAMI base URL cannot contain credentials, a query, or a fragment"
            )
        if not (token or "").strip():
            raise ValueError("OpenCHAMI JWT access token is required")
        self.base_url = base_url.rstrip("/")
        self.token = token.strip()
        self.ca_cert = ca_cert
        self.timeout = timeout
        self.retries = max(1, retries)
        self.retry_delay = max(0.0, retry_delay)
        try:
            self.ssl_context = ssl.create_default_context(cafile=ca_cert)
        except (OSError, ssl.SSLError) as exc:
            raise OpenChamiTransportError(
                f"Unable to load OpenCHAMI CA certificate {ca_cert!r}: {exc}"
            ) from exc

    def request_json(
        self,
        method: str,
        path: str,
        payload: Any | None = None,
        expected: Sequence[int] = (200,),
    ) -> APIResponse:
        """Send one JSON request and validate its HTTP status."""
        method = method.upper()
        url = self._url(path)
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"

        attempts = self.retries if method in self._RETRYABLE_METHODS else 1
        last_error = None
        for attempt in range(1, attempts + 1):
            req = request.Request(url, data=data, headers=headers, method=method)
            try:
                with request.urlopen(  # nosec B310 - scheme is required to be HTTPS above
                    req,
                    timeout=self.timeout,
                    context=self.ssl_context,
                ) as response:
                    raw = self._read_limited(response)
                    return self._response(
                        method,
                        url,
                        response.status,
                        response.headers.get("Content-Type", ""),
                        raw,
                        expected,
                    )
            except error.HTTPError as exc:
                raw = self._read_limited(exc)
                if (
                    exc.code in self._RETRYABLE_STATUS
                    and attempt < attempts
                ):
                    time.sleep(self.retry_delay * attempt)
                    continue
                return self._response(
                    method,
                    url,
                    exc.code,
                    exc.headers.get("Content-Type", "") if exc.headers else "",
                    raw,
                    expected,
                )
            except (error.URLError, TimeoutError, ssl.SSLError) as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(self.retry_delay * attempt)
                    continue
                break

        raise OpenChamiTransportError(
            f"{method} {url} failed after {attempts} attempt(s): {last_error}"
        )

    @classmethod
    def _read_limited(cls, response) -> bytes:
        """Read an HTTP body without allowing an upstream memory exhaustion."""
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                declared_length = int(content_length)
            except ValueError:
                declared_length = None
            if (
                declared_length is not None
                and declared_length > cls._MAX_RESPONSE_BYTES
            ):
                raise OpenChamiTransportError(
                    "OpenCHAMI response exceeds the maximum allowed size"
                )
        raw = response.read(cls._MAX_RESPONSE_BYTES + 1)
        if len(raw) > cls._MAX_RESPONSE_BYTES:
            raise OpenChamiTransportError(
                "OpenCHAMI response exceeds the maximum allowed size"
            )
        return raw

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return self.base_url + path

    @staticmethod
    def _decode(raw: bytes, content_type: str) -> Any:
        if not raw:
            return None
        text = raw.decode("utf-8", errors="replace")
        if "json" in content_type.lower() or text[:1] in ("{", "["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        return text

    @classmethod
    def _response(cls, method, url, status, content_type, raw, expected):
        body = cls._decode(raw, content_type)
        if status not in expected:
            if isinstance(body, (dict, list)):
                message = json.dumps(body, separators=(",", ":"))
            else:
                message = str(body or "empty response")
            # Avoid unbounded error output from a proxy or upstream service.
            raise OpenChamiAPIError(method, url, status, message[:1000])
        return APIResponse(status=status, body=body, content_type=content_type)


class SMDClient:
    """Operations used by Omnia against SMD."""

    BASE = "/hsm/v2"

    def __init__(self, client: OpenChamiClient):
        self.client = client

    def health(self) -> dict[str, Any]:
        return self.client.request_json("GET", f"{self.BASE}/service/ready").body

    def components(self) -> list[dict[str, Any]]:
        body = self.client.request_json("GET", f"{self.BASE}/State/Components").body
        if isinstance(body, dict):
            return body.get("Components", [])
        return body or []

    def interfaces(self) -> list[dict[str, Any]]:
        body = self.client.request_json(
            "GET", f"{self.BASE}/Inventory/EthernetInterfaces"
        ).body
        return body or []

    def hardware_inventory(self) -> list[dict[str, Any]]:
        """Return SMD Hardware Inventory records by location XNAME."""
        body = self.client.request_json(
            "GET", f"{self.BASE}/Inventory/Hardware"
        ).body
        return body or []

    def create_hardware_inventory(
        self,
        records: Iterable[dict[str, Any]],
    ) -> Any:
        """Create or update native SMD Hardware Inventory records."""
        hardware = list(records)
        if not hardware:
            return None
        return self.client.request_json(
            "POST",
            f"{self.BASE}/Inventory/Hardware",
            {"Hardware": hardware},
            expected=(200,),
        ).body

    def groups(self) -> list[dict[str, Any]]:
        body = self.client.request_json("GET", f"{self.BASE}/groups").body
        return body or []

    def create_group(self, group: dict[str, Any]) -> Any:
        """Create one SMD group with its initial membership."""
        return self.client.request_json(
            "POST",
            f"{self.BASE}/groups",
            group,
            expected=(201,),
        ).body

    def set_group_members(self, label: str, xnames: Iterable[str]) -> Any:
        """Replace an existing SMD group's membership atomically."""
        path = f"{self.BASE}/groups/{self._segment(label)}/members"
        return self.client.request_json(
            "PUT",
            path,
            {"ids": self._unique(xnames)},
            expected=(201,),
        ).body

    def delete_group(self, label: str) -> bool:
        """Delete one SMD group, treating an absent group as success."""
        path = f"{self.BASE}/groups/{self._segment(label)}"
        response = self.client.request_json(
            "DELETE", path, expected=(200, 404)
        )
        return response.status != 404

    def delete_component_endpoints(self, xnames: Iterable[str]):
        return self._delete_many("Inventory/ComponentEndpoints", xnames)

    def delete_redfish_endpoints(self, xnames: Iterable[str]):
        return self._delete_many("Inventory/RedfishEndpoints", xnames)

    def delete_interfaces(self, interface_ids: Iterable[str]):
        return self._delete_many("Inventory/EthernetInterfaces", interface_ids)

    def delete_components(self, xnames: Iterable[str]):
        return self._delete_many("State/Components", xnames)

    def delete_group_member(self, label: str, xname: str) -> bool:
        """Remove one node from an SMD group, tolerating its absence."""
        path = (
            f"{self.BASE}/groups/{self._segment(label)}"
            f"/members/{self._segment(xname)}"
        )
        response = self.client.request_json(
            "DELETE", path, expected=(200, 204, 404)
        )
        return response.status != 404

    def _delete_many(self, collection: str, identifiers: Iterable[str]):
        deleted = []
        missing = []
        for identifier in self._unique(identifiers):
            path = f"{self.BASE}/{collection}/{self._segment(identifier)}"
            response = self.client.request_json(
                "DELETE", path, expected=(200, 204, 404)
            )
            (missing if response.status == 404 else deleted).append(identifier)
        return {"deleted": deleted, "missing": missing}

    @staticmethod
    def _segment(value: str) -> str:
        return parse.quote(str(value), safe="")

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(str(value).strip() for value in values if value))


class MetadataClient:
    """Operations used by Omnia against Metadata Service."""

    BASE = "/metadata-service"

    def __init__(self, client: OpenChamiClient):
        self.client = client

    def health(self) -> dict[str, Any]:
        return self.client.request_json("GET", f"{self.BASE}/health").body

    def instance_infos(self) -> list[dict[str, Any]]:
        body = self.client.request_json("GET", f"{self.BASE}/instanceinfos").body
        return body or []

    def create_instance_info(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.client.request_json(
            "POST", f"{self.BASE}/instanceinfos", payload, expected=(200, 201)
        ).body

    def update_instance_info(self, uid: str, payload: dict[str, Any]):
        path = f"{self.BASE}/instanceinfos/{parse.quote(uid, safe='')}"
        return self.client.request_json("PUT", path, payload, expected=(200,)).body

    def delete_instance_info(self, uid: str) -> bool:
        path = f"{self.BASE}/instanceinfos/{parse.quote(uid, safe='')}"
        response = self.client.request_json(
            "DELETE", path, expected=(200, 204, 404)
        )
        return response.status != 404


class BootServiceClient:
    """Read operations used to validate Boot Service authentication."""

    BASE = "/boot-service"

    def __init__(self, client: OpenChamiClient):
        self.client = client

    def health(self) -> dict[str, Any]:
        return self.client.request_json("GET", f"{self.BASE}/health").body

    def boot_configurations(self) -> list[dict[str, Any]]:
        body = self.client.request_json(
            "GET", f"{self.BASE}/bootconfigurations"
        ).body
        return body or []
