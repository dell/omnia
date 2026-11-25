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

"""Dependency-free helpers of the external GitLab checks (version, expiry, CA mode)."""

from datetime import date, datetime, timezone
from typing import Optional

from .vars.execute_vars import EXTERNAL_CA_MAX_MODE


def gitlab_major_version(version: str) -> Optional[int]:
    """Return the major number of ``17.4.1-ee`` (None when unparsable)."""
    try:
        return int(str(version).split(".", maxsplit=1)[0])
    except ValueError:
        return None


def days_until(expires_at: str, today: Optional[date] = None) -> Optional[int]:
    """Return the whole days from ``today`` to a ``YYYY-MM-DD`` date (None when unset)."""
    if not expires_at:
        return None
    try:
        expiry = datetime.strptime(str(expires_at)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    return (expiry - (today or datetime.now(timezone.utc).date())).days


def mode_is_ca_safe(mode: str) -> bool:
    """Return whether an octal mode is 0644 or stricter with no execute bit."""
    try:
        value = int(mode, 8)
    except ValueError:
        return False
    return value & ~EXTERNAL_CA_MAX_MODE == 0 and value & 0o111 == 0
