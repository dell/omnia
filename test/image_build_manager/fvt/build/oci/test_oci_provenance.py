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
  V033: after a push to the external registry, every tag resolves to the local digest,
        created is preserved, and a repeated push keeps the digest (AC-007, AC-014)

V033 needs an external registry. It skips unless OMNIA_OCI_HARBOR_HOST, OMNIA_OCI_HARBOR_PORT,
OMNIA_OCI_HARBOR_NAMESPACE, and OMNIA_OCI_HARBOR_CA_FILE are set, and the account is set
through OMNIA_OCI_TEST_USERNAME and OMNIA_OCI_TEST_PASSWORD. It writes only to a disposable
repository in that namespace and deletes it afterwards.
"""

import os

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
    remote_annotations,
    remote_copy,
    remote_delete,
    remote_digest,
    remote_env,
    remove_fixture,
    tag_digests,
    _remote_config,
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


HARBOR_HOST = os.environ.get("OMNIA_OCI_HARBOR_HOST", "")
HARBOR_PORT = int(os.environ.get("OMNIA_OCI_HARBOR_PORT", "443"))
HARBOR_NAMESPACE = os.environ.get("OMNIA_OCI_HARBOR_NAMESPACE", "")
HARBOR_CA_FILE = os.environ.get("OMNIA_OCI_HARBOR_CA_FILE", "")


def _push_and_check(repo, local_digest, created, env, remote_repo):
    """Push every tag, then check digests, created, and a repeat push. Returns the three checks."""
    for tag in TAGS:
        remote_copy(f"{LOCAL_REGISTRY}/{repo}:{tag}", f"{remote_repo}:{tag}", env)
    remote = {tag: remote_digest(f"{remote_repo}:{tag}", env) for tag in TAGS}
    tags_agree = set(remote.values()) == {local_digest}
    kept = remote_annotations(f"{remote_repo}:10.2", env).get("org.opencontainers.image.created")
    for tag in TAGS:
        remote_copy(f"{LOCAL_REGISTRY}/{repo}:{tag}", f"{remote_repo}:{tag}", env)
    repeat_stable = remote_digest(f"{remote_repo}:10.2", env) == local_digest
    return tags_agree, kept == created, repeat_stable


def _cleanup_remote(remote_repo, env):
    """Delete every remote manifest that a tag still points to, by digest."""
    digests = set()
    for tag in TAGS:
        try:
            digests.add(remote_digest(f"{remote_repo}:{tag}", env))
        except RuntimeError:
            continue
    for digest_value in digests:
        remote_delete(remote_repo, digest_value, env)


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(17)
def test_external_push_keeps_digests_and_created():
    """After a push, tags match the local digest, created is kept, and a repeat push is stable."""
    tc = TC["oci_provenance_harbor_push"]
    tl = TestLogger(tc["title"], tc["id"])
    account = os.environ.get("OMNIA_OCI_TEST_USERNAME", "")
    secret = os.environ.get("OMNIA_OCI_TEST_PASSWORD", "")
    if not (HARBOR_HOST and HARBOR_NAMESPACE and HARBOR_CA_FILE and account and secret):
        tl.skipped(LOG["oci_probe_skipped"])
        pytest.skip(LOG["oci_probe_skipped"])

    repo = _fixture(TAGS)
    local_ref = f"{LOCAL_REGISTRY}/{repo}:10.2"
    created = config_created(local_ref)
    annotate(local_ref, publish_annotations(GROUP, JOB_ID, created))
    for tag in TAGS[1:]:
        copy_tag(repo, "10.2", tag)
    remote_repo = f"{HARBOR_HOST}:{HARBOR_PORT}/{HARBOR_NAMESPACE}/{repo}"
    config_path = _remote_config(HARBOR_HOST, HARBOR_PORT, account, secret, HARBOR_CA_FILE)
    env = remote_env(config_path)
    try:
        tags_agree, created_kept, repeat_stable = _push_and_check(
            repo, digest(local_ref), created, env, remote_repo)
        ok = tags_agree and created_kept and repeat_stable
        if ok:
            tl.passed(LOG["oci_provenance_ok"].format(
                detail="tags match the local digest; created kept; repeat push stable"))
        else:
            tl.failed(LOG["oci_provenance_failed"].format(
                expected="remote tags match, created kept, repeat push stable",
                observed=f"tags_agree={tags_agree} created_kept={created_kept} "
                         f"repeat_stable={repeat_stable}"))
        assert ok, ASSERT["oci_provenance_assert"].format(detail="external push provenance")
    finally:
        try:
            _cleanup_remote(remote_repo, env)
        finally:
            os.remove(config_path)
            remove_fixture(repo, TAGS)
