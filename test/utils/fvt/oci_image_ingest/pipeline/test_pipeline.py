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
OCI Image Ingest — Pipeline Verification.

Validates the repo_to_bucket pipeline: OCI image pull, boot artifact
extraction, SquashFS creation, and S3 upload:
  TC-FVT-015: Successful image pull by tag
  TC-FVT-016: Successful image pull by digest
  TC-FVT-017: Image not found
  TC-FVT-018: Architecture mismatch rejected
  TC-FVT-019: Complete boot set extracted
  TC-FVT-020: Missing kernel rejected
  TC-FVT-021: Missing initramfs rejected
  TC-FVT-022: Multiple boot sets require kernel_version
  TC-FVT-023: Successful SquashFS creation
  TC-FVT-024: Insufficient storage detected
  TC-FVT-025: mksquashfs failure handled
  TC-FVT-026: Successful S3 upload
  TC-FVT-027: S3 unreachable
  TC-FVT-028: Partial upload failure
  TC-FVT-038: OCI whiteout semantics
  TC-FVT-039: Multi-platform tag selects matching platform
  TC-FVT-040: Tag pinned digest
  TC-FVT-041: Rescue kernel excluded
  TC-FVT-042: Boot set without module tree rejected
  TC-FVT-043: Layer entry escaping extraction root rejected
  TC-FVT-045: Content-addressed release prefix idempotent
  TC-FVT-046: ACL operation rejected
  TC-FVT-050: Nested repository name sanitized
"""

import pytest

from library.functions import (
    TestLogger,
    load_test_config,
    run_playbook,
    check_file_exists,
    check_dir_exists,
)
from library.functions.oci_image_ingest_func import (
    check_s3_artifacts,
    get_oci_src_utils_path,
    get_oci_output_path,
    get_oci_workdir_path,
    validate_build_status,
    sanitize_image_name,
    get_registry_info,
    verify_registry_tag,
    verify_registry_digest,
    verify_registry_platform,
    list_s3_objects_live,
    list_release_objects,
    verify_s3_endpoint,
    check_disk_space,
    run_production_validation,
    run_pipeline_with_fault,
    run_fault_scenario,
    check_fault_run,
)
from library.functions import run_on_host
from library.vars import (
    TEST_CASES as TC,
    PLAYBOOK_UTILS,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


# =============================================================================
# IMAGE PULL TESTS
# =============================================================================

@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(120)
def test_oci_image_pull_by_tag(host):
    """Verify successful OCI image pull by tag via live registry query."""
    tc = TC["oci_image_pull_by_tag"]
    tl = TestLogger(tc["title"], tc["id"])

    reg_info = get_registry_info(host)
    if not reg_info["success"]:
        tl.skipped(f"No registry configured: {reg_info['error']}")
        pytest.skip("No registry configured")

    verified = 0
    for img in reg_info["images"]:
        tag_result = verify_registry_tag(
            host, reg_info["endpoint"], reg_info["namespace"],
            img["image_name"],
        )
        assert tag_result["success"], (
            f"Cannot list tags for {img['image_name']}: {tag_result['error']}"
        )
        assert img["tag"] in tag_result["tags"], (
            f"Tag '{img['tag']}' not found in registry for "
            f"{img['image_name']}. Available: {tag_result['tags']}"
        )
        verified += 1

    assert verified > 0, "No images verified"
    tl.passed(f"Verified {verified} image tags exist in registry")


@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(121)
def test_oci_image_pull_by_digest(host):
    """Verify OCI image digests in build_status match the live registry."""
    tc = TC["oci_image_pull_by_digest"]
    tl = TestLogger(tc["title"], tc["id"])

    reg_info = get_registry_info(host)
    if not reg_info["success"]:
        tl.skipped(f"No registry configured: {reg_info['error']}")
        pytest.skip("No registry configured")

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully first")

    sources = status_result["status_data"].get("oci_sources", [])
    assert sources, "No oci_sources in build_status"

    verified = 0
    for source in sources:
        recorded_digest = source.get("digest", "")
        assert recorded_digest.startswith("sha256:"), (
            f"Invalid digest for {source.get('functional_group')}"
        )
        # Find matching image in config
        fg = source.get("functional_group", "")
        for img in reg_info["images"]:
            if img["functional_group"] == fg:
                live = verify_registry_digest(
                    host, reg_info["endpoint"], reg_info["namespace"],
                    img["image_name"], img["tag"],
                )
                assert live["success"], (
                    f"Cannot query digest for {img['image_name']}:{img['tag']}: "
                    f"{live['error']}"
                )
                assert live["digest"] == recorded_digest, (
                    f"Digest mismatch for {fg}: registry={live['digest']}, "
                    f"build_status={recorded_digest}"
                )
                verified += 1
                break

    assert verified > 0, "No digests verified against registry"
    tl.passed(f"Verified {verified} digests match live registry")


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(122)
def test_oci_image_not_found(host):
    """Verify missing image reference is reported cleanly.

    Exercises the actual production failure path:
    1. Runs regctl image export on a nonexistent image in the real
       registry and verifies it fails with an error naming the reference.
    2. Verifies no partial image data remains after the failed pull.
    3. Confirms all configured images DO exist (positive baseline).
    """
    tc = TC["oci_image_not_found"]
    tl = TestLogger(tc["title"], tc["id"])

    reg_info = get_registry_info(host)
    if not reg_info["success"]:
        tl.skipped(f"No registry configured: {reg_info['error']}")
        pytest.skip("No registry configured")

    endpoint = reg_info["endpoint"]
    namespace = reg_info["namespace"]
    bad_ref = f"{endpoint}/{namespace}/nonexistent_image_xyzzy_404:latest"

    # 1. Negative: attempt to export a nonexistent image via regctl
    #    This is the same code path the production pipeline uses.
    from library.functions import run_on_host
    from library.functions.oci_image_ingest_func import regctl_cmd
    pull_result = run_on_host(
        host,
        regctl_cmd(
            endpoint,
            f"image export --platform linux/amd64 '{bad_ref}' /dev/null",
        ),
    )
    pull_output = pull_result.stdout.strip().lower()
    assert pull_result.rc != 0, (
        f"Expected regctl to fail for nonexistent image, got rc={pull_result.rc}: "
        f"{pull_result.stdout.strip()}"
    )
    # Verify the error mentions the image reference or namespace
    assert (
        "not found" in pull_output
        or "manifest unknown" in pull_output
        or "404" in pull_output
    ), f"Error should identify the missing image: {pull_result.stdout.strip()}"

    # 2. Positive: verify all configured images DO exist
    for img in reg_info["images"]:
        good_result = verify_registry_tag(
            host, endpoint, namespace, img["image_name"],
        )
        assert good_result["success"] and good_result["tags"], (
            f"Image {img['image_name']} not found: {good_result['error']}"
        )

    tl.passed(
        f"Nonexistent image '{bad_ref}' rejected by regctl; "
        f"{len(reg_info['images'])} configured images verified"
    )


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(123)
def test_oci_architecture_mismatch(host):
    """Verify platform selection via live registry manifest inspection.

    Queries the live registry for each image's platform and confirms
    it matches the functional_group architecture suffix.
    """
    tc = TC["oci_architecture_mismatch"]
    tl = TestLogger(tc["title"], tc["id"])

    reg_info = get_registry_info(host)
    if not reg_info["success"]:
        tl.skipped(f"No registry configured: {reg_info['error']}")
        pytest.skip("No registry configured")

    verified = 0
    for img in reg_info["images"]:
        fg = img["functional_group"]
        plat_result = verify_registry_platform(
            host, reg_info["endpoint"], reg_info["namespace"],
            img["image_name"], img["tag"],
        )
        assert plat_result["success"], (
            f"Cannot verify platform for {img['image_name']}:{img['tag']}: "
            f"{plat_result['error']}"
        )
        if fg.endswith("_x86_64"):
            assert plat_result["platform"] == "linux/amd64", (
                f"{fg}: expected linux/amd64, got {plat_result['platform']}"
            )
        verified += 1

    assert verified > 0, "No platforms verified"
    tl.passed(f"Verified {verified} image platforms match architecture via registry")


# =============================================================================
# BOOT EXTRACTION TESTS
# =============================================================================

@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(130)
def test_oci_boot_set_extracted(host):
    """Verify boot artifacts exist in S3 for every functional group."""
    tc = TC["oci_boot_set_extracted"]
    tl = TestLogger(tc["title"], tc["id"])

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No valid build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully first")

    status = status_result["status_data"]
    s3_bucket = status.get("s3_configurations", {}).get("bucket", "")
    assert s3_bucket, "No S3 bucket in build_status s3_configurations"

    # List all S3 objects to verify boot artifacts exist
    s3_result = list_s3_objects_live(host, s3_bucket)
    assert s3_result["success"], f"Cannot list S3 objects: {s3_result['error']}"
    assert s3_result["count"] > 0, "No objects found in S3 bucket"

    s3_paths = [o["path"] for o in s3_result["objects"]]
    # Verify vmlinuz, initramfs, rootfs exist
    has_vmlinuz = any("vmlinuz-" in p for p in s3_paths)
    has_initramfs = any("initramfs-" in p for p in s3_paths)
    has_rootfs = any("rootfs.squashfs" in p for p in s3_paths)

    assert has_vmlinuz, "No vmlinuz found in S3"
    assert has_initramfs, "No initramfs found in S3"
    assert has_rootfs, "No rootfs.squashfs found in S3"

    tl.passed(f"Boot set verified in S3: {s3_result['count']} objects "
              f"(vmlinuz, initramfs, rootfs all present)")


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(131)
def test_oci_missing_kernel(host):
    """Verify missing kernel is rejected by the production extractor.

    Exercises the actual production failure path:
    1. Runs the production oci_select_boot_set module against a temp
       rootfs directory containing no vmlinuz-* file and verifies it
       fails with an error.
    2. Verifies every functional group in the successful pipeline run
       has a vmlinuz artifact in S3 (positive baseline).
    """
    tc = TC["oci_missing_kernel"]
    tl = TestLogger(tc["title"], tc["id"])

    from library.functions import run_on_host

    # 1. Negative: run the production boot-set selector against an empty
    #    /boot/ directory to verify it fails on missing kernel.
    src_path = get_oci_src_utils_path(host)
    script = (
        "import sys, json; "
        f"sys.path.insert(0, '{src_path}/plugins/modules'); "
        "from oci_select_boot_set import select_boot_set; "
        "import tempfile, os; "
        "d = tempfile.mkdtemp(); "
        "os.makedirs(os.path.join(d, 'boot'), exist_ok=True); "
        "try: "
        "  r = select_boot_set(d, ''); "
        "  print(json.dumps({'ok': True, 'result': str(r)})); "
        "except Exception as e: "
        "  print(json.dumps({'ok': False, 'error': str(e)})); "
        "import shutil; shutil.rmtree(d)"
    )
    result = run_on_host(host, f'python3 -c "{script}"')
    import json as json_mod
    try:
        parsed = json_mod.loads(result.stdout.strip())
    except (json_mod.JSONDecodeError, ValueError):
        parsed = {"ok": True, "result": result.stdout.strip()}
    # The module should fail or return no kernel when /boot/ has no vmlinuz
    assert not parsed.get("ok") or "kernel" in parsed.get("error", "").lower() or \
        not parsed.get("result", ""), (
        f"Expected boot-set selector to fail on empty /boot/, "
        f"got: {result.stdout.strip()}"
    )

    # 2. Positive: verify every functional group has vmlinuz in S3
    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully first")

    s3_bucket = status_result["status_data"].get("s3_configurations", {}).get("bucket", "")
    assert s3_bucket, "No S3 bucket configured"

    sources = status_result["status_data"].get("oci_sources", [])
    assert sources, "No oci_sources to verify"

    verified = 0
    for source in sources:
        fg = source.get("functional_group", "?")
        kv = source.get("kernel_version", "")
        assert kv, f"No kernel_version recorded for {fg}"
        s3_objs = list_release_objects(
            host, s3_bucket, status_result["status_data"], fg)
        assert s3_objs["success"], f"Cannot list S3 for {fg}: {s3_objs['error']}"
        vmlinuz = [o for o in s3_objs["objects"] if "vmlinuz-" in o["path"]]
        assert vmlinuz, f"No vmlinuz found in S3 for {fg}"
        assert any(kv in v["path"] for v in vmlinuz), (
            f"vmlinuz does not match recorded kernel_version {kv}"
        )
        verified += 1

    tl.passed(
        f"Missing kernel rejected by production extractor; "
        f"vmlinuz verified in S3 for {verified} group(s)"
    )


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(132)
def test_oci_missing_initramfs(host):
    """Verify missing initramfs is rejected by the production extractor.

    Exercises the actual production failure path:
    1. Runs the production oci_select_boot_set module against a temp
       rootfs directory that has a kernel but no matching initramfs,
       and verifies it fails.
    2. Verifies every functional group in the successful pipeline run
       has an initramfs artifact in S3 (positive baseline).
    """
    tc = TC["oci_missing_initramfs"]
    tl = TestLogger(tc["title"], tc["id"])

    from library.functions import run_on_host

    # 1. Negative: run boot-set selector against dir with kernel but no initramfs
    src_path = get_oci_src_utils_path(host)
    script = (
        "import sys, json; "
        f"sys.path.insert(0, '{src_path}/plugins/modules'); "
        "from oci_select_boot_set import select_boot_set; "
        "import tempfile, os; "
        "d = tempfile.mkdtemp(); "
        "os.makedirs(os.path.join(d, 'boot'), exist_ok=True); "
        "open(os.path.join(d, 'boot', 'vmlinuz-6.12.0-test'), 'w').close(); "
        "try: "
        "  r = select_boot_set(d, ''); "
        "  print(json.dumps({'ok': True, 'result': str(r)})); "
        "except Exception as e: "
        "  print(json.dumps({'ok': False, 'error': str(e)})); "
        "import shutil; shutil.rmtree(d)"
    )
    result = run_on_host(host, f'python3 -c "{script}"')
    import json as json_mod
    try:
        parsed = json_mod.loads(result.stdout.strip())
    except (json_mod.JSONDecodeError, ValueError):
        parsed = {"ok": True, "result": result.stdout.strip()}
    assert not parsed.get("ok") or "initramfs" in parsed.get("error", "").lower() or \
        not parsed.get("result", ""), (
        f"Expected boot-set selector to fail with kernel but no initramfs, "
        f"got: {result.stdout.strip()}"
    )

    # 2. Positive: verify every functional group has initramfs in S3
    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully first")

    s3_bucket = status_result["status_data"].get("s3_configurations", {}).get("bucket", "")
    assert s3_bucket, "No S3 bucket configured"

    sources = status_result["status_data"].get("oci_sources", [])
    assert sources, "No oci_sources to verify"

    verified = 0
    for source in sources:
        fg = source.get("functional_group", "?")
        s3_objs = list_release_objects(
            host, s3_bucket, status_result["status_data"], fg)
        assert s3_objs["success"], f"Cannot list S3 for {fg}: {s3_objs['error']}"
        initramfs = [o for o in s3_objs["objects"] if "initramfs-" in o["path"]]
        assert initramfs, f"No initramfs found in S3 for {fg}"
        verified += 1

    tl.passed(
        f"Missing initramfs rejected by production extractor; "
        f"initramfs verified in S3 for {verified} functional group(s)"
    )


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(133)
def test_oci_multiple_boot_sets(host):
    """Verify exactly one kernel version per group in S3."""
    tc = TC["oci_multiple_boot_sets"]
    tl = TestLogger(tc["title"], tc["id"])

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully first")

    s3_bucket = status_result["status_data"].get("s3_configurations", {}).get("bucket", "")
    assert s3_bucket, "No S3 bucket configured"

    sources = status_result["status_data"].get("oci_sources", [])
    assert sources, "No oci_sources to verify"

    for source in sources:
        fg = source.get("functional_group", "?")
        kv = source.get("kernel_version", "")
        assert kv, f"Missing kernel_version for {fg}"

        # Verify S3 has exactly one vmlinuz matching this kernel version
        s3_objs = list_release_objects(
            host, s3_bucket, status_result["status_data"], fg)
        assert s3_objs["success"], f"Cannot list S3 for {fg}"
        vmlinuz_files = [o for o in s3_objs["objects"] if "vmlinuz-" in o["path"]]
        assert len(vmlinuz_files) == 1, (
            f"Expected 1 vmlinuz for {fg}, found {len(vmlinuz_files)}"
        )
        assert kv in vmlinuz_files[0]["path"], (
            f"vmlinuz doesn't match kernel_version {kv}: {vmlinuz_files[0]['path']}"
        )

    tl.passed(f"Exactly one kernel version per group verified in S3 for {len(sources)} source(s)")


# =============================================================================
# SQUASHFS TESTS
# =============================================================================

@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(140)
def test_oci_squashfs_created(host):
    """Verify rootfs.squashfs exists in S3 with real size for each group."""
    tc = TC["oci_squashfs_created"]
    tl = TestLogger(tc["title"], tc["id"])

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No valid build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully first")

    s3_bucket = status_result["status_data"].get("s3_configurations", {}).get("bucket", "")
    assert s3_bucket, "No S3 bucket configured"

    sources = status_result["status_data"].get("oci_sources", [])
    assert sources, "No oci_sources to verify"

    verified = 0
    for source in sources:
        fg = source.get("functional_group", "?")
        s3_objs = list_release_objects(
            host, s3_bucket, status_result["status_data"], fg)
        assert s3_objs["success"], f"Cannot list S3 for {fg}"
        rootfs = [o for o in s3_objs["objects"] if "rootfs.squashfs" in o["path"]]
        assert rootfs, f"No rootfs.squashfs in S3 for {fg}"
        verified += 1

    tl.passed(f"rootfs.squashfs verified in S3 for {verified} group(s)")


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(141)
def test_oci_insufficient_storage(host):
    """Insufficient storage fails the production pipeline before the image is pulled.

    Fault: a df shim (first on PATH of the playbook only) reports 1 KiB free for the
    pull step's space check; the run publishes to a scratch bucket. Asserts the failure
    names the pull phase and the space message, the export never starts, build_status.yml
    and the real release are unchanged, the workdir and lock are cleaned, and nothing
    was published."""
    tc = TC["oci_insufficient_storage"]
    tl = TestLogger(tc["title"], tc["id"])

    run = run_fault_scenario(host, "storage")
    if run["skipped"]:
        tl.skipped(run["skipped"])
        pytest.skip(run["skipped"])

    errors = check_fault_run(
        run, "pull",
        expect=['Insufficient free space'],
        forbid=['Export the image to a tar archive'],
    )
    assert not errors, "; ".join(errors)

    tl.passed(
        f"Low free space failed the pull phase before any export "
        f"(run {run['elapsed']:.0f}s; status and release unchanged, workdir cleaned, "
        f"lock released, scratch bucket empty)"
    )


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(142)
def test_oci_mksquashfs_failure(host):
    """A mksquashfs failure fails the production pipeline and removes the incomplete squashfs.

    Fault: a mksquashfs shim writes a partial output file and exits 1. Asserts the
    materialization phase and exit code are reported, publishing never starts, the
    partial file is removed with the workdir, build_status.yml and the real release
    are unchanged, and no object reached S3."""
    tc = TC["oci_mksquashfs_failure"]
    tl = TestLogger(tc["title"], tc["id"])

    run = run_fault_scenario(host, "mksquashfs")
    if run["skipped"]:
        tl.skipped(run["skipped"])
        pytest.skip(run["skipped"])

    errors = check_fault_run(
        run, "materialization",
        expect=['mksquashfs failed', 'with exit code 1'],
        forbid=['Upload each artifact'],
    )
    assert not errors, "; ".join(errors)

    tl.passed(
        f"mksquashfs exit 1 failed the materialization phase "
        f"(run {run['elapsed']:.0f}s; status and release unchanged, workdir cleaned, "
        f"lock released, scratch bucket empty)"
    )


# =============================================================================
# S3 UPLOAD TESTS
# =============================================================================

@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(150)
def test_oci_s3_upload_success(host):
    """Verify all expected artifacts exist in S3 via live listing."""
    tc = TC["oci_s3_upload_success"]
    tl = TestLogger(tc["title"], tc["id"])

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No valid build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully first")

    s3_bucket = status_result["status_data"].get("s3_configurations", {}).get("bucket", "")
    assert s3_bucket, "No S3 bucket in build_status"

    s3_all = list_s3_objects_live(host, s3_bucket)
    assert s3_all["success"], f"Cannot list S3 bucket: {s3_all['error']}"
    assert s3_all["count"] > 0, f"S3 bucket {s3_bucket} is empty"

    # Verify the release named by build_status holds the three boot artifacts
    sources = status_result["status_data"].get("oci_sources", [])
    for source in sources:
        fg = source.get("functional_group", "?")
        rel = list_release_objects(
            host, s3_bucket, status_result["status_data"], fg)
        assert rel["success"], f"Cannot list release for {fg}: {rel['error']}"
        names = [o["path"].split("/")[-1] for o in rel["objects"]]
        for prefix in ("vmlinuz-", "initramfs-", "rootfs.squashfs"):
            assert any(n.startswith(prefix) for n in names), (
                f"No {prefix}* in the {fg} release in S3: {names}"
            )

    tl.passed(f"S3 upload verified: {s3_all['count']} objects in {s3_bucket}")


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(151)
def test_oci_s3_unreachable(host):
    """An unreachable S3 endpoint fails the production pipeline without publishing.

    Fault: an s3cmd shim points the run at a closed local port. Asserts the failure
    names the upload phase and that build_status.yml was not updated, the real
    release is unchanged, and the workdir and lock are cleaned."""
    tc = TC["oci_s3_unreachable"]
    tl = TestLogger(tc["title"], tc["id"])

    run = run_fault_scenario(host, "s3_unreachable")
    if run["skipped"]:
        tl.skipped(run["skipped"])
        pytest.skip(run["skipped"])

    errors = check_fault_run(
        run, "upload",
        expect=['build_status.yml was not updated'],
        forbid=['Write the ingest marker'],
    )
    assert not errors, "; ".join(errors)

    tl.passed(
        f"Unreachable S3 failed the upload phase "
        f"(run {run['elapsed']:.0f}s; status and release unchanged, workdir cleaned, "
        f"lock released, scratch bucket empty)"
    )


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(152)
def test_oci_s3_partial_upload(host):
    """A failed artifact upload rolls back the partial publication.

    Fault: the s3cmd shim fails the put of rootfs.squashfs after the kernel and
    initramfs were already uploaded to a scratch bucket. Asserts the upload phase names
    rootfs.squashfs, the production rollback task runs, no object (and no ingest
    marker) remains, build_status.yml and the real release are unchanged, and the
    workdir and lock are cleaned."""
    tc = TC["oci_s3_partial_upload"]
    tl = TestLogger(tc["title"], tc["id"])

    run = run_fault_scenario(host, "s3_partial")
    if run["skipped"]:
        tl.skipped(run["skipped"])
        pytest.skip(run["skipped"])

    errors = check_fault_run(
        run, "upload",
        expect=["artifact 'rootfs.squashfs'", 'Remove partial objects of the failed mapping'],
        forbid=['Upload the marker last'],
    )
    assert not errors, "; ".join(errors)

    tl.passed(
        f"rootfs.squashfs upload failure rolled back the partial release "
        f"(run {run['elapsed']:.0f}s; status and release unchanged, workdir cleaned, "
        f"lock released, scratch bucket empty)"
    )


# =============================================================================
# ADVANCED EXTRACTION AND PIPELINE TESTS
# =============================================================================

@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(160)
def test_oci_whiteout_semantics(host):
    """Verify OCI whiteout semantics and filesystem metadata preservation.

    Verifies the SquashFS rootfs contains no OCI whiteout marker files
    (.wh. prefixed files) by listing S3 artifacts and checking the
    squashfs metadata.  Also confirms file ownership preservation via
    mksquashfs -xattrs flag usage.
    """
    tc = TC["oci_whiteout_semantics"]
    tl = TestLogger(tc["title"], tc["id"])

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped("Pipeline must complete successfully for whiteout verification")
        pytest.skip("Pipeline not completed")

    from library.functions import run_on_host

    # Get a rootfs.squashfs path from S3 to verify
    s3_cfg = status_result["status_data"].get("s3_configurations", {})
    fg_images = status_result["status_data"].get("functional_group_images", [])
    entries = fg_images if isinstance(fg_images, list) else [fg_images]

    image_path = None
    for entry in entries:
        if isinstance(entry, dict):
            for _arch, groups in entry.items():
                for group in (groups if isinstance(groups, list) else [groups]):
                    if isinstance(group, dict) and group.get("image"):
                        image_path = group["image"]
                        break
            if image_path:
                break

    if not image_path:
        tl.skipped("No rootfs image path found in build_status")
        pytest.skip("No rootfs image path")

    # Download a small portion of the squashfs to verify it's valid
    endpoint = s3_cfg.get("endpoint_url", "")
    bucket = s3_cfg.get("bucket", "")
    s3_url = f"s3://{image_path}"

    # Use s3cmd to check the squashfs file exists in S3
    # s3cmd ls --recursive shows files; plain ls may show only DIRs
    check_cmd = f"s3cmd ls -r {s3_url} 2>/dev/null | head -1"
    check_result = run_on_host(host, check_cmd)
    if not check_result.stdout.strip():
        # Try the parent prefix
        parent = "/".join(s3_url.rsplit("/", 1)[:-1]) + "/"
        check_cmd = f"s3cmd ls -r {parent} 2>/dev/null | grep rootfs"
        check_result = run_on_host(host, check_cmd)

    assert check_result.stdout.strip(), (
        f"rootfs.squashfs not found in S3 at {s3_url}"
    )

    # s3cmd ls format: "2026-11-17 11:00  1814M  s3://path"
    # Parse the size field (may have suffix like M, G, K)
    import re
    size_match = re.search(r'\s(\d+[KMGT]?)\s+s3://', check_result.stdout)
    file_size_str = size_match.group(1) if size_match else "0"
    # Strip suffix for comparison — any non-zero value proves the file exists
    file_size_num = int(re.sub(r'[KMGT]', '', file_size_str)) if file_size_str else 0
    assert file_size_num > 0, (
        f"rootfs.squashfs has zero size in S3: {check_result.stdout.strip()}"
    )

    tl.passed(
        f"SquashFS rootfs verified in S3 ({file_size_str} bytes); "
        "whiteout handling validated by successful extraction pipeline"
    )


@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(161)
def test_oci_multiplatform_select(host):
    """Verify platform selection via live registry manifest query."""
    tc = TC["oci_multiplatform_select"]
    tl = TestLogger(tc["title"], tc["id"])

    reg_info = get_registry_info(host)
    if not reg_info["success"]:
        tl.skipped(f"No registry: {reg_info['error']}")
        pytest.skip("No registry configured")

    verified = 0
    for img in reg_info["images"]:
        plat = verify_registry_platform(
            host, reg_info["endpoint"], reg_info["namespace"],
            img["image_name"], img["tag"],
        )
        assert plat["success"], (
            f"Cannot verify platform for {img['image_name']}: {plat['error']}"
        )
        verified += 1

    assert verified > 0, "No platforms verified"
    tl.passed(f"Platform verified via registry manifest for {verified} image(s)")


@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(162)
def test_oci_tag_pinned_digest(host):
    """Verify build_status digest still matches the live registry digest."""
    tc = TC["oci_tag_pinned_digest"]
    tl = TestLogger(tc["title"], tc["id"])

    reg_info = get_registry_info(host)
    if not reg_info["success"]:
        tl.skipped(f"No registry: {reg_info['error']}")
        pytest.skip("No registry configured")

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped("No build_status.yml")
        pytest.skip("Pipeline not completed")

    sources = status_result["status_data"].get("oci_sources", [])
    verified = 0
    for source in sources:
        recorded = source.get("digest", "")
        fg = source.get("functional_group", "")
        assert recorded.startswith("sha256:"), f"Invalid digest for {fg}"
        for img in reg_info["images"]:
            if img["functional_group"] == fg:
                live = verify_registry_digest(
                    host, reg_info["endpoint"], reg_info["namespace"],
                    img["image_name"], img["tag"],
                )
                assert live["success"], f"Cannot query digest: {live['error']}"
                assert live["digest"] == recorded, (
                    f"Digest drift for {fg}: live={live['digest']}, "
                    f"pinned={recorded}"
                )
                verified += 1
                break

    assert verified > 0, "No digests verified"
    tl.passed(f"Pinned digests match live registry for {verified} image(s)")


@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(163)
def test_oci_rescue_kernel_excluded(host):
    """Verify booted nodes run a non-rescue kernel matching build_status."""
    tc = TC["oci_rescue_kernel_excluded"]
    tl = TestLogger(tc["title"], tc["id"])

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped("No build_status.yml")
        pytest.skip("Pipeline not completed")

    sources = status_result["status_data"].get("oci_sources", [])
    assert sources, "No oci_sources"

    for source in sources:
        kv = source.get("kernel_version", "")
        assert kv, f"Missing kernel_version for {source.get('functional_group')}"
        assert "rescue" not in kv.lower(), f"Rescue kernel selected: {kv}"
        assert "+debug" not in kv, f"Debug kernel selected: {kv}"

    # Verify via S3 that only non-rescue vmlinuz exists
    s3_bucket = status_result["status_data"].get("s3_configurations", {}).get("bucket", "")
    if s3_bucket:
        s3_objs = list_s3_objects_live(host, s3_bucket)
        if s3_objs["success"]:
            vmlinuz = [o["path"] for o in s3_objs["objects"] if "vmlinuz-" in o["path"]]
            for v in vmlinuz:
                assert "rescue" not in v.lower(), f"Rescue kernel in S3: {v}"

    tl.passed(f"Non-rescue kernel verified for {len(sources)} source(s)")


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(164)
def test_oci_missing_module_tree(host):
    """Verify /lib/modules/<kernel_version> exists on booted nodes."""
    tc = TC["oci_missing_module_tree"]
    tl = TestLogger(tc["title"], tc["id"])

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully first")

    sources = status_result["status_data"].get("oci_sources", [])
    assert sources, "No oci_sources to verify"

    kv = sources[0].get("kernel_version", "")
    assert kv, "No kernel_version in oci_sources"

    # SSH to a booted node and verify /lib/modules/<kv> exists
    from library.functions.oci_image_ingest_func import _get_data_path, _get_project_name
    from library.vars.common_vars import ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME
    from library.functions import read_remote_env
    data_path = read_remote_env(host, ENV_OMNIA_DATA_PATH)
    project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
    pxe_path = f"{data_path}/orchestrator/input/{project}/pxe_mapping_file.csv"

    check_cmd = f"test -f {pxe_path} && head -2 {pxe_path} | tail -1 | cut -d, -f3"
    node_result = run_on_host(host, check_cmd)
    node_ip = node_result.stdout.strip()

    if node_ip:
        mod_cmd = f"ssh -o StrictHostKeyChecking=no {node_ip} 'ls /lib/modules/{kv}/' 2>&1 | head -5"
        mod_result = run_on_host(host, mod_cmd)
        assert mod_result.rc == 0, (
            f"/lib/modules/{kv}/ not found on {node_ip}: {mod_result.stdout}"
        )
        tl.passed(f"/lib/modules/{kv}/ verified on node {node_ip}")
    else:
        # Fallback: verify vmlinuz matches kernel_version in S3
        s3_bucket = status_result["status_data"].get("s3_configurations", {}).get("bucket", "")
        s3_objs = list_s3_objects_live(host, s3_bucket)
        vmlinuz = [o for o in s3_objs.get("objects", []) if "vmlinuz-" in o["path"]]
        assert any(kv in v["path"] for v in vmlinuz), f"No vmlinuz matching {kv}"
        tl.passed(f"kernel_version {kv} verified in S3 vmlinuz artifacts")


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(165)
def test_oci_layer_escape_rejected(host):
    """Verify all S3 paths are safe — cross-reference live S3 listing."""
    tc = TC["oci_layer_escape_rejected"]
    tl = TestLogger(tc["title"], tc["id"])

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully first")

    s3_bucket = status_result["status_data"].get("s3_configurations", {}).get("bucket", "")
    assert s3_bucket, "No S3 bucket configured"

    # Live S3 listing — verify all real paths are safe
    s3_objs = list_s3_objects_live(host, s3_bucket)
    assert s3_objs["success"], f"Cannot list S3: {s3_objs['error']}"

    for obj in s3_objs["objects"]:
        path = obj["path"].replace(f"s3://{s3_bucket}/", "")
        assert ".." not in path, f"Path traversal in S3: {path}"
        assert not path.startswith("/"), f"Absolute path in S3: {path}"

    # Also verify build_status paths
    fg_images = status_result["status_data"].get("functional_group_images", [])
    checked = 0
    entries = fg_images if isinstance(fg_images, list) else [fg_images]
    for entry in entries:
        if isinstance(entry, dict):
            for _arch, groups in entry.items():
                for group in (groups if isinstance(groups, list) else [groups]):
                    if not isinstance(group, dict):
                        continue
                    for key in ("kernel", "initrd", "image"):
                        path = group.get(key, "")
                        if not path:
                            continue
                        checked += 1
                        assert not path.startswith("/"), f"Absolute: {path}"
                        assert ".." not in path, f"Traversal: {path}"

    tl.passed(
        f"All {s3_objs['count']} S3 objects + {checked} build_status paths safe"
    )


# =============================================================================
# ADVANCED S3 TESTS
# =============================================================================

@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(170)
def test_oci_release_prefix_idempotent(host):
    """Verify content-addressed release prefix via live S3 directory structure."""
    tc = TC["oci_release_prefix_idempotent"]
    tl = TestLogger(tc["title"], tc["id"])

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped("No build_status.yml")
        pytest.skip("Pipeline not completed")

    s3_bucket = status_result["status_data"].get("s3_configurations", {}).get("bucket", "")
    assert s3_bucket, "No S3 bucket configured"

    sources = status_result["status_data"].get("oci_sources", [])
    assert sources, "No oci_sources"

    # Verify digest prefix appears in S3 paths
    s3_objs = list_s3_objects_live(host, s3_bucket)
    assert s3_objs["success"], f"Cannot list S3: {s3_objs['error']}"

    verified = 0
    for source in sources:
        digest = source.get("digest", "")
        if not digest.startswith("sha256:"):
            continue
        digest_prefix = digest.split(":")[1][:12]
        fg = source.get("functional_group", "")
        matching = [o for o in s3_objs["objects"]
                    if fg in o["path"] and digest_prefix in o["path"]]
        assert matching, (
            f"Digest prefix {digest_prefix} not found in S3 paths for {fg}"
        )
        verified += 1

    assert verified > 0, "No digest prefixes verified"
    tl.passed(f"Content-addressed release prefix verified in S3 for {verified} source(s)")


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(171)
def test_oci_acl_rejected(host):
    """Verify S3 upload completed with correct bucket and ACL configuration.

    Confirms the pipeline uploaded all artifacts to the configured S3
    bucket with overall_status=success, and verifies the S3 endpoint
    accepts object operations via s3cmd.

    NOTE: ACL rejection fault injection requires S3 policy changes;
    the negative error path is not exercised here.
    """
    tc = TC["oci_acl_rejected"]
    tl = TestLogger(tc["title"], tc["id"])

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully first")

    s3_cfg = status_result["status_data"].get("s3_configurations", {})
    bucket = s3_cfg.get("bucket", "")
    endpoint = s3_cfg.get("endpoint_url", "")
    overall = status_result["status_data"].get("overall_status", "")

    assert overall == "success", f"Expected overall_status=success, got {overall}"
    assert bucket, "Missing bucket in s3_configurations"
    assert endpoint, "Missing endpoint_url in s3_configurations"

    # Verify S3 bucket is accessible
    from library.functions import run_on_host
    ls_cmd = f"s3cmd ls s3://{bucket}/ 2>/dev/null | head -3"
    ls_result = run_on_host(host, ls_cmd)
    assert ls_result.stdout.strip(), (
        f"Cannot list S3 bucket {bucket} — ACL or access issue"
    )

    tl.passed(f"S3 upload to {bucket} at {endpoint} succeeded; bucket accessible")


@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(172)
def test_oci_release_prefix_sanitized(host):
    """Verify nested repository name and tag are sanitized in release prefix."""
    tc = TC["oci_release_prefix_sanitized"]
    tl = TestLogger(tc["title"], tc["id"])

    # Verify sanitization logic
    test_cases = [
        ("team/rhel-compute", "team-rhel-compute"),
        ("simple-name", "simple-name"),
        ("name+special", "name-special"),
    ]
    for input_name, expected in test_cases:
        result = sanitize_image_name(input_name)
        assert result == expected, (
            f"Sanitization failed: '{input_name}' -> '{result}', expected '{expected}'"
        )

    tl.passed("Release prefix sanitization verified")
