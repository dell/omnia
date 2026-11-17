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

"""FVT coverage for Image Thrillhouse artifact naming."""

import json
from typing import List

import pytest

from library.functions import TestLogger, check_build_status_file
from library.vars import TEST_CASES as TC
from library.vars.common_vars import CMDS, REGISTRY_PORT, S3_BOOT_IMAGES_BUCKET


def _get_registry_repos(host) -> List[str]:
    hostname_cmd = host.run(CMDS["hostname_short"])
    fqdn = hostname_cmd.stdout.strip() if hostname_cmd.rc == 0 else "localhost"
    registry_url = f"{fqdn}:{REGISTRY_PORT}"
    for scheme in ("http", "https"):
        result = host.run(
            CMDS["curl_registry_catalog_scheme"].format(
                scheme=scheme, port=REGISTRY_PORT,
            )
        )
        if result.rc == 0 and "repositories" in result.stdout:
            try:
                repos = json.loads(result.stdout).get("repositories", [])
                if repos:
                    return repos
            except (json.JSONDecodeError, ValueError):
                pass
    result = host.run(CMDS["regctl_repo_ls"].format(registry=registry_url))
    if result.rc == 0:
        return [repo.strip() for repo in result.stdout.splitlines() if repo.strip()]
    return []


def _get_s3_image_paths(host) -> List[str]:
    result = host.run(CMDS["s3cmd_ls_bucket"].format(bucket=S3_BOOT_IMAGES_BUCKET))
    if result.rc != 0:
        return []
    return [
        parts[3]
        for line in result.stdout.splitlines()
        if len(parts := line.split()) >= 4
    ]


@pytest.mark.order(8)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_registry_naming_image_thrillhouse_x86_64(host):
    tc = TC["registry_naming_th_x86_64"]
    tl = TestLogger(tc["title"], tc["id"])
    status = check_build_status_file(host)
    assert status.get("image_build_type") == "image-thrillhouse"
    repos = {
        repo.split("/", 1)[1] if "/" in repo else repo
        for repo in _get_registry_repos(host)
    }
    matching = [
        repo for repo in repos
        if "rhel-" in repo and "x86_64" in repo and repo.endswith("-imgth")
    ]
    if not matching:
        pytest.skip("No x86_64 Image Thrillhouse images found in the registry")
    tl.passed(f"{len(matching)} registry images use the -imgth suffix")


@pytest.mark.order(9)
@pytest.mark.x86_64
@pytest.mark.sanity
def test_s3_naming_image_thrillhouse_x86_64(host):
    tc = TC["s3_naming_th_x86_64"]
    tl = TestLogger(tc["title"], tc["id"])
    status = check_build_status_file(host)
    assert status.get("image_build_type") == "image-thrillhouse"
    matching = [
        path for path in _get_s3_image_paths(host)
        if "rhel-" in path and "x86_64" in path and "-imgth/" in path
    ]
    if not matching:
        pytest.skip("No x86_64 Image Thrillhouse images found in S3")
    tl.passed(f"{len(matching)} S3 image paths use the -imgth suffix")
