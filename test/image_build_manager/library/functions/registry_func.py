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

"""OCI registry image verification functions."""

import json
from typing import Dict, Any

from ._config_helpers import get_configured_functional_groups
from ..vars.common_vars import CMDS, REGISTRY_PORT


# =============================================================================
# REGISTRY IMAGE VERIFICATION
# =============================================================================

def check_registry_images(
    host, arch: str = "x86_64"
) -> Dict[str, Any]:
    """Verify base and compute images exist in the local registry.

    Queries the registry catalog via HTTP/HTTPS curl. Falls back
    to regctl if curl is unavailable.

    Args:
        host: testinfra host object
        arch: Architecture filter

    Returns:
        Dict with 'success', 'registry_url', 'found', 'missing'.
    """
    hostname_cmd = host.run(CMDS["hostname_short"])
    if hostname_cmd.rc != 0:
        return {
            "success": False,
            "registry_url": "",
            "found_images": [],
            "missing_images": [],
            "error": "Failed to get hostname",
        }

    fqdn = hostname_cmd.stdout.strip()
    registry_url = f"{fqdn}:{REGISTRY_PORT}"

    groups = get_configured_functional_groups(host, arch=arch)

    if not groups:
        return {
            "success": True,
            "skipped": True,
            "registry_url": registry_url,
            "found_images": [],
            "missing_images": [],
            "details": f"No {arch} functional groups configured",
        }

    # Expected images: base + one per functional group
    expected = [f"rhel-{arch}-base"]
    for fg in groups:
        expected.append(f"rhel-{fg}")

    # Query registry catalog via curl (try HTTP first, then HTTPS)
    catalog_repos = []
    for scheme in ("http", "https"):
        curl_cmd = host.run(
            CMDS["curl_registry_catalog_scheme"].format(
                scheme=scheme, port=REGISTRY_PORT,
            )
        )
        if curl_cmd.rc == 0 and "repositories" in curl_cmd.stdout:
            try:
                data = json.loads(curl_cmd.stdout)
                catalog_repos = data.get("repositories", [])
            except (json.JSONDecodeError, ValueError):
                catalog_repos = []
            if catalog_repos:
                break

    if not catalog_repos:
        # Fallback to regctl
        regctl_cmd = host.run(
            CMDS["regctl_repo_ls"].format(registry=registry_url)
        )
        if regctl_cmd.rc == 0:
            catalog_repos = [
                r.strip()
                for r in regctl_cmd.stdout.strip().split("\n")
                if r.strip()
            ]

    if not catalog_repos:
        return {
            "success": False,
            "registry_url": registry_url,
            "found_images": [],
            "missing_images": expected,
            "error": "Cannot query registry catalog",
        }

    # Flatten: registry repos may be prefixed (hostname/image)
    # Normalize by stripping hostname prefix for matching
    normalized_repos = []
    for repo in catalog_repos:
        normalized_repos.append(repo)
        if "/" in repo:
            normalized_repos.append(repo.split("/", 1)[1])

    found = []
    missing = []
    for img in expected:
        # Match: exact, partial, or with version suffix
        matched = any(
            img in repo for repo in normalized_repos
        )
        if matched:
            found.append(img)
        else:
            missing.append(img)

    return {
        "success": len(missing) == 0,
        "registry_url": registry_url,
        "found_images": found,
        "missing_images": missing,
        "details": (
            f"All x86_64 images found in registry"
            if not missing
            else f"Missing: {', '.join(missing)}"
        ),
        "error": None if not missing else (
            f"Missing: {', '.join(missing)}"
        ),
    }
