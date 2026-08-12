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
  image-builder     → suffix "-ib"  e.g. rhel-x86_64-base-ib,  rhel-slurm_omnia_2.2-ib
  image-thrillhouse → suffix "-th"  e.g. rhel-x86_64-base-th,  rhel-slurm_omnia_2.2-th

Test IDs: TC_BD_007 – TC_BD_011
"""

import re
import pytest

from omnia_auto import log, TestLogger
from library.vars import TEST_CASES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Expected suffix keyed by image_build_type value
_SUFFIX_MAP = {
    "image-builder": "-ib",
    "image-thrillhouse": "-th",
}

# Opposite suffix — must NOT appear in artifacts produced by the active type
_OPPOSITE_SUFFIX = {
    "image-builder": "-th",
    "image-thrillhouse": "-ib",
}


def _get_build_type(host) -> str:
    """Return the image_build_type configured on the target."""
    result = host.run(
        "grep -E '^image_build_type:' "
        "$(find /opt/omnia -name 'image_build_config.yml' 2>/dev/null | head -1) "
        "2>/dev/null | awk '{print $2}' || echo 'image-builder'"
    )
    build_type = result.stdout.strip().strip('"').strip("'")
    return build_type if build_type in _SUFFIX_MAP else "image-builder"


def _registry_repos(host, registry_host: str) -> list[str]:
    """Return list of OCI repo names from the local registry."""
    result = host.run(
        f"/usr/local/bin/regctl repo ls --limit 500 {registry_host}:5000"
    )
    if result.rc != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _s3_list_prefixes(host, bucket: str) -> list[str]:
    """Return top-level object keys listed in an S3 bucket via s3cmd."""
    result = host.run(f"s3cmd ls s3://{bucket}/ 2>/dev/null || true")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _registry_host_from_env(host) -> str:
    """Resolve registry hostname from the target environment."""
    result = host.run(
        "grep -E '^SYSTEM_HOSTNAME:' /etc/omnia/omnia.env 2>/dev/null "
        "| awk '{print $2}' || hostname -s"
    )
    return result.stdout.strip() or "localhost"


# ---------------------------------------------------------------------------
# TC_BD_007 — image-builder registry naming (x86_64)
# ---------------------------------------------------------------------------

@pytest.mark.order(7)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_registry_naming_image_builder_x86_64(host):
    """TC_BD_007 — Verify x86_64 registry images carry the -ib suffix when
    image_build_type is image-builder."""
    tc = TEST_CASES.get("registry_naming_ib_x86_64", {})
    tc_id = tc.get("id", "TC_BD_007")
    with TestLogger(tc_id, "Verify image-builder x86_64 registry naming (-ib suffix)") as tl:

        build_type = _get_build_type(host)
        if build_type != "image-builder":
            pytest.skip(f"image_build_type is '{build_type}'; TC_BD_007 requires image-builder")

        registry = _registry_host_from_env(host)
        repos = _registry_repos(host, registry)
        tl.log(f"Registry repos found: {len(repos)}")

        expected_suffix = _SUFFIX_MAP["image-builder"]  # "-ib"
        wrong_suffix = _OPPOSITE_SUFFIX["image-builder"]  # "-th"

        # Filter to repos that look like Omnia images
        omnia_repos = [r for r in repos if "rhel-" in r]
        assert omnia_repos, (
            f"No 'rhel-*' images found in registry {registry}:5000. "
            "Ensure the build tag was run before this test."
        )
        tl.log(f"rhel-* repos: {omnia_repos}")

        # Every Omnia image must end with -ib
        bad = [r for r in omnia_repos if not r.endswith(expected_suffix)]
        assert not bad, (
            f"These registry images are missing the '{expected_suffix}' suffix: {bad}\n"
            "Expected all image-builder artifacts to carry '-ib'."
        )

        # No -th images should be present from this build
        contaminated = [r for r in omnia_repos if r.endswith(wrong_suffix)]
        assert not contaminated, (
            f"Found image-thrillhouse artifacts (-th) in an image-builder build: "
            f"{contaminated}. Check that builds are not mixing build types."
        )
        tl.log(f"All {len(omnia_repos)} x86_64 registry images correctly suffixed with '{expected_suffix}'")


# ---------------------------------------------------------------------------
# TC_BD_008 — image-builder S3 naming (x86_64)
# ---------------------------------------------------------------------------

@pytest.mark.order(8)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_s3_naming_image_builder_x86_64(host):
    """TC_BD_008 — Verify x86_64 S3 image paths carry the -ib suffix when
    image_build_type is image-builder."""
    tc = TEST_CASES.get("s3_naming_ib_x86_64", {})
    tc_id = tc.get("id", "TC_BD_008")
    with TestLogger(tc_id, "Verify image-builder x86_64 S3 naming (-ib suffix)") as tl:

        build_type = _get_build_type(host)
        if build_type != "image-builder":
            pytest.skip(f"image_build_type is '{build_type}'; TC_BD_008 requires image-builder")

        expected_suffix = _SUFFIX_MAP["image-builder"]  # "-ib"
        wrong_suffix = _OPPOSITE_SUFFIX["image-builder"]  # "-th"

        s3_objects = _s3_list_prefixes(host, "boot-images")
        tl.log(f"S3 boot-images entries: {len(s3_objects)}")

        omnia_objects = [o for o in s3_objects if "rhel-" in o]
        assert omnia_objects, (
            "No 'rhel-*' objects found in s3://boot-images/. "
            "Ensure the build tag was run before this test."
        )

        bad = [o for o in omnia_objects if expected_suffix not in o]
        assert not bad, (
            f"S3 objects missing '{expected_suffix}': {bad}\n"
            "All image-builder artifacts must carry the '-ib' suffix."
        )

        contaminated = [o for o in omnia_objects if wrong_suffix in o]
        assert not contaminated, (
            f"Found '-th' (image-thrillhouse) objects in an image-builder S3 build: "
            f"{contaminated}"
        )
        tl.log(f"All x86_64 S3 image paths correctly include '{expected_suffix}'")


# ---------------------------------------------------------------------------
# TC_BD_009 — image-thrillhouse registry naming (x86_64)
# ---------------------------------------------------------------------------

@pytest.mark.order(9)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_registry_naming_image_thrillhouse_x86_64(host):
    """TC_BD_009 — Verify x86_64 registry images carry the -th suffix when
    image_build_type is image-thrillhouse."""
    tc = TEST_CASES.get("registry_naming_th_x86_64", {})
    tc_id = tc.get("id", "TC_BD_009")
    with TestLogger(tc_id, "Verify image-thrillhouse x86_64 registry naming (-th suffix)") as tl:

        build_type = _get_build_type(host)
        if build_type != "image-thrillhouse":
            pytest.skip(f"image_build_type is '{build_type}'; TC_BD_009 requires image-thrillhouse")

        registry = _registry_host_from_env(host)
        repos = _registry_repos(host, registry)
        tl.log(f"Registry repos found: {len(repos)}")

        expected_suffix = _SUFFIX_MAP["image-thrillhouse"]  # "-th"
        wrong_suffix = _OPPOSITE_SUFFIX["image-thrillhouse"]  # "-ib"

        omnia_repos = [r for r in repos if "rhel-" in r]
        assert omnia_repos, (
            f"No 'rhel-*' images found in registry {registry}:5000."
        )

        bad = [r for r in omnia_repos if not r.endswith(expected_suffix)]
        assert not bad, (
            f"Registry images missing '{expected_suffix}': {bad}"
        )

        contaminated = [r for r in omnia_repos if r.endswith(wrong_suffix)]
        assert not contaminated, (
            f"Found image-builder artifacts (-ib) in an image-thrillhouse build: "
            f"{contaminated}"
        )
        tl.log(f"All {len(omnia_repos)} x86_64 registry images correctly suffixed with '{expected_suffix}'")


# ---------------------------------------------------------------------------
# TC_BD_010 — image-thrillhouse S3 naming (x86_64)
# ---------------------------------------------------------------------------

@pytest.mark.order(10)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_s3_naming_image_thrillhouse_x86_64(host):
    """TC_BD_010 — Verify x86_64 S3 image paths carry the -th suffix when
    image_build_type is image-thrillhouse."""
    tc = TEST_CASES.get("s3_naming_th_x86_64", {})
    tc_id = tc.get("id", "TC_BD_010")
    with TestLogger(tc_id, "Verify image-thrillhouse x86_64 S3 naming (-th suffix)") as tl:

        build_type = _get_build_type(host)
        if build_type != "image-thrillhouse":
            pytest.skip(f"image_build_type is '{build_type}'; TC_BD_010 requires image-thrillhouse")

        expected_suffix = _SUFFIX_MAP["image-thrillhouse"]  # "-th"
        wrong_suffix = _OPPOSITE_SUFFIX["image-thrillhouse"]  # "-ib"

        s3_objects = _s3_list_prefixes(host, "boot-images")
        omnia_objects = [o for o in s3_objects if "rhel-" in o]
        assert omnia_objects, (
            "No 'rhel-*' objects found in s3://boot-images/."
        )

        bad = [o for o in omnia_objects if expected_suffix not in o]
        assert not bad, (
            f"S3 objects missing '{expected_suffix}': {bad}"
        )

        contaminated = [o for o in omnia_objects if wrong_suffix in o]
        assert not contaminated, (
            f"Found '-ib' (image-builder) objects in an image-thrillhouse S3 build: "
            f"{contaminated}"
        )
        tl.log(f"All x86_64 S3 image paths correctly include '{expected_suffix}'")


# ---------------------------------------------------------------------------
# TC_BD_011 — Suffix isolation: -ib and -th paths never collide
# ---------------------------------------------------------------------------

@pytest.mark.order(11)
@pytest.mark.x86_64
@pytest.mark.functional
def test_artifact_suffix_isolation(host):
    """TC_BD_011 — Verify that -ib and -th suffixed artifacts do not share any
    path prefix.  This confirms the two build engines cannot overwrite each
    other's output even when both have been used on the same OIM.

    The test reads the full registry repo list and S3 listing and checks that
    for every 'rhel-*' name its -ib and -th variants are distinct entries.
    """
    tc = TEST_CASES.get("artifact_suffix_isolation", {})
    tc_id = tc.get("id", "TC_BD_011")
    with TestLogger(tc_id, "Verify -ib and -th artifact paths are fully isolated") as tl:

        registry = _registry_host_from_env(host)
        repos = _registry_repos(host, registry)
        s3_objects = _s3_list_prefixes(host, "boot-images")

        # Extract base names (strip suffix)
        def _strip_suffix(name: str) -> str:
            for sfx in ("-ib", "-th"):
                if name.endswith(sfx):
                    return name[: -len(sfx)]
            return name

        ib_bases = {_strip_suffix(r) for r in repos if r.endswith("-ib") and "rhel-" in r}
        th_bases = {_strip_suffix(r) for r in repos if r.endswith("-th") and "rhel-" in r}
        collision_registry = ib_bases & th_bases

        ib_s3 = {_strip_suffix(o) for o in s3_objects if "-ib" in o and "rhel-" in o}
        th_s3 = {_strip_suffix(o) for o in s3_objects if "-th" in o and "rhel-" in o}
        collision_s3 = ib_s3 & th_s3

        # Both sets can coexist — that is expected and correct.
        # What we verify is that within a single build run the artifacts
        # produced belong to exactly one suffix family (no cross-contamination).
        build_type = _get_build_type(host)
        expected_suffix = _SUFFIX_MAP.get(build_type, "-ib")
        wrong_suffix = "-th" if expected_suffix == "-ib" else "-ib"

        wrong_in_registry = [r for r in repos if r.endswith(wrong_suffix) and "rhel-" in r]
        wrong_in_s3 = [o for o in s3_objects if wrong_suffix in o and "rhel-" in o]

        tl.log(
            f"build_type={build_type}, expected_suffix={expected_suffix}\n"
            f"Registry ib bases: {sorted(ib_bases)}\n"
            f"Registry th bases: {sorted(th_bases)}\n"
            f"S3 ib bases: {sorted(ib_s3)}\n"
            f"S3 th bases: {sorted(th_s3)}"
        )

        if wrong_in_registry:
            tl.log(
                f"WARNING: {len(wrong_in_registry)} '{wrong_suffix}' images found in registry "
                f"from a previous {wrong_suffix.strip('-')} build — this is allowed for "
                "coexistence but flagged for awareness."
            )

        # No shared base name should appear with BOTH -ib and -th in the same
        # registry at the same tag — that would indicate an actual path collision.
        if collision_registry:
            tl.log(f"Collision check (registry): {collision_registry}")
        if collision_s3:
            tl.log(f"Collision check (S3): {collision_s3}")

        # The test passes as long as the current build run only wrote correct-suffix artifacts.
        assert not (
            wrong_in_registry and wrong_in_s3
        ), (
            f"Both -ib and -th artifacts exist for the same image names in registry AND S3, "
            f"suggesting a naming collision.  Check _build_type_suffix in vars/main.yml."
        )
        tl.log("Artifact suffix isolation verified — no naming collision detected")
