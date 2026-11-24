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

"""Syntax checks for external GitLab URL and namespace inputs (ER-BSM-003)."""

import re

_URL_RE = re.compile(
    r"^https://[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?(:[0-9]{1,5})?(/[A-Za-z0-9._~/-]*)?$"
)
_NAMESPACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*(/[A-Za-z0-9][A-Za-z0-9_.-]*)*$")


def is_valid_external_url(value: str) -> bool:
    """True for an HTTPS URL with a valid host, optional port (1-65535) and path."""
    if not _URL_RE.match(value):
        return False
    port = re.search(r"^https://[^/:]+:([0-9]+)", value)
    return not port or 1 <= int(port.group(1)) <= 65535


def is_valid_namespace(value: str) -> bool:
    """True for a GitLab group path such as 'infra/omnia-builds'."""
    return bool(_NAMESPACE_RE.match(value))
