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
"""Network-value helpers for the dataset generator CLI."""

import ipaddress
import re


_HOST_LABEL_PATTERN = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
)
_DOTTED_NUMERIC_PATTERN = re.compile(r"(?:[0-9]+\.){3}[0-9]+")
DOCUMENTATION_REPO_MANAGER_HOST = "repo.example.invalid"
_DOCUMENTATION_DNS_SUFFIXES = (
    "invalid", "test", "example", "localhost",
    "example.com", "example.net", "example.org",
)
_DOCUMENTATION_IPV4_NETWORKS = tuple(
    ipaddress.IPv4Network(cidr)
    for cidr in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
)


def validate_hostname_or_ipv4(value: str) -> str:
    """Return a valid hostname/IPv4 value or raise ``ValueError``."""
    if not value or len(value) > 253 or value != value.strip():
        raise ValueError("must be a non-empty hostname or IPv4 address")
    if any(character in value for character in ":/@[]"):
        raise ValueError("must not include a scheme, credentials, port, or path")
    if _DOTTED_NUMERIC_PATTERN.fullmatch(value):
        try:
            ipaddress.IPv4Address(value)
        except ipaddress.AddressValueError as exc:
            raise ValueError("is not a valid IPv4 address") from exc
        return value
    labels = value.split(".")
    if any(
        not label
        or len(label) > 63
        or not _HOST_LABEL_PATTERN.fullmatch(label)
        for label in labels
    ):
        raise ValueError("is not a valid DNS hostname")
    return value


def is_documentation_host(hostname: str) -> bool:
    """Return whether a host is reserved exclusively for examples/tests."""
    lowered = hostname.lower()
    if _DOTTED_NUMERIC_PATTERN.fullmatch(lowered):
        try:
            address = ipaddress.IPv4Address(lowered)
        except ipaddress.AddressValueError:
            return False
        return any(address in network for network in _DOCUMENTATION_IPV4_NETWORKS)
    return any(
        lowered == suffix or lowered.endswith(f".{suffix}")
        for suffix in _DOCUMENTATION_DNS_SUFFIXES
    )
