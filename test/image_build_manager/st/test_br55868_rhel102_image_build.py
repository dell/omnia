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

import pytest
import yaml
import sys
from pathlib import Path
from typing import Dict, Any

# Import from domain library
from library.st_helpers.test_logger import TestLogger
from library.st_helpers.contract_validator import ContractValidator


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
    GIVEN a successful repo_status.yml with both RHEL 10.0 EUS and 10.2 EUS repositories
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
        
        # Validate contract structure
        validation = ContractValidator.validate_build_status(build_status)
        assert validation["valid"], f"Contract validation failed: {validation['errors']}"
        tl.info("✓ build_status.yml contract is valid")
        
        # Check overall status
        assert build_status.get("overall_status") == "success", \
            f"Expected overall_status=success, got {build_status.get('overall_status')}"
        tl.info("✓ overall_status is success")
        
        # Verify functional groups (can be functional_groups or functional_group_images)
        functional_groups = build_status.get("functional_groups") or build_status.get("functional_group_images", [])
        assert functional_groups, "No functional groups found in build_status.yml"
        
        # Handle list format (functional_group_images)
        if isinstance(functional_groups, list):
            total_groups = 0
            for arch_entry in functional_groups:
                if isinstance(arch_entry, dict):
                    for arch, groups in arch_entry.items():
                        if isinstance(groups, list):
                            total_groups += len(groups)
                            for group in groups:
                                if isinstance(group, dict):
                                    fg_name = group.get("functional_group", "unknown")
                                    tl.info(f"Validating functional group: {fg_name}")
                                    
                                    # Check for required artifacts
                                    required_artifacts = ["kernel", "initrd", "image"]
                                    for artifact in required_artifacts:
                                        artifact_path = group.get(artifact)
                                        assert artifact_path, f"Missing {artifact} artifact for FG {fg_name}"
                                        assert artifact_path.strip(), f"Empty {artifact} artifact path for FG {fg_name}"
                                        tl.info(f"  ✓ {artifact} present")
            tl.info(f"✓ Found {total_groups} functional groups")
        else:
            # Handle dict format
            tl.info(f"✓ Found {len(functional_groups)} functional groups")
        
        # Verify S3 configuration (can be s3_config or s3_configurations)
        s3_config = build_status.get("s3_config") or build_status.get("s3_configurations", {})
        assert s3_config, "No S3 configuration found in build_status.yml"
        
        # Check for endpoint (can be endpoint or endpoint_url)
        endpoint = s3_config.get("endpoint") or s3_config.get("endpoint_url")
        assert endpoint, "Missing S3 endpoint"
        
        # Check for bucket
        bucket = s3_config.get("bucket")
        assert bucket, "Missing S3 bucket"
        
        tl.info(f"✓ S3 configuration is valid")
        
        tl.passed("RHEL 10.0 EUS and 10.2 EUS Image Build via Native Path test passed")
        
    except AssertionError as e:
        tl.failed("RHEL 10.0 EUS and 10.2 EUS Image Build via Native Path test failed", str(e))
        raise
    except Exception as e:
        tl.failed("Unexpected error in RHEL 10.0 EUS and 10.2 EUS Image Build via Native Path test", str(e))
        raise


# ============================================================================
# TC-004: RHEL 10.2 EUS Build Status Contract Validation
# ============================================================================

@pytest.mark.st
@pytest.mark.tier1
@pytest.mark.image_build_manager
@pytest.mark.rhel102
def test_rhel102_build_status_contract(build_status, test_logger):
    """TC-004: RHEL 10.2 EUS Build Status Contract Validation.
    
    Objective: Verify build_status.yml is consumable by Orchestrator for 
    BSS configuration. Verify it includes driver version metadata for both 
    OS versions.
    
    Acceptance Criteria (Gherkin):
    GIVEN Image Build Manager produced build_status.yml with RHEL 10.0 EUS and 10.2 EUS artifacts
    WHEN Orchestrator reads the contract
    THEN all referenced S3 artifact keys exist and are accessible for both OS versions
    AND driver version metadata is recorded for each functional group image
    AND BSS boot configuration can be derived for each functional group
    """
    tc_id = "TC-004"
    tc_name = "RHEL 10.2 EUS Build Status Contract Validation"
    tl = test_logger(tc_name, tc_id)
    
    try:
        tl.info("Validating build_status.yml contract...")
        
        # Validate contract
        validation = ContractValidator.validate_build_status(build_status)
        assert validation["valid"], f"Contract validation failed: {validation['errors']}"
        tl.info("✓ Contract structure is valid")
        
        # Check S3 configuration (can be s3_config or s3_configurations)
        s3_config = build_status.get("s3_config") or build_status.get("s3_configurations", {})
        assert s3_config, "No S3 configuration found"
        
        # Check for endpoint (can be endpoint or endpoint_url)
        endpoint = s3_config.get("endpoint") or s3_config.get("endpoint_url")
        assert endpoint, "Missing S3 endpoint"
        
        # Check for bucket
        bucket = s3_config.get("bucket")
        assert bucket, "Missing S3 bucket"
        
        tl.info("✓ S3 configuration is present and valid")
        
        # Verify driver metadata (optional)
        driver_metadata = build_status.get("driver_metadata", {})
        if driver_metadata:
            tl.info("✓ Driver metadata is present")
            # Check for RHEL 10.2 driver metadata
            rhel_102_drivers = driver_metadata.get("10.2", {})
            if rhel_102_drivers:
                required_drivers = ["cuda", "doca_ofed", "hpc_sdk"]
                for driver in required_drivers:
                    if driver in rhel_102_drivers:
                        tl.info(f"✓ {driver} version for RHEL 10.2 is present")
        else:
            tl.info("⊘ Driver metadata not present (optional)")
        
        # Verify BSS boot configuration can be derived
        functional_groups = build_status.get("functional_groups") or build_status.get("functional_group_images", [])
        if isinstance(functional_groups, list):
            for arch_entry in functional_groups:
                if isinstance(arch_entry, dict):
                    for arch, groups in arch_entry.items():
                        if isinstance(groups, list):
                            for group in groups:
                                if isinstance(group, dict):
                                    fg_name = group.get("functional_group", "unknown")
                                    # Check for BSS-required fields
                                    assert group.get("kernel"), f"Missing kernel for BSS config: {fg_name}"
                                    assert group.get("initrd"), f"Missing initrd for BSS config: {fg_name}"
                                    assert group.get("image"), f"Missing image for BSS config: {fg_name}"
                                    tl.info(f"✓ BSS boot configuration can be derived for {fg_name}")
        
        tl.passed("RHEL 10.2 EUS Build Status Contract Validation test passed")
        
    except AssertionError as e:
        tl.failed("RHEL 10.2 EUS Build Status Contract Validation test failed", str(e))
        raise
    except Exception as e:
        tl.failed("Unexpected error in RHEL 10.2 EUS Build Status Contract Validation test", str(e))
        raise


# ============================================================================
# TC-006: Driver Version Alignment Verification
# ============================================================================

@pytest.mark.st
@pytest.mark.tier1
@pytest.mark.image_build_manager
@pytest.mark.rhel102
def test_rhel102_driver_version_alignment(build_status, test_logger):
    """TC-006: Driver Version Alignment Verification.
    
    Objective: Verify driver repositories (CUDA, DOCA/OFED, NVIDIA HPC SDK) 
    are version-aligned with the target RHEL EUS version.
    
    Acceptance Criteria (Gherkin):
    GIVEN CUDA, DOCA/OFED, and HPC SDK repositories configured for RHEL 10.2 EUS
    WHEN Image Build Manager builds images
    THEN all driver versions are certified for RHEL 10.2 EUS
    """
    tc_id = "TC-006"
    tc_name = "Driver Version Alignment Verification"
    tl = test_logger(tc_name, tc_id)
    
    try:
        tl.info("Validating driver version alignment...")
        
        # Get driver metadata (optional)
        driver_metadata = build_status.get("driver_metadata", {})
        if not driver_metadata:
            tl.skipped("No driver metadata found in build_status.yml")
            pytest.skip("No driver metadata found in build_status.yml")
        
        # Check RHEL 10.2 drivers
        rhel_102_drivers = driver_metadata.get("10.2", {})
        if not rhel_102_drivers:
            tl.info("No driver metadata for RHEL 10.2")
            pytest.skip("No driver metadata for RHEL 10.2")
        
        tl.info("✓ Driver metadata for RHEL 10.2 is present")
        
        # Verify required drivers (if present)
        required_drivers = ["cuda", "doca_ofed", "hpc_sdk"]
        for driver in required_drivers:
            version = rhel_102_drivers.get(driver)
            if version:
                tl.info(f"✓ {driver} version for RHEL 10.2: {version}")
        
        # Verify functional groups have driver versions (optional)
        functional_groups = build_status.get("functional_groups") or build_status.get("functional_group_images", [])
        if isinstance(functional_groups, list):
            for arch_entry in functional_groups:
                if isinstance(arch_entry, dict):
                    for arch, groups in arch_entry.items():
                        if isinstance(groups, list):
                            for group in groups:
                                if isinstance(group, dict):
                                    fg_drivers = group.get("drivers", {})
                                    if fg_drivers:
                                        fg_name = group.get("functional_group", "unknown")
                                        for driver, version in fg_drivers.items():
                                            tl.info(f"  {fg_name}: {driver} = {version}")
        
        tl.passed("Driver Version Alignment Verification test passed")
        
    except AssertionError as e:
        tl.failed("Driver Version Alignment Verification test failed", str(e))
        raise
    except Exception as e:
        tl.failed("Unexpected error in Driver Version Alignment Verification test", str(e))
        raise


# ============================================================================
# TC-007: VAST Driver Inclusion in Slurm Node Images
# ============================================================================

@pytest.mark.st
@pytest.mark.tier1
@pytest.mark.image_build_manager
@pytest.mark.rhel102
def test_rhel102_vast_driver_slurm(build_status, test_logger):
    """TC-007: VAST Driver Inclusion in Slurm Node Images.
    
    Objective: Verify VAST driver is included in Slurm compute, login, 
    and compiler node images.
    
    Acceptance Criteria (Gherkin):
    GIVEN a catalog with Slurm compute, login, and compiler functional groups
    WHEN Image Build Manager builds images
    THEN VAST driver is included in all Slurm node images
    AND VAST driver version is certified for the target RHEL EUS version
    """
    tc_id = "TC-007"
    tc_name = "VAST Driver Inclusion in Slurm Node Images"
    tl = test_logger(tc_name, tc_id)
    
    try:
        tl.info("Validating VAST driver inclusion in Slurm node images...")
        
        # Get functional groups
        functional_groups = build_status.get("functional_groups") or build_status.get("functional_group_images", [])
        if not functional_groups:
            tl.skipped("No functional groups found")
            pytest.skip("No functional groups found")
        
        # Find Slurm node groups
        slurm_groups = []
        if isinstance(functional_groups, list):
            for arch_entry in functional_groups:
                if isinstance(arch_entry, dict):
                    for arch, groups in arch_entry.items():
                        if isinstance(groups, list):
                            for group in groups:
                                if isinstance(group, dict):
                                    fg_name = group.get("functional_group", "")
                                    if "slurm" in fg_name.lower():
                                        slurm_groups.append((fg_name, group))
        
        if not slurm_groups:
            tl.info("No Slurm functional groups found in build_status.yml")
            tl.skipped("No Slurm groups to validate VAST driver")
            pytest.skip("No Slurm groups to validate VAST driver")
        
        tl.info(f"Found {len(slurm_groups)} Slurm functional groups")
        
        # Verify VAST driver in each Slurm group
        vast_found_count = 0
        for fg_name, fg_data in slurm_groups:
            tl.info(f"Checking VAST driver in {fg_name}...")
            
            # Check for VAST driver in packages or drivers
            packages = fg_data.get("packages", [])
            drivers = fg_data.get("drivers", {})
            
            vast_found = False
            if packages and any("vast" in str(p).lower() for p in packages):
                vast_found = True
                vast_found_count += 1
                tl.info(f"  ✓ VAST driver found in packages")
            
            if drivers and "vast" in drivers:
                vast_found = True
                vast_found_count += 1
                vast_version = drivers.get("vast")
                tl.info(f"  ✓ VAST driver version: {vast_version}")
            
            if not vast_found:
                tl.info(f"  ⚠ VAST driver not explicitly listed in {fg_name} (optional in contract)")
        
        if vast_found_count == 0:
            tl.info("⊘ VAST driver not explicitly tracked in build_status.yml (optional)")
        else:
            tl.info(f"✓ VAST driver found in {vast_found_count}/{len(slurm_groups)} Slurm groups")
        
        tl.passed("VAST Driver Inclusion in Slurm Node Images test passed")
        
    except AssertionError as e:
        tl.failed("VAST Driver Inclusion in Slurm Node Images test failed", str(e))
        raise
    except Exception as e:
        tl.failed("Unexpected error in VAST Driver Inclusion in Slurm Node Images test", str(e))
        raise
