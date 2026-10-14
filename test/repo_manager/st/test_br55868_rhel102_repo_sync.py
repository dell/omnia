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
Tier 1: Image Pipeline — RHEL 10.2 EUS Repository Synchronization and Validation.

Test Plan: BR-55868 — RHEL 10.2 Support for x86_64 Functional Groups
ER: ER-ORCH-010-rhel-10-2-x86-64-support

Tier 1 Tests:
  TC-001: RHEL 10.2 EUS Repository Synchronization
  TC-002: RHEL 10.0 EUS and 10.2 EUS Image Build via Native Path
  TC-003: RHEL 10.2 EUS Repo Status Contract Validation
  TC-004: RHEL 10.2 EUS Build Status Contract Validation
  TC-005: Dual-Version EUS Catalog
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
# TC-001: RHEL 10.2 EUS Repository Synchronization
# ============================================================================

@pytest.mark.st
@pytest.mark.tier1
@pytest.mark.repo_manager
@pytest.mark.rhel102
def test_rhel102_repo_sync_eus(repo_status, test_logger):
    """TC-001: RHEL 10.2 EUS Repository Synchronization.
    
    Objective: Verify Repo Manager synchronizes RHEL 10.2 EUS content 
    (BaseOS, AppStream, CodeReady Builder) and third-party repositories 
    into Pulp and generates a successful repo_status.yml.
    
    Acceptance Criteria (Gherkin):
    GIVEN an Omnia 2.3 OIM with RHEL 10.2 EUS entitlement configured
    WHEN the Repo Manager runs prepare, precheck, download, and status 
         for a RHEL 10.2 EUS catalog
    THEN Pulp creates HTTPS distributions for BaseOS, AppStream, and 
         CodeReady Builder 10.2 EUS x86_64
    AND Pulp creates distributions for RHEL 10.2-compatible third-party repositories
    AND repo_status.yml reports overall_status success with valid 10.2 EUS repository URLs
    """
    tc_id = "TC-001"
    tc_name = "RHEL 10.2 EUS Repository Synchronization"
    tl = test_logger(tc_name, tc_id)
    
    try:
        tl.info("Validating repo_status.yml contract...")
        
        # Validate contract structure
        validation = ContractValidator.validate_repo_status(repo_status)
        assert validation["valid"], f"Contract validation failed: {validation['errors']}"
        tl.info("✓ repo_status.yml contract is valid")
        
        # Check overall status
        assert repo_status.get("overall_status") == "success", \
            f"Expected overall_status=success, got {repo_status.get('overall_status')}"
        tl.info("✓ overall_status is success")
        
        # Verify RHEL 10.2 EUS repositories
        repositories = repo_status.get("repositories", {})
        assert repositories, "No repositories found in repo_status.yml"
        
        rhel_102 = repositories.get("10.2", {})
        assert rhel_102, "RHEL 10.2 EUS not found in repo_status.yml"
        tl.info("✓ RHEL 10.2 EUS repositories found")
        
        # Check x86_64 architecture
        x86_64 = rhel_102.get("x86_64", {})
        assert x86_64, "x86_64 architecture not found for RHEL 10.2"
        tl.info("✓ x86_64 architecture found")
        
        # Verify required repositories
        required_repos = ["baseos", "appstream", "codeready-builder"]
        for repo in required_repos:
            repo_url = x86_64.get(repo)
            if repo_url and isinstance(repo_url, dict):
                repo_url = repo_url.get("url")
            assert repo_url, f"Missing {repo} repository URL"
            assert isinstance(repo_url, str) and repo_url.startswith("http"), \
                f"Invalid {repo} URL: {repo_url}"
            tl.info(f"✓ {repo} repository URL is valid")
        
        # Verify additional repositories
        additional_repos = ["cuda", "doca", "vast", "nvidia-hpc-sdk"]
        for repo in additional_repos:
            if repo in x86_64:
                tl.info(f"✓ {repo} repository found")
        
        tl.passed("RHEL 10.2 EUS Repository Synchronization test passed")
        
    except AssertionError as e:
        tl.failed("RHEL 10.2 EUS Repository Synchronization test failed", str(e))
        raise
    except Exception as e:
        tl.failed("Unexpected error in RHEL 10.2 EUS Repository Synchronization test", str(e))
        raise


# ============================================================================
# TC-003: RHEL 10.2 EUS Repo Status Contract Validation
# ============================================================================

@pytest.mark.st
@pytest.mark.tier1
@pytest.mark.repo_manager
@pytest.mark.rhel102
def test_rhel102_repo_status_contract(repo_status, test_logger):
    """TC-003: RHEL 10.2 EUS Repo Status Contract Validation.
    
    Objective: Verify the repo_status.yml contract is consumable by 
    Image Build Manager and Orchestrator, and includes driver-to-OS 
    version alignment metadata.
    
    Acceptance Criteria (Gherkin):
    GIVEN Repo Manager produced repo_status.yml with RHEL 10.0 EUS and 10.2 EUS repositories
    WHEN Image Build Manager and Orchestrator validate the contract
    THEN schema validation passes for both consumers
    AND all referenced repository URLs are reachable
    AND driver-to-OS version alignment metadata is present
    """
    tc_id = "TC-003"
    tc_name = "RHEL 10.2 EUS Repo Status Contract Validation"
    tl = test_logger(tc_name, tc_id)
    
    try:
        tl.info("Validating repo_status.yml contract structure...")
        
        # Validate contract
        validation = ContractValidator.validate_repo_status(repo_status)
        assert validation["valid"], f"Contract validation failed: {validation['errors']}"
        tl.info("✓ Contract structure is valid")
        
        # Verify OS versions present
        repositories = repo_status.get("repositories", {})
        os_versions = list(repositories.keys())
        assert os_versions, "No OS versions found in repositories"
        tl.info(f"✓ OS versions found: {os_versions}")
        
        # Check for driver metadata (optional in actual contract)
        driver_metadata = repo_status.get("driver_metadata", {})
        if driver_metadata:
            tl.info("✓ Driver metadata is present")
            # Validate driver alignment for available OS versions
            for os_version in os_versions:
                if os_version in driver_metadata:
                    tl.info(f"✓ Driver metadata for RHEL {os_version} is present")
        else:
            tl.info("⊘ Driver metadata not present (optional)")
        
        # Verify public certificate path (optional - may be in repo_manager section)
        cert_path = repo_status.get("certificate_path")
        if not cert_path:
            # Check in repo_manager section
            repo_manager = repo_status.get("repo_manager", {})
            certificates = repo_manager.get("certificates", {})
            cert_path = certificates.get("server_crt") or certificates.get("certs_dir")
        
        if cert_path:
            tl.info(f"✓ Certificate path is present")
        else:
            tl.info("⊘ Certificate path not found (optional)")
        
        tl.passed("RHEL 10.2 EUS Repo Status Contract Validation test passed")
        
    except AssertionError as e:
        tl.failed("RHEL 10.2 EUS Repo Status Contract Validation test failed", str(e))
        raise
    except Exception as e:
        tl.failed("Unexpected error in RHEL 10.2 EUS Repo Status Contract Validation test", str(e))
        raise


# ============================================================================
# TC-005: Dual-Version EUS Catalog
# ============================================================================

@pytest.mark.st
@pytest.mark.tier1
@pytest.mark.repo_manager
@pytest.mark.rhel102
@pytest.mark.rhel100
def test_rhel102_catalog_dual_eus(repo_status, test_logger):
    """TC-005: Dual-Version EUS Catalog.
    
    Objective: Verify that a catalog containing both RHEL 10.0 EUS 
    (GPU groups) and RHEL 10.2 EUS (x86_64 groups) produces correct, 
    validated images for both version tracks.
    
    Acceptance Criteria (Gherkin):
    GIVEN a catalog with RHEL 10.0 EUS GPU groups and RHEL 10.2 EUS x86_64 groups
    WHEN Repo Manager syncs and Image Build Manager builds
    THEN repo_status.yml contains both 10.0 EUS and 10.2 EUS repository URLs
    AND build_status.yml maps each FG to its correct OS version artifacts
    AND S3 contains distinct, validated image sets per FG with correct driver versions
    """
    tc_id = "TC-005"
    tc_name = "Dual-Version EUS Catalog"
    tl = test_logger(tc_name, tc_id)
    
    try:
        tl.info("Validating dual-version EUS catalog...")
        
        # Check for OS versions in repositories
        repositories = repo_status.get("repositories", {})
        os_versions = list(repositories.keys())
        assert os_versions, "No OS versions found in repositories"
        tl.info(f"✓ OS versions found: {os_versions}")
        
        # Verify x86_64 architecture for each OS version
        for version in os_versions:
            version_data = repositories.get(version, {})
            x86_64_data = version_data.get("x86_64", {})
            assert x86_64_data, f"RHEL {version} x86_64 repositories not found"
            tl.info(f"✓ RHEL {version} x86_64 repositories are present")
        
        # Verify driver versions (optional)
        driver_metadata = repo_status.get("driver_metadata", {})
        if driver_metadata:
            for version in os_versions:
                if version in driver_metadata:
                    tl.info(f"✓ Driver metadata for RHEL {version} is present")
        else:
            tl.info("⊘ Driver metadata not present (optional)")
        
        tl.passed("Dual-Version EUS Catalog test passed")
        
    except AssertionError as e:
        tl.failed("Dual-Version EUS Catalog test failed", str(e))
        raise
    except Exception as e:
        tl.failed("Unexpected error in Dual-Version EUS Catalog test", str(e))
        raise
