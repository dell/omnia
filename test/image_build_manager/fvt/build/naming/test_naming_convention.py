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
from library.vars.common_vars import CMDS, REGISTRY_PORT, S3_BOOT_IMAGES_BUCKET


# ---------------------------------------------------------------------------
# Suffix constants
# ---------------------------------------------------------------------------

_SUFFIX_MAP = {
    "image-builder": "-imgbld",
    "image-thrillhouse": "-imgth",
}

_OPPOSITE_SUFFIX = {
    "image-builder": "-imgth",
    "image-thrillhouse": "-imgbld",
}


# ---------------------------------------------------------------------------
# Helpers — reuse the same infra as check_registry_images / check_s3_bucket_images
# ---------------------------------------------------------------------------

def _get_build_type(host) -> str:
    """Return the image_build_type configured on the target."""
    result = host.run(
        "grep -E '^image_build_type:' "
        "$(find /opt/omnia -name 'image_build_config.yml' 2>/dev/null | head -1) "
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

@pytest.mark.order(7)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_registry_naming_image_builder_x86_64(host):
    """Verify x86_64 registry images carry the -imgbld suffix when
    image_build_type is image-builder."""
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
    wrong_suffix = _OPPOSITE_SUFFIX["image-builder"]

    omnia_repos = [r for r in flat if "rhel-" in r]
    if not omnia_repos:
        tl.skipped("No 'rhel-*' images found in registry")
        pytest.skip("No 'rhel-*' images found in registry — build not run yet")

    tl.info(f"rhel-* repos: {omnia_repos}")

    bad = [r for r in omnia_repos if not r.endswith(expected_suffix)]
    contaminated = [r for r in omnia_repos if r.endswith(wrong_suffix)]

    if not bad and not contaminated:
        tl.passed(
            f"All {len(omnia_repos)} x86_64 registry images correctly "
            f"suffixed with '{expected_suffix}'"
        )
    else:
        tl.failed(
            f"Naming issues: {len(bad)} missing '{expected_suffix}', "
            f"{len(contaminated)} have wrong suffix '{wrong_suffix}'",
            f"Missing suffix: {bad}\nContaminated: {contaminated}",
        )

    assert not bad, (
        f"These registry images are missing the '{expected_suffix}' suffix: {bad}\n"
        f"Expected all image-builder artifacts to carry '{expected_suffix}'."
    )
    assert not contaminated, (
        f"Found image-thrillhouse artifacts ({wrong_suffix}) in an image-builder build: "
        f"{contaminated}. Check that builds are not mixing build types."
    )


# ---------------------------------------------------------------------------
# TC_BD_008 — image-builder S3 naming (x86_64)
# ---------------------------------------------------------------------------

@pytest.mark.order(8)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_s3_naming_image_builder_x86_64(host):
    """Verify x86_64 S3 image paths carry the -imgbld suffix when
    image_build_type is image-builder."""
    tc = TC["s3_naming_ib_x86_64"]
    tl = TestLogger(tc["title"], tc["id"])

    build_type = _get_build_type(host)
    if build_type != "image-builder":
        tl.skipped(f"image_build_type is '{build_type}'; requires image-builder")
        pytest.skip(f"image_build_type is '{build_type}'; TC_BD_008 requires image-builder")

    expected_suffix = _SUFFIX_MAP["image-builder"]
    wrong_suffix = _OPPOSITE_SUFFIX["image-builder"]

    s3_paths = _get_s3_image_paths(host)
    tl.info(f"S3 boot-images entries: {len(s3_paths)}")

    omnia_paths = [p for p in s3_paths if "rhel-" in p]
    if not omnia_paths:
        tl.skipped("No 'rhel-*' objects found in s3://boot-images/")
        pytest.skip("No 'rhel-*' objects in S3 — build not run yet")

    bad = [p for p in omnia_paths if expected_suffix not in p]
    contaminated = [p for p in omnia_paths if wrong_suffix in p]

    if not bad and not contaminated:
        tl.passed(f"All x86_64 S3 image paths correctly include '{expected_suffix}'")
    else:
        tl.failed(
            f"S3 naming issues: {len(bad)} missing '{expected_suffix}', "
            f"{len(contaminated)} have wrong suffix '{wrong_suffix}'",
            f"Missing suffix: {bad}\nContaminated: {contaminated}",
        )

    assert not bad, (
        f"S3 objects missing '{expected_suffix}': {bad}\n"
        f"All image-builder artifacts must carry the '{expected_suffix}' suffix."
    )
    assert not contaminated, (
        f"Found '{wrong_suffix}' (image-thrillhouse) objects in an image-builder S3 build: "
        f"{contaminated}"
    )


# ---------------------------------------------------------------------------
# TC_BD_009 — image-thrillhouse registry naming (x86_64)
# ---------------------------------------------------------------------------

@pytest.mark.order(9)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_registry_naming_image_thrillhouse_x86_64(host):
    """Verify x86_64 registry images carry the -imgth suffix when
    image_build_type is image-thrillhouse."""
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
    wrong_suffix = _OPPOSITE_SUFFIX["image-thrillhouse"]

    omnia_repos = [r for r in flat if "rhel-" in r]
    if not omnia_repos:
        tl.skipped("No 'rhel-*' images found in registry")
        pytest.skip("No 'rhel-*' images found in registry — build not run yet")

    bad = [r for r in omnia_repos if not r.endswith(expected_suffix)]
    contaminated = [r for r in omnia_repos if r.endswith(wrong_suffix)]

    if not bad and not contaminated:
        tl.passed(
            f"All {len(omnia_repos)} x86_64 registry images correctly "
            f"suffixed with '{expected_suffix}'"
        )
    else:
        tl.failed(
            f"Naming issues: {len(bad)} missing '{expected_suffix}', "
            f"{len(contaminated)} have wrong suffix '{wrong_suffix}'",
            f"Missing suffix: {bad}\nContaminated: {contaminated}",
        )

    assert not bad, (
        f"Registry images missing '{expected_suffix}': {bad}"
    )
    assert not contaminated, (
        f"Found image-builder artifacts ({wrong_suffix}) in an image-thrillhouse build: "
        f"{contaminated}"
    )


# ---------------------------------------------------------------------------
# TC_BD_010 — image-thrillhouse S3 naming (x86_64)
# ---------------------------------------------------------------------------

@pytest.mark.order(10)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_s3_naming_image_thrillhouse_x86_64(host):
    """Verify x86_64 S3 image paths carry the -imgth suffix when
    image_build_type is image-thrillhouse."""
    tc = TC["s3_naming_th_x86_64"]
    tl = TestLogger(tc["title"], tc["id"])

    build_type = _get_build_type(host)
    if build_type != "image-thrillhouse":
        tl.skipped(f"image_build_type is '{build_type}'; requires image-thrillhouse")
        pytest.skip(f"image_build_type is '{build_type}'; TC_BD_010 requires image-thrillhouse")

    expected_suffix = _SUFFIX_MAP["image-thrillhouse"]
    wrong_suffix = _OPPOSITE_SUFFIX["image-thrillhouse"]

    s3_paths = _get_s3_image_paths(host)
    omnia_paths = [p for p in s3_paths if "rhel-" in p]
    if not omnia_paths:
        tl.skipped("No 'rhel-*' objects found in s3://boot-images/")
        pytest.skip("No 'rhel-*' objects in S3 — build not run yet")

    bad = [p for p in omnia_paths if expected_suffix not in p]
    contaminated = [p for p in omnia_paths if wrong_suffix in p]

    if not bad and not contaminated:
        tl.passed(f"All x86_64 S3 image paths correctly include '{expected_suffix}'")
    else:
        tl.failed(
            f"S3 naming issues: {len(bad)} missing '{expected_suffix}', "
            f"{len(contaminated)} have wrong suffix '{wrong_suffix}'",
            f"Missing suffix: {bad}\nContaminated: {contaminated}",
        )

    assert not bad, (
        f"S3 objects missing '{expected_suffix}': {bad}"
    )
    assert not contaminated, (
        f"Found '{wrong_suffix}' (image-builder) objects in an image-thrillhouse S3 build: "
        f"{contaminated}"
    )


# ---------------------------------------------------------------------------
# TC_BD_011 — Suffix isolation: -imgbld and -imgth paths never collide
# ---------------------------------------------------------------------------

@pytest.mark.order(11)
@pytest.mark.x86_64
@pytest.mark.functional
def test_artifact_suffix_isolation(host):
    """Verify that -imgbld and -imgth suffixed artifacts do not share any
    path prefix.  This confirms the two build engines cannot overwrite each
    other's output even when both have been used on the same OIM."""
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

    def _strip_suffix(name: str) -> str:
        for sfx in ("-imgbld", "-imgth"):
            if name.endswith(sfx):
                return name[: -len(sfx)]
        return name

    ib_bases = {_strip_suffix(r) for r in flat if r.endswith("-imgbld") and "rhel-" in r}
    th_bases = {_strip_suffix(r) for r in flat if r.endswith("-imgth") and "rhel-" in r}

    ib_s3 = {_strip_suffix(p) for p in s3_paths if "-imgbld" in p and "rhel-" in p}
    th_s3 = {_strip_suffix(p) for p in s3_paths if "-imgth" in p and "rhel-" in p}

    build_type = _get_build_type(host)
    expected_suffix = _SUFFIX_MAP.get(build_type, "-imgbld")
    wrong_suffix = "-imgth" if expected_suffix == "-imgbld" else "-imgbld"

    wrong_in_registry = [r for r in flat if r.endswith(wrong_suffix) and "rhel-" in r]
    wrong_in_s3 = [p for p in s3_paths if wrong_suffix in p and "rhel-" in p]

    tl.info(f"build_type={build_type}, expected_suffix={expected_suffix}")
    tl.info(f"Registry imgbld bases: {sorted(ib_bases)}, imgth bases: {sorted(th_bases)}")
    tl.info(f"S3 imgbld bases: {sorted(ib_s3)}, imgth bases: {sorted(th_s3)}")

    if wrong_in_registry:
        tl.info(
            f"{len(wrong_in_registry)} '{wrong_suffix}' images in registry "
            f"from a previous build — allowed for coexistence"
        )

    has_collision = wrong_in_registry and wrong_in_s3

    if not has_collision:
        tl.passed("Artifact suffix isolation verified — no naming collision detected")
    else:
        tl.failed(
            f"Both {_SUFFIX_MAP['image-builder']} and {_SUFFIX_MAP['image-thrillhouse']} "
            "artifacts exist in registry AND S3",
            f"Registry wrong: {wrong_in_registry}\nS3 wrong: {wrong_in_s3}",
        )

    assert not has_collision, (
        f"Both -imgbld and -imgth artifacts exist for the same image names in "
        f"registry AND S3, suggesting a naming collision. "
        f"Check _build_type_suffix in vars/main.yml."
    )
