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

"""Catalog validators for ER-BSM-002.

Provides validation functions for base OS version pinning, schema version
compatibility, and catalog integrity checks.
"""

from typing import List, Optional, Set, Tuple

from api.logging_utils import log_secure_info
from .exceptions import CatalogParseError
from .models import Catalog


class BaseOSVersionNotPinnedError(CatalogParseError):
    """One or more BaseOS entries are missing a pinned version.

    Raised when a catalog's BaseOS array contains entries without explicit
    Name and Version fields, which is required for reproducible builds.
    """

    def __init__(
        self,
        unpinned_entries: List[str],
        correlation_id: Optional[str] = None,
    ) -> None:
        msg = (
            f"BaseOS version pinning required: the following entries are "
            f"missing explicit version: {unpinned_entries}"
        )
        super().__init__(msg, correlation_id=correlation_id)
        self.unpinned_entries = unpinned_entries


def validate_base_os_version_pinning(catalog: Catalog) -> List[str]:
    """Validate that all BaseOS entries have pinned Name and Version.

    Each entry in ``catalog.base_os`` must declare ``Name`` and ``Version``
    so the image builder knows which exact OS version to use. This
    prevents drift between catalog declaration and what Pulp serves.

    Args:
        catalog: Parsed Catalog instance.

    Returns:
        List of warning messages (empty if all entries are pinned).

    Raises:
        BaseOSVersionNotPinnedError: If any BaseOS entry is missing
            an explicit version.
    """
    unpinned: List[str] = []
    warnings: List[str] = []

    for i, entry in enumerate(catalog.base_os):
        name = entry.get("Name", "")
        version = entry.get("Version", "")

        if not name:
            unpinned.append(f"BaseOS[{i}] (unnamed)")
        elif not version:
            unpinned.append(name)
        else:
            log_secure_info(
                "debug",
                f"BaseOS version pinned: {name} {version}",
            )

    if unpinned:
        raise BaseOSVersionNotPinnedError(unpinned_entries=unpinned)

    log_secure_info(
        "info",
        f"BaseOS version pinning validated: {len(catalog.base_os)} entries OK",
    )
    return warnings


def extract_base_os_versions(catalog: Catalog) -> List[Tuple[str, str]]:
    """Extract (os_name, os_version) pairs from the catalog BaseOS layer.

    Useful for downstream Pulp validation — the caller can verify that
    the declared OS versions have corresponding repository content in Pulp.

    Args:
        catalog: Parsed Catalog instance.

    Returns:
        List of (os_name, os_version) tuples.
    """
    pairs: List[Tuple[str, str]] = []
    for entry in catalog.base_os:
        name = entry.get("Name", "")
        version = entry.get("Version", "")
        if name and version:
            pairs.append((name, version))
    return pairs


def validate_schema_version_compatibility(
    catalog: Catalog,
    supported: Set[int],
) -> None:
    """Validate catalog schema version against the supported set.

    This is a convenience wrapper around the parser-level check,
    usable for post-parse validation or re-validation flows.

    Args:
        catalog: Parsed Catalog instance.
        supported: Set of supported schema versions.

    Raises:
        CatalogParseError: If schema version is not in the supported set.
    """
    from .exceptions import UnsupportedSchemaVersionError

    if catalog.schema_version not in supported:
        raise UnsupportedSchemaVersionError(
            schema_version=catalog.schema_version,
            supported=supported,
        )
