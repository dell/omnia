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
Image Build Build — OCI provenance annotations and tags (TC-FVT-003).

Runs against disposable fixtures in the local registry, copied from an existing
image and removed by manifest digest afterwards. The production repositories are
read, never modified:
  V030: the nine provenance annotations are present, and created equals the image
        config created time (AC-005)
  V031: repeated publication of the same image keeps the local digest and the
        created value (AC-014)
  V032: the OS-version, catalog-digest, and release tags resolve to one digest, and
        a tag that resolves elsewhere is detected (AC-007)
"""

import pytest

from library.functions import TestLogger
from library.functions.oci_provenance_func import (
    ANNOTATION_KEYS,
    LOCAL_REGISTRY,
    annotate,
    config_created,
    copy_fixture,
    copy_tag,
    digest,
    manifest_annotations,
    new_fixture_repo,
    publish_annotations,
    remove_fixture,
    tag_digests,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

JOB_ID = "fvt-provenance-job"
GROUP = "login_node_rhel_10_2_x86_64"
TAGS = ["10.2", "2.3.0.0", "a1b2c3d4"]


def _fixture(tags):
    repo = new_fixture_repo()
    copy_fixture(repo, tags[0])
    for tag in tags[1:]:
        copy_tag(repo, tags[0], tag)
    return repo


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(14)
def test_provenance_annotations_present_and_created_from_config():
    """Every image carries the nine provenance annotations, and created is the config time."""
    tc = TC["oci_provenance_annotations"]
    tl = TestLogger(tc["title"], tc["id"])
    repo = _fixture(["10.2"])
    ref = f"{LOCAL_REGISTRY}/{repo}:10.2"
    try:
        created = config_created(ref)
        annotate(ref, publish_annotations(GROUP, JOB_ID, created))
        found = manifest_annotations(ref)
        created_seen = found.get("org.opencontainers.image.created")
        missing = [key for key in ANNOTATION_KEYS if key not in found]
        ok = not missing and found["org.opencontainers.image.created"] == created
        if ok:
            tl.passed(LOG["oci_provenance_ok"].format(detail=f"9 annotations, created={created}"))
        else:
            tl.failed(LOG["oci_provenance_failed"].format(
                expected="9 annotations with created equal to the config time",
                observed=f"missing={missing} created={created_seen}"))
        assert ok, ASSERT["oci_provenance_assert"].format(
            detail=str(missing) or "created mismatch")
    finally:
        remove_fixture(repo, ["10.2"])


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(15)
def test_repeated_publication_keeps_digest_and_created():
    """Publishing the same image again with the same job ID keeps the digest and created."""
    tc = TC["oci_provenance_repeat"]
    tl = TestLogger(tc["title"], tc["id"])
    repo = _fixture(["10.2"])
    ref = f"{LOCAL_REGISTRY}/{repo}:10.2"
    try:
        created = config_created(ref)
        annotate(ref, publish_annotations(GROUP, JOB_ID, created))
        first = digest(ref)
        annotate(ref, publish_annotations(GROUP, JOB_ID, config_created(ref)))
        second = digest(ref)
        created_again = manifest_annotations(ref)["org.opencontainers.image.created"]
        ok = first == second and created_again == created
        if ok:
            tl.passed(LOG["oci_provenance_ok"].format(
                detail=f"digest {first[:19]} and created unchanged"))
        else:
            tl.failed(LOG["oci_provenance_failed"].format(
                expected="same digest and created on republication",
                observed=(f"digest_same={first == second} "
                          f"created_same={created_again == created}")))
        assert ok, ASSERT["oci_provenance_assert"].format(detail="republication changed the image")
    finally:
        remove_fixture(repo, ["10.2"])


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(16)
def test_tags_resolve_to_one_digest_and_a_mismatch_is_detected():
    """OS-version, catalog-digest, and release tags share one digest; a different one is caught."""
    tc = TC["oci_provenance_tags"]
    tl = TestLogger(tc["title"], tc["id"])
    repo = _fixture(TAGS)
    try:
        shared = len(set(tag_digests(repo, TAGS).values())) == 1
        copy_fixture(repo, "other")
        other_ref = f"{LOCAL_REGISTRY}/{repo}:other"
        annotate(other_ref, publish_annotations(GROUP, "other-job", config_created(other_ref)))
        detected = len(set(tag_digests(repo, TAGS + ["other"]).values())) > 1
        ok = shared and detected
        if ok:
            tl.passed(LOG["oci_provenance_ok"].format(
                detail="three tags share one digest; a different one is detected"))
        else:
            tl.failed(LOG["oci_provenance_failed"].format(
                expected="tags share one digest, and a different digest is detected",
                observed=f"shared={shared} detected={detected}"))
        assert ok, ASSERT["oci_provenance_assert"].format(detail="tag digest agreement")
    finally:
        remove_fixture(repo, TAGS + ["other"])
