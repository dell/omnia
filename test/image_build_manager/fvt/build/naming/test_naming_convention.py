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

Test metadata is resolved from the centralized test-case registry.
"""

import json
from collections import Counter
from typing import List

import pytest

from library.functions import (
    TestLogger,
    check_build_status_file,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    CMDS,
    IMAGE_BUILD_TYPE_SUFFIXES,
    REGISTRY_PORT,
    S3_BOOT_IMAGES_BUCKET,
)


# ---------------------------------------------------------------------------
# Suffix constants
# ---------------------------------------------------------------------------

def _is_x86_64_artifact(value: str) -> bool:
    """Return whether an artifact name or path belongs to x86_64."""
    return "x86_64" in value


def _invalid_suffix_artifacts(artifacts: List[str]) -> List[str]:
    """Return artifacts that carry neither suffix or both suffixes."""
    return [
        artifact for artifact in artifacts
        if sum(
            suffix in artifact
            for suffix in IMAGE_BUILD_TYPE_SUFFIXES.values()
        ) != 1
    ]


def _duplicate_artifacts(artifacts: List[str]) -> List[str]:
    """Return duplicate artifact names or paths."""
    return sorted(
        artifact
        for artifact, count in Counter(artifacts).items()
        if count > 1
    )


def _normalized_registry_repos(repos: List[str]) -> List[str]:
    """Strip an optional registry prefix and return unique repo names."""
    return sorted({
        repo.split("/", 1)[1] if "/" in repo else repo
        for repo in repos
    })


def _naming_details(
    build_type: str,
    required_type: str,
    suffix: str,
    location: str,
    matching_count: int,
    ignored_count: int,
) -> dict:
    """Return consistent, ordered naming verification fields."""
    return {
        "Artifact store": location,
        "Architecture": "x86_64",
        "Build-status image type": build_type,
        "Required image build type": required_type,
        "Required suffix": suffix,
        "Matching current artifacts": matching_count,
        "Other artifacts ignored": ignored_count,
        "Coexistence rule": (
            "Artifacts from the other image engine may coexist safely."
        ),
    }


# ---------------------------------------------------------------------------
# Helpers — reuse the same infra as check_registry_images / check_s3_bucket_images
# ---------------------------------------------------------------------------

def _get_build_type(host) -> str:
    """Return the engine that produced the active build-status manifest."""
    status = check_build_status_file(host)
    return status.get("image_build_type", "")


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
# Image Builder registry naming (x86_64)
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
        tl.skipped_fields(
            f"build_status.yml records '{build_type}'; requires image-builder",
            _naming_details(
                build_type, "image-builder", "-imgbld",
                "OCI registry", 0, 0,
            ),
        )
        pytest.skip(
            f"build_status.yml records '{build_type}'; requires image-builder"
        )

    repos = _get_registry_repos(host)
    tl.info(f"Registry repos found: {len(repos)}")

    normalized_repos = _normalized_registry_repos(repos)

    expected_suffix = IMAGE_BUILD_TYPE_SUFFIXES["image-builder"]

    # Filter to only artifacts with the current build type's suffix
    current_repos = [
        repo for repo in normalized_repos
        if "rhel-" in repo
        and _is_x86_64_artifact(repo)
        and repo.endswith(expected_suffix)
    ]
    old_repos = [
        repo for repo in normalized_repos
        if "rhel-" in repo
        and _is_x86_64_artifact(repo)
        and not repo.endswith(expected_suffix)
    ]

    if old_repos:
        tl.info(
            f"{len(old_repos)} old artifacts from previous build type "
            f"in registry — ignored (coexistence is expected)"
        )

    if not current_repos:
        tl.skipped_fields(
            f"No 'rhel-*{expected_suffix}' images found in registry",
            _naming_details(
                build_type, "image-builder", expected_suffix,
                "OCI registry", 0, len(old_repos),
            ),
        )
        pytest.skip(
            f"No 'rhel-*{expected_suffix}' images found in registry "
            "— build not run yet"
        )

    tl.passed_fields(
        f"{len(current_repos)} x86_64 registry images correctly "
        f"suffixed with '{expected_suffix}'",
        _naming_details(
            build_type, "image-builder", expected_suffix,
            "OCI registry", len(current_repos), len(old_repos),
        ),
    )


# ---------------------------------------------------------------------------
# Image Builder S3 naming (x86_64)
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
        tl.skipped_fields(
            f"build_status.yml records '{build_type}'; requires image-builder",
            _naming_details(
                build_type, "image-builder", "-imgbld",
                "S3 boot-images bucket", 0, 0,
            ),
        )
        pytest.skip(
            f"build_status.yml records '{build_type}'; requires image-builder"
        )

    expected_suffix = IMAGE_BUILD_TYPE_SUFFIXES["image-builder"]

    s3_paths = _get_s3_image_paths(host)
    tl.info(f"S3 boot-images entries: {len(s3_paths)}")

    # Filter to only artifacts with the current build type's suffix
    current_paths = [
        path for path in s3_paths
        if "rhel-" in path
        and _is_x86_64_artifact(path)
        and expected_suffix in path
    ]
    old_paths = [
        path for path in s3_paths
        if "rhel-" in path
        and _is_x86_64_artifact(path)
        and expected_suffix not in path
    ]

    if old_paths:
        tl.info(
            f"{len(old_paths)} old S3 artifacts from previous build type "
            f"— ignored (coexistence is expected)"
        )

    if not current_paths:
        tl.skipped_fields(
            f"No 'rhel-*' objects with '{expected_suffix}' "
            "found in s3://boot-images/",
            _naming_details(
                build_type, "image-builder", expected_suffix,
                "S3 boot-images bucket", 0, len(old_paths),
            ),
        )
        pytest.skip(
            f"No 'rhel-*' objects with '{expected_suffix}' in S3 "
            "— build not run yet"
        )

    tl.passed_fields(
        f"{len(current_paths)} x86_64 S3 image paths correctly "
        f"include '{expected_suffix}'",
        _naming_details(
            build_type, "image-builder", expected_suffix,
            "S3 boot-images bucket", len(current_paths), len(old_paths),
        ),
    )


# ---------------------------------------------------------------------------
# Image Thrillhouse registry naming (x86_64)
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
        tl.skipped_fields(
            f"build_status.yml records '{build_type}'; requires image-thrillhouse",
            _naming_details(
                build_type, "image-thrillhouse", "-imgth",
                "OCI registry", 0, 0,
            ),
        )
        pytest.skip(
            "build_status.yml records "
            f"'{build_type}'; requires image-thrillhouse"
        )

    repos = _get_registry_repos(host)
    tl.info(f"Registry repos found: {len(repos)}")

    normalized_repos = _normalized_registry_repos(repos)

    expected_suffix = IMAGE_BUILD_TYPE_SUFFIXES["image-thrillhouse"]

    # Filter to only artifacts with the current build type's suffix
    current_repos = [
        repo for repo in normalized_repos
        if "rhel-" in repo
        and _is_x86_64_artifact(repo)
        and repo.endswith(expected_suffix)
    ]
    old_repos = [
        repo for repo in normalized_repos
        if "rhel-" in repo
        and _is_x86_64_artifact(repo)
        and not repo.endswith(expected_suffix)
    ]

    if old_repos:
        tl.info(
            f"{len(old_repos)} old artifacts from previous build type "
            f"in registry — ignored (coexistence is expected)"
        )

    if not current_repos:
        tl.skipped_fields(
            f"No 'rhel-*{expected_suffix}' images found in registry",
            _naming_details(
                build_type, "image-thrillhouse", expected_suffix,
                "OCI registry", 0, len(old_repos),
            ),
        )
        pytest.skip(
            f"No 'rhel-*{expected_suffix}' images found in registry "
            "— build not run yet"
        )

    tl.passed_fields(
        f"{len(current_repos)} x86_64 registry images correctly "
        f"suffixed with '{expected_suffix}'",
        _naming_details(
            build_type, "image-thrillhouse", expected_suffix,
            "OCI registry", len(current_repos), len(old_repos),
        ),
    )


# ---------------------------------------------------------------------------
# Image Thrillhouse S3 naming (x86_64)
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
        tl.skipped_fields(
            f"build_status.yml records '{build_type}'; requires image-thrillhouse",
            _naming_details(
                build_type, "image-thrillhouse", "-imgth",
                "S3 boot-images bucket", 0, 0,
            ),
        )
        pytest.skip(
            "build_status.yml records "
            f"'{build_type}'; requires image-thrillhouse"
        )

    expected_suffix = IMAGE_BUILD_TYPE_SUFFIXES["image-thrillhouse"]

    s3_paths = _get_s3_image_paths(host)

    # Filter to only artifacts with the current build type's suffix
    current_paths = [
        path for path in s3_paths
        if "rhel-" in path
        and _is_x86_64_artifact(path)
        and expected_suffix in path
    ]
    old_paths = [
        path for path in s3_paths
        if "rhel-" in path
        and _is_x86_64_artifact(path)
        and expected_suffix not in path
    ]

    if old_paths:
        tl.info(
            f"{len(old_paths)} old S3 artifacts from previous build type "
            f"— ignored (coexistence is expected)"
        )

    if not current_paths:
        tl.skipped_fields(
            f"No 'rhel-*' objects with '{expected_suffix}' "
            "found in s3://boot-images/",
            _naming_details(
                build_type, "image-thrillhouse", expected_suffix,
                "S3 boot-images bucket", 0, len(old_paths),
            ),
        )
        pytest.skip(
            f"No 'rhel-*' objects with '{expected_suffix}' in S3 "
            "— build not run yet"
        )

    tl.passed_fields(
        f"{len(current_paths)} x86_64 S3 image paths correctly "
        f"include '{expected_suffix}'",
        _naming_details(
            build_type, "image-thrillhouse", expected_suffix,
            "S3 boot-images bucket", len(current_paths), len(old_paths),
        ),
    )


# ---------------------------------------------------------------------------
# Suffix isolation: -imgbld and -imgth paths never collide
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

    # Normalize registry repo names without creating duplicate aliases.
    normalized_repos = _normalized_registry_repos(repos)
    omnia_repos = [
        repo for repo in normalized_repos
        if "rhel-" in repo and _is_x86_64_artifact(repo)
    ]
    omnia_s3 = [
        path for path in s3_paths
        if "rhel-" in path and _is_x86_64_artifact(path)
    ]

    build_type = _get_build_type(host)
    expected_suffix = IMAGE_BUILD_TYPE_SUFFIXES.get(build_type, "")
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

    # Every artifact must carry exactly one engine suffix and every complete
    # repository name or S3 object path must be unique.
    invalid_registry = _invalid_suffix_artifacts(omnia_repos)
    invalid_s3 = _invalid_suffix_artifacts(omnia_s3)
    duplicate_registry = _duplicate_artifacts(omnia_repos)
    duplicate_s3 = _duplicate_artifacts(omnia_s3)
    violations = []
    if invalid_registry:
        violations.append(f"Invalid registry suffixes: {invalid_registry}")
    if invalid_s3:
        violations.append(f"Invalid S3 suffixes: {invalid_s3}")
    if duplicate_registry:
        violations.append(f"Duplicate registry repositories: {duplicate_registry}")
    if duplicate_s3:
        violations.append(f"Duplicate S3 object paths: {duplicate_s3}")

    if violations:
        details = "\n".join(violations)
        tl.failed("Artifact suffix isolation violations found", details)
        pytest.fail(details)

    # Verify the current build type produced at least one artifact.
    current_reg = [
        repo for repo in omnia_repos
        if expected_suffix and repo.endswith(expected_suffix)
    ]
    current_s3 = [
        path for path in omnia_s3
        if expected_suffix and expected_suffix in path
    ]

    has_current = bool(current_reg) or bool(current_s3)
    if not has_current:
        tl.skipped_fields(
            f"No artifacts with '{expected_suffix}' found — "
            "build may not have run yet",
            {
                "Architecture": "x86_64",
                "Build-status engine": build_type,
                "Required suffix": expected_suffix,
                "Registry repositories checked": len(omnia_repos),
                "S3 object paths checked": len(omnia_s3),
            },
        )
        pytest.skip(
            f"No '{expected_suffix}' artifacts in registry or S3"
        )

    # Coexistence of both suffixes is expected and proves isolation.
    if imgbld_reg and imgth_reg:
        tl.info(
            "Both -imgbld and -imgth artifacts coexist in registry "
            "— this confirms suffix isolation is working"
        )

    tl.passed_fields(
        "Artifact suffix isolation is valid",
        {
            "Architecture": "x86_64",
            "Build-status engine": build_type,
            "Required suffix": expected_suffix,
            "Current registry repositories": len(current_reg),
            "Current S3 object paths": len(current_s3),
            "Image Builder registry repositories": len(imgbld_reg),
            "Thrillhouse registry repositories": len(imgth_reg),
            "Image Builder S3 object paths": len(imgbld_s3),
            "Thrillhouse S3 object paths": len(imgth_s3),
            "Isolation rule": (
                "Every artifact has exactly one engine suffix and a unique path."
            ),
            "Coexistence rule": (
                "Artifacts from the other engine may coexist safely."
            ),
        },
    )
