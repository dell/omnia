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
Image Build Manager — OCI provenance helpers (TC-FVT-003).

Drives regctl with argument vectors against the local OCI registry. Fixtures are
copies of an existing local image under a disposable repository, and they are
removed by manifest digest afterwards. Production image repositories are read
but never modified.
"""

import json
import os
import secrets
import subprocess
from typing import Dict, List

REGCTL = os.environ.get("OMNIA_REGCTL_BIN", "/usr/local/bin/regctl")
LOCAL_REGISTRY = os.environ.get("OMNIA_LOCAL_REGISTRY", "localhost:5000")
SOURCE_REPO = os.environ.get("OMNIA_PROVENANCE_SOURCE", "oim/rhel-x86_64-base-imgth")
FIXTURE_NAMESPACE = "zz-fvt-provenance"
CREATED_FORMAT = '{{.Created.UTC.Format "2006-01-02T15:04:05Z"}}'
ANNOTATION_KEYS = [
    "org.opencontainers.image.source",
    "org.opencontainers.image.revision",
    "org.opencontainers.image.created",
    "org.opencontainers.image.version",
    "org.opencontainers.image.vendor",
    "io.dell.omnia.functional_group",
    "io.dell.omnia.architecture",
    "io.dell.omnia.build_job_id",
    "io.dell.omnia.published_by",
]


def _regctl(*args: str) -> str:
    result = subprocess.run([REGCTL, *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"regctl {args[0]} failed: {result.stderr.strip()[:200]}")
    return result.stdout.strip()


def new_fixture_repo() -> str:
    """Return a unique disposable repository name."""
    return f"{FIXTURE_NAMESPACE}/{secrets.token_hex(4)}"


def copy_fixture(repo: str, tag: str) -> str:
    """Copy the source image into the disposable repository and return its reference."""
    dest = f"{LOCAL_REGISTRY}/{repo}:{tag}"
    _regctl("image", "copy", f"{LOCAL_REGISTRY}/{SOURCE_REPO}:10.2", dest)
    return dest


def copy_tag(repo: str, src_tag: str, dst_tag: str) -> str:
    """Copy one tag to another in the same repository, as the publish step tags the local image."""
    src = f"{LOCAL_REGISTRY}/{repo}:{src_tag}"
    dest = f"{LOCAL_REGISTRY}/{repo}:{dst_tag}"
    _regctl("image", "copy", src, dest)
    return dest


def config_created(ref: str) -> str:
    """Return the image config created time as RFC 3339 UTC."""
    return _regctl("image", "config", ref, "--format", CREATED_FORMAT)


def digest(ref: str) -> str:
    """Return the manifest digest for a reference."""
    return _regctl("image", "digest", ref)


def manifest_annotations(ref: str) -> Dict[str, str]:
    """Return the manifest annotations for a reference."""
    return json.loads(_regctl("manifest", "get", ref, "--format", "{{json .Annotations}}") or "{}")


def publish_annotations(group: str, job_id: str, created: str) -> Dict[str, str]:
    """Return the nine provenance annotations the publish step sets for one group."""
    return {
        "org.opencontainers.image.source": "fvt-provenance",
        "org.opencontainers.image.revision": "0" * 64,
        "org.opencontainers.image.created": created,
        "org.opencontainers.image.version": "2.3.0.0",
        "org.opencontainers.image.vendor": "Dell Technologies",
        "io.dell.omnia.functional_group": group,
        "io.dell.omnia.architecture": "x86_64",
        "io.dell.omnia.build_job_id": job_id,
        "io.dell.omnia.published_by": "buildstream",
    }


def annotate(ref: str, annotations: Dict[str, str]) -> None:
    """Replace the manifest annotations, as the publish step does with regctl image mod."""
    args: List[str] = ["image", "mod", ref, "--replace"]
    for key, value in annotations.items():
        args += ["--annotation", f"{key}={value}"]
    _regctl(*args)


def tag_digests(repo: str, tags: List[str]) -> Dict[str, str]:
    """Return the digest of every tag in the repository."""
    return {tag: digest(f"{LOCAL_REGISTRY}/{repo}:{tag}") for tag in tags}


def remove_fixture(repo: str, tags: List[str]) -> None:
    """Delete each fixture manifest once, by digest. A digest removes every tag that points to it."""
    digests = set()
    for tag in tags:
        try:
            digests.add(digest(f"{LOCAL_REGISTRY}/{repo}:{tag}"))
        except RuntimeError:
            continue
    for manifest in sorted(digests):
        _regctl("manifest", "delete", f"{LOCAL_REGISTRY}/{repo}@{manifest}")
