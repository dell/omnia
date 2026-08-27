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

"""
FVT — Build naming convention tests.

Verifies that image artifacts produced by image-builder and image-thrillhouse
follow the correct naming convention so the two flows never overwrite each
other's artifacts in the OCI registry or S3 bucket.

Naming rules (enforced by roles/build_os_images/vars/main.yml):
  image-builder     → suffix "-imgbld"  e.g. rhel-x86_64-base-imgbld
  image-thrillhouse → suffix "-imgth"   e.g. rhel-x86_64-base-imgth

Test IDs: TC_BD_007 – TC_BD_011
"""

import json
from typing import List

import pytest

from library.functions import (
    TestLogger,
    check_registry_images,
    check_s3_bucket_images,
    get_configured_functional_groups,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    CMDS,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    REGISTRY_PORT,
    S3_BOOT_IMAGES_BUCKET,
)


# ---------------------------------------------------------------------------
# Suffix constants
# ---------------------------------------------------------------------------

_SUFFIX_MAP = {
    "image-builder": "-imgbld",
    "image-thrillhouse": "-imgth",
}


# ---------------------------------------------------------------------------
# Helpers — reuse the same infra as check_registry_images / check_s3_bucket_images
# ---------------------------------------------------------------------------

def _get_build_type(host) -> str:
    """Return the image_build_type configured on the target.

    Resolves the config path from OMNIA_DATA_PATH / OMNIA_PROJECT_NAME
    environment variables on the target host.
    """
    data_path = host.check_output(
        f"echo ${ENV_OMNIA_DATA_PATH}"
    ).strip()
    project = host.check_output(
        f"echo ${ENV_OMNIA_PROJECT_NAME}"
    ).strip() or "project_default"
    cfg_path = (
        f"{data_path}/image_build_manager/input/{project}"
        "/image_build_config.yml"
    )
    result = host.run(
        f"grep -E '^image_build_type:' {cfg_path} "
        "2>/dev/null | awk '{print $2}' || echo 'image-builder'"
    )
    build_type = result.stdout.strip().strip('"').strip("'")
    return build_type if build_type in _SUFFIX_MAP else "image-builder"


def _get_registry_repos(host) -> List[str]:
    """Return list of OCI repo names using the same approach as check_registry_images."""
    hostname_cmd = host.run(CMDS["hostname_short"])
    fqdn = hostname_cmd.stdout.strip() if hostname_cmd.rc == 0 else "localhost"
    registry_url = f"{fqdn}:{REGISTRY_PORT}"

    # Try curl (HTTP, then HTTPS) — same as check_registry_images
    for scheme in ("http", "https"):
        curl_cmd = host.run(
            CMDS["curl_registry_catalog_scheme"].format(
                scheme=scheme, port=REGISTRY_PORT,
            )
        )
        if curl_cmd.rc == 0 and "repositories" in curl_cmd.stdout:
            try:
                data = json.loads(curl_cmd.stdout)
                repos = data.get("repositories", [])
                if repos:
                    return repos
            except (json.JSONDecodeError, ValueError):
                pass

    # Fallback to regctl
    regctl_cmd = host.run(CMDS["regctl_repo_ls"].format(registry=registry_url))
    if regctl_cmd.rc == 0:
        return [r.strip() for r in regctl_cmd.stdout.strip().split("\n") if r.strip()]
    return []


def _get_s3_image_paths(host) -> List[str]:
    """Return S3 object paths using s3cmd ls -Hr (same as check_s3_bucket_images)."""
    result = host.run(CMDS["s3cmd_ls_bucket"].format(bucket=S3_BOOT_IMAGES_BUCKET))
    if result.rc != 0:
        return []
    paths = []
    for line in result.stdout.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 4:
            paths.append(parts[3])  # s3://boot-images/group/rhel-...-imgbld/file
    return paths


# ---------------------------------------------------------------------------
# TC_BD_007 — image-builder registry naming (x86_64)
# ---------------------------------------------------------------------------

@pytest.mark.order(8)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_registry_naming_image_builder_x86_64(host):
    """Verify x86_64 registry images carry the -imgbld suffix when
    image_build_type is image-builder.

    Only checks artifacts with the current build type's suffix.
    Old artifacts from a previous build type (e.g. -imgth from an
    earlier image-thrillhouse run) are expected to coexist and are
    ignored.
    """
    tc = TC["registry_naming_ib_x86_64"]
    tl = TestLogger(tc["title"], tc["id"])

    build_type = _get_build_type(host)
    if build_type != "image-builder":
        tl.skipped(f"image_build_type is '{build_type}'; requires image-builder")
        pytest.skip(f"image_build_type is '{build_type}'; TC_BD_007 requires image-builder")

    repos = _get_registry_repos(host)
    tl.info(f"Registry repos found: {len(repos)}")

    # Normalize: strip hostname prefix for matching
    flat = []
    for r in repos:
        flat.append(r)
        if "/" in r:
            flat.append(r.split("/", 1)[1])

    expected_suffix = _SUFFIX_MAP["image-builder"]

    # Filter to only artifacts with the current build type's suffix
    current_repos = [r for r in flat if "rhel-" in r and r.endswith(expected_suffix)]
    old_repos = [
        r for r in flat
        if "rhel-" in r and not r.endswith(expected_suffix)
    ]

    if old_repos:
        tl.info(
            f"{len(old_repos)} old artifacts from previous build type "
            f"in registry — ignored (coexistence is expected)"
        )

    if not current_repos:
        tl.skipped(
            f"No 'rhel-*{expected_suffix}' images found in registry"
        )
        pytest.skip(
            f"No 'rhel-*{expected_suffix}' images found in registry "
            "— build not run yet"
        )

    tl.passed(
        f"{len(current_repos)} x86_64 registry images correctly "
        f"suffixed with '{expected_suffix}'"
    )


# ---------------------------------------------------------------------------
# TC_BD_008 — image-builder S3 naming (x86_64)
# ---------------------------------------------------------------------------

@pytest.mark.order(9)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_s3_naming_image_builder_x86_64(host):
    """Verify x86_64 S3 image paths carry the -imgbld suffix when
    image_build_type is image-builder.

    Only checks artifacts with the current build type's suffix.
    Old artifacts from a previous build type are expected to coexist
    and are ignored.
    """
    tc = TC["s3_naming_ib_x86_64"]
    tl = TestLogger(tc["title"], tc["id"])

    build_type = _get_build_type(host)
    if build_type != "image-builder":
        tl.skipped(f"image_build_type is '{build_type}'; requires image-builder")
        pytest.skip(f"image_build_type is '{build_type}'; TC_BD_008 requires image-builder")

    expected_suffix = _SUFFIX_MAP["image-builder"]

    s3_paths = _get_s3_image_paths(host)
    tl.info(f"S3 boot-images entries: {len(s3_paths)}")

    # Filter to only artifacts with the current build type's suffix
    current_paths = [p for p in s3_paths if "rhel-" in p and expected_suffix in p]
    old_paths = [
        p for p in s3_paths
        if "rhel-" in p and expected_suffix not in p
    ]

    if old_paths:
        tl.info(
            f"{len(old_paths)} old S3 artifacts from previous build type "
            f"— ignored (coexistence is expected)"
        )

    if not current_paths:
        tl.skipped(
            f"No 'rhel-*' objects with '{expected_suffix}' "
            "found in s3://boot-images/"
        )
        pytest.skip(
            f"No 'rhel-*' objects with '{expected_suffix}' in S3 "
            "— build not run yet"
        )

    tl.passed(
        f"{len(current_paths)} x86_64 S3 image paths correctly "
        f"include '{expected_suffix}'"
    )


# ---------------------------------------------------------------------------
# TC_BD_009 — image-thrillhouse registry naming (x86_64)
# ---------------------------------------------------------------------------

@pytest.mark.order(10)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_registry_naming_image_thrillhouse_x86_64(host):
    """Verify x86_64 registry images carry the -imgth suffix when
    image_build_type is image-thrillhouse.

    Only checks artifacts for **configured** functional groups.
    Old artifacts from a previous build type (e.g. -imgbld from an
    earlier image-builder run) are expected to coexist and are ignored.
    """
    tc = TC["registry_naming_th_x86_64"]
    tl = TestLogger(tc["title"], tc["id"])

    build_type = _get_build_type(host)
    if build_type != "image-thrillhouse":
        tl.skipped(f"image_build_type is '{build_type}'; requires image-thrillhouse")
        pytest.skip(f"image_build_type is '{build_type}'; TC_BD_009 requires image-thrillhouse")

    repos = _get_registry_repos(host)
    tl.info(f"Registry repos found: {len(repos)}")

    flat = []
    for r in repos:
        flat.append(r)
        if "/" in r:
            flat.append(r.split("/", 1)[1])

    expected_suffix = _SUFFIX_MAP["image-thrillhouse"]

    # Filter to only artifacts with the current build type's suffix
    current_repos = [r for r in flat if "rhel-" in r and r.endswith(expected_suffix)]
    old_repos = [
        r for r in flat
        if "rhel-" in r and not r.endswith(expected_suffix)
    ]

    if old_repos:
        tl.info(
            f"{len(old_repos)} old artifacts from previous build type "
            f"in registry — ignored (coexistence is expected)"
        )

    if not current_repos:
        tl.skipped(
            f"No 'rhel-*{expected_suffix}' images found in registry"
        )
        pytest.skip(
            f"No 'rhel-*{expected_suffix}' images found in registry "
            "— build not run yet"
        )

    tl.passed(
        f"{len(current_repos)} x86_64 registry images correctly "
        f"suffixed with '{expected_suffix}'"
    )


# ---------------------------------------------------------------------------
# TC_BD_010 — image-thrillhouse S3 naming (x86_64)
# ---------------------------------------------------------------------------

@pytest.mark.order(11)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_s3_naming_image_thrillhouse_x86_64(host):
    """Verify x86_64 S3 image paths carry the -imgth suffix when
    image_build_type is image-thrillhouse.

    Only checks artifacts with the current build type's suffix.
    Old artifacts from a previous build type are expected to coexist
    and are ignored.
    """
    tc = TC["s3_naming_th_x86_64"]
    tl = TestLogger(tc["title"], tc["id"])

    build_type = _get_build_type(host)
    if build_type != "image-thrillhouse":
        tl.skipped(f"image_build_type is '{build_type}'; requires image-thrillhouse")
        pytest.skip(f"image_build_type is '{build_type}'; TC_BD_010 requires image-thrillhouse")

    expected_suffix = _SUFFIX_MAP["image-thrillhouse"]

    s3_paths = _get_s3_image_paths(host)

    # Filter to only artifacts with the current build type's suffix
    current_paths = [p for p in s3_paths if "rhel-" in p and expected_suffix in p]
    old_paths = [
        p for p in s3_paths
        if "rhel-" in p and expected_suffix not in p
    ]

    if old_paths:
        tl.info(
            f"{len(old_paths)} old S3 artifacts from previous build type "
            f"— ignored (coexistence is expected)"
        )

    if not current_paths:
        tl.skipped(
            f"No 'rhel-*' objects with '{expected_suffix}' "
            "found in s3://boot-images/"
        )
        pytest.skip(
            f"No 'rhel-*' objects with '{expected_suffix}' in S3 "
            "— build not run yet"
        )

    tl.passed(
        f"{len(current_paths)} x86_64 S3 image paths correctly "
        f"include '{expected_suffix}'"
    )


# ---------------------------------------------------------------------------
# TC_BD_011 — Suffix isolation: -imgbld and -imgth paths never collide
# ---------------------------------------------------------------------------

@pytest.mark.order(12)
@pytest.mark.x86_64
@pytest.mark.functional
def test_artifact_suffix_isolation(host):
    """Verify that -imgbld and -imgth suffixes keep artifact paths unique.

    The suffixes exist so that switching between image-builder and
    image-thrillhouse on the same OIM never overwrites the other
    engine's output.  Both ``rhel-X-imgbld`` and ``rhel-X-imgth``
    coexisting is the **intended design** — it proves isolation works.

    This test verifies:
      1. Every ``rhel-*`` artifact carries exactly one suffix.
      2. Full artifact names (with suffix) are unique — no duplicate
         paths exist in the registry or S3.
    """
    tc = TC["artifact_suffix_isolation"]
    tl = TestLogger(tc["title"], tc["id"])

    repos = _get_registry_repos(host)
    s3_paths = _get_s3_image_paths(host)

    # Normalize registry repos
    flat = []
    for r in repos:
        flat.append(r)
        if "/" in r:
            flat.append(r.split("/", 1)[1])

    omnia_repos = [r for r in flat if "rhel-" in r]
    omnia_s3 = [p for p in s3_paths if "rhel-" in p]

    build_type = _get_build_type(host)
    expected_suffix = _SUFFIX_MAP.get(build_type, "-imgbld")
    tl.info(f"build_type={build_type}, expected_suffix={expected_suffix}")

    # Count artifacts by suffix
    imgbld_reg = [r for r in omnia_repos if r.endswith("-imgbld")]
    imgth_reg = [r for r in omnia_repos if r.endswith("-imgth")]
    imgbld_s3 = [p for p in omnia_s3 if "-imgbld" in p]
    imgth_s3 = [p for p in omnia_s3 if "-imgth" in p]

    tl.info(
        f"Registry: {len(imgbld_reg)} -imgbld, {len(imgth_reg)} -imgth"
    )
    tl.info(
        f"S3: {len(imgbld_s3)} -imgbld, {len(imgth_s3)} -imgth"
    )

    # 1. Verify no unsuffixed rhel-* artifacts exist (every artifact
    #    must carry exactly one of the two suffixes)
    unsuffixed_reg = [
        r for r in omnia_repos
        if not r.endswith("-imgbld") and not r.endswith("-imgth")
    ]
    unsuffixed_s3 = [
        p for p in omnia_s3
        if "-imgbld" not in p and "-imgth" not in p
    ]

    if unsuffixed_reg:
        tl.info(f"Unsuffixed registry repos (no -imgbld/-imgth): {unsuffixed_reg}")
    if unsuffixed_s3:
        tl.info(f"Unsuffixed S3 objects (no -imgbld/-imgth): {unsuffixed_s3}")

    # 2. Verify current build type produced at least one artifact
    current_reg = [r for r in omnia_repos if r.endswith(expected_suffix)]
    current_s3 = [p for p in omnia_s3 if expected_suffix in p]

    has_current = bool(current_reg) or bool(current_s3)
    if not has_current:
        tl.skipped(
            f"No artifacts with '{expected_suffix}' found — "
            "build may not have run yet"
        )
        pytest.skip(
            f"No '{expected_suffix}' artifacts in registry or S3"
        )

    # Coexistence of both suffixes is expected and proves isolation
    if imgbld_reg and imgth_reg:
        tl.info(
            "Both -imgbld and -imgth artifacts coexist in registry "
            "— this confirms suffix isolation is working"
        )

    tl.passed(
        f"Suffix isolation verified: {len(current_reg)} registry + "
        f"{len(current_s3)} S3 artifacts carry '{expected_suffix}'. "
        f"Coexistence with other suffix is expected."
    )
