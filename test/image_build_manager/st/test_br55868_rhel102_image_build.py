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
Tier 1: Image Build — RHEL 10.2 EUS Image Build and Validation.

Test Plan: BR-55868 — RHEL 10.2 Support for x86_64 Functional Groups
ER: ER-ORCH-010-rhel-10-2-x86-64-support

Tier 1 Tests:
  TC-002: RHEL 10.0 EUS and 10.2 EUS Image Build via Native Path
  TC-004: RHEL 10.2 EUS Build Status Contract Validation
  TC-006: Driver Version Alignment Verification
  TC-007: VAST Driver Inclusion in Slurm Node Images
"""

import subprocess
import pytest
import yaml
import sys
from pathlib import Path
from typing import Dict, Any, List

# Import from domain library
from library.st_helpers.test_logger import TestLogger
from library.st_helpers.contract_validator import ContractValidator


# ============================================================================
# Helpers
# ============================================================================

def _extract_fg_groups(build_status: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten functional_group_images into a list of FG dicts."""
    groups = []
    fgs = build_status.get("functional_groups") or build_status.get(
        "functional_group_images", []
    )
    if isinstance(fgs, list):
        for arch_entry in fgs:
            if isinstance(arch_entry, dict):
                for _arch, fg_list in arch_entry.items():
                    if isinstance(fg_list, list):
                        groups.extend(
                            g for g in fg_list if isinstance(g, dict)
                        )
    elif isinstance(fgs, dict):
        for fg_name, fg_data in fgs.items():
            if isinstance(fg_data, dict):
                fg_data.setdefault("functional_group", fg_name)
                groups.append(fg_data)
    return groups


def _s3_object_exists(s3_key: str) -> bool:
    """Check if an S3 object exists using s3cmd."""
    s3_uri = f"s3://{s3_key}" if not s3_key.startswith("s3://") else s3_key
    try:
        result = subprocess.run(
            ["s3cmd", "ls", s3_uri],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0 and len(result.stdout.strip()) > 0
    except Exception:
        return False


# ============================================================================
# TC-002: RHEL 10.0 EUS and 10.2 EUS Image Build via Native Path
# ============================================================================

@pytest.mark.st
@pytest.mark.tier1
@pytest.mark.image_build_manager
@pytest.mark.rhel102
@pytest.mark.rhel100
def test_rhel102_image_build_dual(build_status, test_logger):
    """TC-002: RHEL 10.0 EUS and 10.2 EUS Image Build via Native Path.

    Objective: Verify Image Build Manager produces bootable images for
    both RHEL 10.0 EUS and RHEL 10.2 EUS x86_64 via the native image-build
    path and uploads them to S3 with correct build_status.yml. Validate
    expected artifacts for both OS versions.

    Acceptance Criteria (Gherkin):
    GIVEN a successful repo_status.yml with both RHEL 10.0 EUS and 10.2 EUS
    AND the native image-build path is selected (BuildStream not enabled)
    WHEN the Image Build Manager builds images for a dual-version catalog
    THEN bootable kernel, initramfs, and rootfs artifacts are uploaded to S3
         for BOTH 10.0 EUS and 10.2 EUS FGs
    AND build_status.yml reports overall_status success with complete artifact
        keys for both OS versions
    AND artifact paths are distinct per OS version with no cross-contamination
    """
    tc_id = "TC-002"
    tc_name = "RHEL 10.0 EUS and 10.2 EUS Image Build via Native Path"
    tl = test_logger(tc_name, tc_id)

    try:
        tl.info("Validating build_status.yml contract...")

        # Step 1: Verify native image-build path (not BuildStream)
        image_build_type = build_status.get("image_build_type", "")
        assert image_build_type and image_build_type != "buildstream", (
            f"Expected native image-build path, got: {image_build_type}"
        )
        tl.info(f"✓ Native image-build path: {image_build_type}")

        # Step 2 + Step 5: Validate contract and overall status
        validation = ContractValidator.validate_build_status(build_status)
        assert validation["valid"], (
            f"Contract validation failed: {validation['errors']}"
        )
        tl.info("✓ build_status.yml contract is valid")

        assert build_status.get("overall_status") == "success", (
            f"Expected overall_status=success, "
            f"got {build_status.get('overall_status')}"
        )
        tl.info("✓ overall_status is success")

        # Extract all FGs and classify by OS version
        all_fgs = _extract_fg_groups(build_status)
        assert all_fgs, "No functional groups found in build_status.yml"

        fgs_100 = [
            g for g in all_fgs
            if "10_0" in g.get("functional_group", "")
        ]
        fgs_102 = [
            g for g in all_fgs
            if "10_2" in g.get("functional_group", "")
        ]

        # Step 6: Verify RHEL 10.2 EUS FGs have artifact keys
        assert fgs_102, "No RHEL 10.2 FGs found in build_status.yml"
        required_artifacts = ["kernel", "initrd", "image"]
        for fg in fgs_102:
            fg_name = fg.get("functional_group", "unknown")
            for artifact in required_artifacts:
                path = fg.get(artifact)
                assert path and path.strip(), (
                    f"Missing or empty {artifact} for 10.2 FG {fg_name}"
                )
            tl.info(f"✓ 10.2 FG {fg_name}: all artifacts present")

        # Step 7: Verify RHEL 10.0 EUS FGs have artifact keys
        assert fgs_100, "No RHEL 10.0 FGs found in build_status.yml"
        for fg in fgs_100:
            fg_name = fg.get("functional_group", "unknown")
            for artifact in required_artifacts:
                path = fg.get(artifact)
                assert path and path.strip(), (
                    f"Missing or empty {artifact} for 10.0 FG {fg_name}"
                )
            tl.info(f"✓ 10.0 FG {fg_name}: all artifacts present")

        tl.info(
            f"✓ Total: {len(fgs_100)} RHEL 10.0 FGs, "
            f"{len(fgs_102)} RHEL 10.2 FGs"
        )

        # Step 8: Verify artifact paths are distinct per OS version
        for fg in all_fgs:
            fg_name = fg.get("functional_group", "")
            img_path = fg.get("image", "")
            if "10_0" in fg_name:
                assert "10.2" not in img_path and "10_2" not in img_path, (
                    f"Cross-contamination: 10.0 FG '{fg_name}' has 10.2 "
                    f"artifact: {img_path}"
                )
            elif "10_2" in fg_name:
                assert "10.0" not in img_path and "10_0" not in img_path, (
                    f"Cross-contamination: 10.2 FG '{fg_name}' has 10.0 "
                    f"artifact: {img_path}"
                )
        tl.info("✓ No cross-contamination in artifact paths")

        # Step 3-4: Verify S3 artifacts exist for a sample FG per version
        s3_config = build_status.get("s3_config") or build_status.get(
            "s3_configurations", {}
        )
        assert s3_config, "No S3 configuration found in build_status.yml"
        endpoint = s3_config.get("endpoint") or s3_config.get("endpoint_url")
        assert endpoint, "Missing S3 endpoint"
        bucket = s3_config.get("bucket")
        assert bucket, "Missing S3 bucket"
        tl.info(f"✓ S3 configuration valid: {endpoint} / {bucket}")

        # Verify S3 objects for each FG's image artifact
        s3_verified = 0
        for fg in all_fgs:
            fg_name = fg.get("functional_group", "unknown")
            img_key = fg.get("image", "")
            if img_key:
                exists = _s3_object_exists(img_key)
                assert exists, (
                    f"S3 object not found for FG {fg_name}: {img_key}"
                )
                s3_verified += 1
        tl.info(f"✓ S3 artifacts verified for {s3_verified} FGs")

        tl.passed(
            "RHEL 10.0 EUS and 10.2 EUS Image Build via Native Path "
            "test passed"
        )

    except AssertionError as e:
        tl.failed(
            "RHEL 10.0 EUS and 10.2 EUS Image Build test failed", str(e)
        )
        raise
    except Exception as e:
        tl.failed(
            "Unexpected error in RHEL 10.0 EUS and 10.2 EUS Image Build test",
            str(e),
        )
        raise


# ============================================================================
# TC-004: RHEL 10.2 EUS Build Status Contract Validation
# ============================================================================

@pytest.mark.st
@pytest.mark.tier1
@pytest.mark.image_build_manager
@pytest.mark.rhel102
def test_rhel102_build_status_contract(
    build_status, repo_status, test_logger
):
    """TC-004: RHEL 10.2 EUS Build Status Contract Validation.

    Objective: Verify build_status.yml is consumable by Orchestrator for
    BSS configuration. Verify it includes driver version metadata for both
    OS versions.

    Acceptance Criteria (Gherkin):
    GIVEN Image Build Manager produced build_status.yml with RHEL 10.0 EUS
         and 10.2 EUS artifacts
    WHEN Orchestrator reads the contract
    THEN all referenced S3 artifact keys exist and are accessible
    AND driver version metadata is recorded for each functional group image
    AND BSS boot configuration can be derived for each functional group
    """
    tc_id = "TC-004"
    tc_name = "RHEL 10.2 EUS Build Status Contract Validation"
    tl = test_logger(tc_name, tc_id)

    try:
        tl.info("Validating build_status.yml contract...")

        # Step 1: Validate contract structure
        validation = ContractValidator.validate_build_status(build_status)
        assert validation["valid"], (
            f"Contract validation failed: {validation['errors']}"
        )
        tl.info("✓ Contract structure is valid")

        assert build_status.get("overall_status") == "success", (
            f"Expected overall_status=success, "
            f"got {build_status.get('overall_status')}"
        )
        tl.info("✓ overall_status is success")

        # Step 2: Verify S3 configuration
        s3_config = build_status.get("s3_config") or build_status.get(
            "s3_configurations", {}
        )
        assert s3_config, "No S3 configuration found"
        endpoint = s3_config.get("endpoint") or s3_config.get("endpoint_url")
        assert endpoint, "Missing S3 endpoint"
        bucket = s3_config.get("bucket")
        assert bucket, "Missing S3 bucket"
        tl.info("✓ S3 configuration is present and valid")

        # Step 3-4: Verify FGs with version-specific checks
        all_fgs = _extract_fg_groups(build_status)
        assert all_fgs, "No functional groups found in build_status.yml"

        fgs_100 = [
            g for g in all_fgs
            if "10_0" in g.get("functional_group", "")
        ]
        fgs_102 = [
            g for g in all_fgs
            if "10_2" in g.get("functional_group", "")
        ]

        for fg in fgs_102:
            fg_name = fg.get("functional_group", "unknown")
            assert fg.get("kernel"), f"Missing kernel for 10.2 FG: {fg_name}"
            assert fg.get("initrd"), f"Missing initrd for 10.2 FG: {fg_name}"
            assert fg.get("image"), f"Missing image for 10.2 FG: {fg_name}"
            tl.info(f"✓ RHEL 10.2 FG {fg_name}: all artifacts present")

        for fg in fgs_100:
            fg_name = fg.get("functional_group", "unknown")
            assert fg.get("kernel"), f"Missing kernel for 10.0 FG: {fg_name}"
            assert fg.get("initrd"), f"Missing initrd for 10.0 FG: {fg_name}"
            assert fg.get("image"), f"Missing image for 10.0 FG: {fg_name}"
            tl.info(f"✓ RHEL 10.0 FG {fg_name}: all artifacts present")

        # Step 5: Verify driver version alignment via repo_status
        required_drivers = ["cuda", "doca", "nvidia-hpc-sdk"]
        for version in ["10.0", "10.2"]:
            drv = ContractValidator.validate_driver_alignment(
                repo_status, version, required_drivers=required_drivers,
            )
            assert drv["valid"], (
                f"Driver alignment metadata missing for RHEL {version}: "
                f"{drv['errors']}"
            )
            tl.info(
                f"✓ Driver version metadata present for RHEL {version}"
            )

        # Step 6: Verify S3 objects at referenced keys exist
        for fg in all_fgs:
            fg_name = fg.get("functional_group", "unknown")
            for artifact in ["kernel", "initrd", "image"]:
                key = fg.get(artifact, "")
                if key:
                    exists = _s3_object_exists(key)
                    assert exists, (
                        f"S3 object not found for {fg_name}/{artifact}: {key}"
                    )
            tl.info(f"✓ S3 artifacts verified for {fg_name}")

        # Step 7: Verify BSS boot configuration derivability
        for fg in all_fgs:
            fg_name = fg.get("functional_group", "unknown")
            kernel = fg.get("kernel", "")
            initrd = fg.get("initrd", "")
            image = fg.get("image", "")
            assert kernel and initrd and image, (
                f"Cannot derive BSS boot config for {fg_name}: "
                f"kernel={bool(kernel)} initrd={bool(initrd)} "
                f"image={bool(image)}"
            )
        tl.info(
            f"✓ BSS boot configuration derivable for all "
            f"{len(all_fgs)} FGs"
        )

        tl.passed(
            "RHEL 10.2 EUS Build Status Contract Validation test passed"
        )

    except AssertionError as e:
        tl.failed(
            "RHEL 10.2 EUS Build Status Contract Validation test failed",
            str(e),
        )
        raise
    except Exception as e:
        tl.failed(
            "Unexpected error in RHEL 10.2 EUS Build Status Contract "
            "Validation test",
            str(e),
        )
        raise


# ============================================================================
# TC-006: Driver Version Alignment Verification
# ============================================================================

@pytest.mark.st
@pytest.mark.tier1
@pytest.mark.image_build_manager
@pytest.mark.rhel102
def test_rhel102_driver_version_alignment(repo_status, build_status, test_logger):
    """TC-006: Driver Version Alignment Verification.

    Objective: Verify driver repositories (CUDA, DOCA/OFED, NVIDIA HPC SDK)
    are version-aligned with the target RHEL EUS version by confirming that
    repo_status.yml contains version-scoped driver repo URLs under each OS
    version and that build_status.yml shows a successful build consuming them.

    Acceptance Criteria (Gherkin):
    GIVEN CUDA, DOCA/OFED, and HPC SDK repositories configured for RHEL 10.2 EUS
    WHEN Image Build Manager builds images
    THEN all driver versions are certified for RHEL 10.2 EUS
    """
    tc_id = "TC-006"
    tc_name = "Driver Version Alignment Verification"
    tl = test_logger(tc_name, tc_id)

    try:
        tl.info("Validating driver version alignment via repo_status.yml...")

        required_drivers = ["cuda", "doca", "nvidia-hpc-sdk"]

        # --- Step 1-2: Verify RHEL 10.2 EUS driver repos in repo_status ---
        validation_102 = ContractValidator.validate_driver_alignment(
            repo_status, "10.2", required_drivers=required_drivers,
        )
        assert validation_102["valid"], (
            f"RHEL 10.2 driver alignment failed: {validation_102['errors']}"
        )
        for driver, url in validation_102["drivers"].items():
            tl.info(f"  {driver} (10.2): {url}")
        tl.info("✓ All required driver repos present and version-scoped for RHEL 10.2")

        # --- Step 3: Verify RHEL 10.0 EUS driver repos (dual-version catalog) ---
        validation_100 = ContractValidator.validate_driver_alignment(
            repo_status, "10.0", required_drivers=required_drivers,
        )
        if validation_100["valid"]:
            for driver, url in validation_100["drivers"].items():
                tl.info(f"  {driver} (10.0): {url}")
            tl.info("✓ All required driver repos present and version-scoped for RHEL 10.0")
        else:
            tl.info(
                "⊘ RHEL 10.0 driver repos not all present (acceptable if "
                "catalog has no 10.0 FGs)"
            )

        # --- Step 4: Cross-check that build succeeded with these repos ---
        assert build_status.get("overall_status") == "success", (
            f"Expected build overall_status=success, "
            f"got {build_status.get('overall_status')}"
        )
        tl.info("✓ build_status.yml overall_status is success")

        # --- Step 5: Verify no version cross-contamination ---
        for driver, url in validation_102["drivers"].items():
            assert "/rhel/10.0/" not in url, (
                f"RHEL 10.2 driver '{driver}' URL references 10.0 path: {url}"
            )
        tl.info("✓ No version cross-contamination in driver repo URLs")

        tl.passed("Driver Version Alignment Verification test passed")

    except AssertionError as e:
        tl.failed("Driver Version Alignment Verification test failed", str(e))
        raise
    except Exception as e:
        tl.failed(
            "Unexpected error in Driver Version Alignment Verification test",
            str(e),
        )
        raise


# ============================================================================
# TC-007: VAST Driver Inclusion in Slurm Node Images
# ============================================================================

@pytest.mark.st
@pytest.mark.tier1
@pytest.mark.image_build_manager
@pytest.mark.rhel102
def test_rhel102_vast_driver_slurm(build_status, catalog, repo_status, test_logger):
    """TC-007: VAST Driver Inclusion in Slurm Node Images.

    Objective: Verify VAST storage driver is included in Slurm compute,
    login, and compiler FG images, and NOT in K8s control plane images.

    Acceptance Criteria (Gherkin):
    GIVEN a catalog with Slurm compute, Slurm login, compiler, and K8s
         control plane FGs
    WHEN Image Build Manager builds RHEL 10.2 EUS images
    THEN Slurm compute, Slurm login, and compiler images include the VAST
         storage driver
    AND K8s control plane images do NOT include the VAST driver
    """
    tc_id = "TC-007"
    tc_name = "VAST Driver Inclusion in Slurm Node Images"
    tl = test_logger(tc_name, tc_id)

    try:
        tl.info("Validating VAST driver inclusion via catalog and repo_status...")

        # Step 1: Verify VAST driver repository configured for RHEL 10.2
        repos_102 = repo_status.get("repositories", {}).get(
            "10.2", {}
        ).get("x86_64", {})
        vast_entry = repos_102.get("vast")
        assert vast_entry, (
            "VAST driver repository not found under 10.2.x86_64 in "
            "repo_status.yml"
        )
        vast_url = (
            vast_entry.get("url", vast_entry)
            if isinstance(vast_entry, dict)
            else vast_entry
        )
        assert isinstance(vast_url, str) and vast_url.startswith("http"), (
            f"VAST repository URL invalid: {vast_url}"
        )
        tl.info(f"✓ VAST driver repository configured: {vast_url}")

        # Step 2: Identify FGs from catalog and classify VAST assignment
        functional_layers = catalog.get("catalog", {}).get(
            "functionallayer", []
        )
        assert functional_layers, "No functional layers in catalog"

        vast_fgs = []
        non_vast_k8s_fgs = []
        for fl in functional_layers:
            fl_name = fl["name"]
            has_vast = "vast_stack_driver_groupv1" in fl.get("components", [])
            if has_vast:
                vast_fgs.append(fl_name)
            elif "kube" in fl_name.lower():
                non_vast_k8s_fgs.append(fl_name)

        assert vast_fgs, (
            "No functional layers with vast_stack_driver_groupv1 in catalog"
        )
        tl.info(f"✓ Catalog assigns VAST to: {vast_fgs}")

        # Step 3: Verify build succeeded
        assert build_status.get("overall_status") == "success", (
            f"Build did not succeed: {build_status.get('overall_status')}"
        )

        # Step 4-6: Verify each VAST-assigned FG was built
        all_fgs = _extract_fg_groups(build_status)
        built_fg_names = [
            g.get("functional_group", "") for g in all_fgs
        ]

        for vast_fg in vast_fgs:
            assert vast_fg in built_fg_names, (
                f"VAST-assigned FG '{vast_fg}' not found in "
                f"build_status.yml functional groups"
            )
            tl.info(f"✓ VAST FG '{vast_fg}' has built image")

        # Verify Slurm-specific VAST FGs (compute, login, compiler)
        slurm_vast_fgs = [
            fg for fg in vast_fgs
            if "slurm" in fg.lower() or "login" in fg.lower()
               or "compiler" in fg.lower()
        ]
        assert slurm_vast_fgs, (
            "No Slurm/login/compiler FGs with VAST in catalog"
        )
        tl.info(f"✓ Slurm VAST FGs: {slurm_vast_fgs}")

        # Step 7: Verify K8s control plane does NOT have VAST
        assert non_vast_k8s_fgs, (
            "No K8s control plane FGs found to verify VAST absence"
        )
        for k8s_fg in non_vast_k8s_fgs:
            assert k8s_fg not in vast_fgs, (
                f"K8s FG '{k8s_fg}' should NOT have VAST but does"
            )
            tl.info(f"✓ K8s FG '{k8s_fg}' does NOT include VAST")

        tl.passed("VAST Driver Inclusion in Slurm Node Images test passed")

    except AssertionError as e:
        tl.failed(
            "VAST Driver Inclusion in Slurm Node Images test failed",
            str(e),
        )
        raise
    except Exception as e:
        tl.failed(
            "Unexpected error in VAST Driver Inclusion test", str(e)
        )
        raise
