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
  TC-003: RHEL 10.2 EUS Repo Status Contract Validation
  TC-005: Dual-Version EUS Catalog
"""

import os
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


def _s3_object_exists(s3_key: str, endpoint: str, bucket: str) -> bool:
    """Check if an S3 object exists using s3cmd."""
    s3_uri = f"s3://{bucket}/{s3_key}" if not s3_key.startswith("s3://") else s3_key
    # Normalise: if key already starts with bucket name, strip it
    if s3_uri.startswith(f"s3://{bucket}/{bucket}/"):
        s3_uri = f"s3://{bucket}/{s3_key[len(bucket)+1:]}"
    try:
        result = subprocess.run(
            ["s3cmd", "ls", s3_uri],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0 and len(result.stdout.strip()) > 0
    except Exception:
        return False


# ============================================================================
# TC-001: RHEL 10.2 EUS Repository Synchronization
# ============================================================================

@pytest.mark.st
@pytest.mark.tier1
@pytest.mark.repo_manager
@pytest.mark.rhel102
def test_rhel102_repo_sync_eus(repo_status, repo_status_path, test_logger):
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
    AND Pulp creates distributions for RHEL 10.2-compatible third-party repos
    AND repo_status.yml reports overall_status success with valid 10.2 EUS URLs
    """
    tc_id = "TC-001"
    tc_name = "RHEL 10.2 EUS Repository Synchronization"
    tl = test_logger(tc_name, tc_id)

    try:
        tl.info("Validating repo_status.yml contract...")

        # Step 1-4: Validate contract structure and overall status
        validation = ContractValidator.validate_repo_status(repo_status)
        assert validation["valid"], (
            f"Contract validation failed: {validation['errors']}"
        )
        tl.info("✓ repo_status.yml contract structure is valid")

        assert repo_status.get("overall_status") == "success", (
            f"Expected overall_status=success, "
            f"got {repo_status.get('overall_status')}"
        )
        tl.info("✓ overall_status is success")

        # Step 5: Verify RHEL 10.2 EUS repositories with HTTPS URLs
        repositories = repo_status.get("repositories", {})
        assert repositories, "No repositories found in repo_status.yml"

        rhel_102 = repositories.get("10.2", {})
        assert rhel_102, "RHEL 10.2 EUS not found in repo_status.yml"
        tl.info("✓ RHEL 10.2 EUS repositories found")

        x86_64 = rhel_102.get("x86_64", {})
        assert x86_64, "x86_64 architecture not found for RHEL 10.2"
        tl.info("✓ x86_64 architecture found")

        required_repos = ["baseos", "appstream", "codeready-builder"]
        for repo in required_repos:
            repo_entry = x86_64.get(repo)
            assert repo_entry, f"Missing {repo} repository"
            repo_url = (
                repo_entry.get("url", repo_entry)
                if isinstance(repo_entry, dict)
                else repo_entry
            )
            assert isinstance(repo_url, str) and repo_url.startswith("https"), (
                f"{repo} URL must start with https, got: {repo_url}"
            )
            tl.info(f"✓ {repo} repository URL is valid HTTPS")

        # Step 6: Verify third-party Pulp distributions exist (asserted)
        third_party_repos = ["epel", "kubernetes-v1-35", "cri-o-v1-35"]
        for repo in third_party_repos:
            repo_entry = x86_64.get(repo)
            assert repo_entry, (
                f"Missing third-party repository: {repo} under 10.2.x86_64"
            )
            repo_url = (
                repo_entry.get("url", repo_entry)
                if isinstance(repo_entry, dict)
                else repo_entry
            )
            assert isinstance(repo_url, str) and repo_url.startswith("http"), (
                f"Third-party {repo} URL invalid: {repo_url}"
            )
            tl.info(f"✓ Third-party {repo} repository present")

        # Step 7: Verify additional driver repositories
        driver_repos = ["cuda", "doca", "vast", "nvidia-hpc-sdk"]
        for repo in driver_repos:
            if repo in x86_64:
                tl.info(f"✓ {repo} repository found")

        # Step 8: Verify file permissions (0644)
        stat_info = repo_status_path.stat()
        file_mode = oct(stat_info.st_mode)[-3:]
        assert file_mode == "644", (
            f"repo_status.yml permissions should be 644, got {file_mode}"
        )
        tl.info("✓ repo_status.yml file permissions are 644")

        tl.passed("RHEL 10.2 EUS Repository Synchronization test passed")

    except AssertionError as e:
        tl.failed("RHEL 10.2 EUS Repository Synchronization test failed", str(e))
        raise
    except Exception as e:
        tl.failed(
            "Unexpected error in RHEL 10.2 EUS Repository Synchronization test",
            str(e),
        )
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
    GIVEN Repo Manager produced repo_status.yml with RHEL 10.0 EUS and
         10.2 EUS repositories
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

        # Step 1: Validate contract structure
        validation = ContractValidator.validate_repo_status(repo_status)
        assert validation["valid"], (
            f"Contract validation failed: {validation['errors']}"
        )
        tl.info("✓ Contract structure is valid")

        # Step 1 continued: Verify cluster_os_type
        assert repo_status.get("cluster_os_type") == "rhel", (
            f"Expected cluster_os_type=rhel, "
            f"got {repo_status.get('cluster_os_type')}"
        )
        tl.info("✓ cluster_os_type is rhel")

        # Step 1 continued: Verify both 10.0 and 10.2 version keys present
        repositories = repo_status.get("repositories", {})
        os_versions = list(repositories.keys())
        assert "10.0" in os_versions, "RHEL 10.0 EUS not found in repositories"
        assert "10.2" in os_versions, "RHEL 10.2 EUS not found in repositories"
        tl.info(f"✓ Both 10.0 and 10.2 version keys present: {os_versions}")

        # Step 3: Verify 10.2.x86_64 has BaseOS, AppStream, CRB URLs
        x86_64_102 = repositories.get("10.2", {}).get("x86_64", {})
        assert x86_64_102, "No x86_64 repos under 10.2"
        required_repos = ["baseos", "appstream", "codeready-builder"]
        for repo in required_repos:
            entry = x86_64_102.get(repo)
            assert entry, f"Missing {repo} under 10.2.x86_64"
            url = (
                entry.get("url", entry) if isinstance(entry, dict) else entry
            )
            assert isinstance(url, str) and url.startswith("https"), (
                f"{repo} URL must be HTTPS, got: {url}"
            )
            tl.info(f"✓ 10.2.x86_64.{repo} URL is valid HTTPS")

        # Step 4: Verify driver-to-OS version alignment metadata
        # Driver alignment is encoded via version-scoped repo URLs
        required_drivers = ["cuda", "doca", "nvidia-hpc-sdk"]
        driver_validation = ContractValidator.validate_driver_alignment(
            repo_status, "10.2", required_drivers=required_drivers,
        )
        assert driver_validation["valid"], (
            f"Driver alignment metadata missing for RHEL 10.2: "
            f"{driver_validation['errors']}"
        )
        for driver, url in driver_validation["drivers"].items():
            tl.info(f"✓ Driver {driver} version-scoped for 10.2: {url}")
        tl.info("✓ Driver-to-OS version alignment metadata is present")

        # Step 5: Verify public certificate path exists on filesystem
        rm_section = repo_status.get("repo_manager", {})
        certificates = rm_section.get("certificates", {})
        cert_path = certificates.get("server_crt") or certificates.get(
            "certs_dir"
        )
        assert cert_path, (
            "Certificate path not found in repo_status.yml "
            "repo_manager.certificates"
        )
        assert Path(cert_path).exists(), (
            f"Certificate path does not exist on filesystem: {cert_path}"
        )
        tl.info(f"✓ Certificate path exists: {cert_path}")

        # Step 6-7: Contract is consumable by downstream domains
        # Verify the contract has all keys that Image Build Manager and
        # Orchestrator require (overall_status, repositories with URLs,
        # certificates)
        assert repo_status.get("overall_status") in ("success", "partial"), (
            f"Contract overall_status not consumable: "
            f"{repo_status.get('overall_status')}"
        )
        tl.info("✓ Contract is consumable by downstream domains")

        tl.passed("RHEL 10.2 EUS Repo Status Contract Validation test passed")

    except AssertionError as e:
        tl.failed(
            "RHEL 10.2 EUS Repo Status Contract Validation test failed",
            str(e),
        )
        raise
    except Exception as e:
        tl.failed(
            "Unexpected error in RHEL 10.2 EUS Repo Status Contract "
            "Validation test",
            str(e),
        )
        raise


# ============================================================================
# TC-005: Dual-Version EUS Catalog
# ============================================================================

@pytest.mark.st
@pytest.mark.tier1
@pytest.mark.repo_manager
@pytest.mark.rhel102
@pytest.mark.rhel100
def test_rhel102_catalog_dual_eus(
    repo_status, build_status, catalog, test_logger
):
    """TC-005: Dual-Version EUS Catalog.

    Objective: Verify that a catalog containing both RHEL 10.0 EUS
    (GPU groups) and RHEL 10.2 EUS (x86_64 groups) produces correct,
    validated images for both version tracks.

    Acceptance Criteria (Gherkin):
    GIVEN a catalog with RHEL 10.0 EUS GPU groups and RHEL 10.2 EUS
         x86_64 groups
    WHEN Repo Manager syncs and Image Build Manager builds
    THEN repo_status.yml contains both 10.0 EUS and 10.2 EUS repo URLs
    AND build_status.yml maps each FG to its correct OS version artifacts
    AND S3 contains distinct, validated image sets per FG with correct
        driver versions
    """
    tc_id = "TC-005"
    tc_name = "Dual-Version EUS Catalog"
    tl = test_logger(tc_name, tc_id)

    try:
        tl.info("Validating dual-version EUS catalog...")

        # Step 1: Verify catalog has both 10.0 and 10.2 FGs
        functional_layers = catalog.get("catalog", {}).get(
            "functionallayer", []
        )
        assert functional_layers, "No functional layers found in catalog"

        fg_100 = [
            fl["name"]
            for fl in functional_layers
            if "10_0" in fl["name"]
        ]
        fg_102 = [
            fl["name"]
            for fl in functional_layers
            if "10_2" in fl["name"]
        ]
        assert fg_100, "No RHEL 10.0 functional groups found in catalog"
        assert fg_102, "No RHEL 10.2 functional groups found in catalog"
        tl.info(
            f"✓ Catalog has {len(fg_100)} RHEL 10.0 FGs and "
            f"{len(fg_102)} RHEL 10.2 FGs"
        )

        # Step 2-3: Verify repo_status.yml contains both version keys
        repositories = repo_status.get("repositories", {})
        assert "10.0" in repositories, (
            "RHEL 10.0 not found in repo_status.yml"
        )
        assert "10.2" in repositories, (
            "RHEL 10.2 not found in repo_status.yml"
        )
        tl.info("✓ repo_status.yml contains both 10.0 and 10.2 versions")

        # Verify x86_64 repos for each version
        for version in ["10.0", "10.2"]:
            x86_64_repos = repositories.get(version, {}).get("x86_64", {})
            assert x86_64_repos, (
                f"RHEL {version} x86_64 repositories not found"
            )
            tl.info(f"✓ RHEL {version} x86_64 repositories present")

        # Step 4-5: Verify build_status.yml has FGs for both versions
        assert build_status.get("overall_status") == "success", (
            f"build_status overall_status is not success: "
            f"{build_status.get('overall_status')}"
        )

        all_fgs = _extract_fg_groups(build_status)
        assert all_fgs, "No functional groups found in build_status.yml"

        built_100 = [
            g["functional_group"]
            for g in all_fgs
            if "10_0" in g.get("functional_group", "")
        ]
        built_102 = [
            g["functional_group"]
            for g in all_fgs
            if "10_2" in g.get("functional_group", "")
        ]
        assert built_100, (
            "No RHEL 10.0 FGs in build_status.yml"
        )
        assert built_102, (
            "No RHEL 10.2 FGs in build_status.yml"
        )
        tl.info(
            f"✓ build_status.yml has {len(built_100)} 10.0 FGs and "
            f"{len(built_102)} 10.2 FGs"
        )

        # Step 6: Verify artifact paths are distinct per OS version
        for fg in all_fgs:
            fg_name = fg.get("functional_group", "")
            img_path = fg.get("image", "")
            if "10_0" in fg_name:
                assert "10.2" not in img_path and "10_2" not in img_path, (
                    f"10.0 FG '{fg_name}' has 10.2 artifact path: {img_path}"
                )
            elif "10_2" in fg_name:
                assert "10.0" not in img_path and "10_0" not in img_path, (
                    f"10.2 FG '{fg_name}' has 10.0 artifact path: {img_path}"
                )
        tl.info("✓ Artifact paths are distinct per OS version")

        # Step 7-8: Verify driver repos are version-scoped for both
        required_drivers = ["cuda", "doca", "nvidia-hpc-sdk"]
        for version in ["10.0", "10.2"]:
            drv = ContractValidator.validate_driver_alignment(
                repo_status, version, required_drivers=required_drivers,
            )
            assert drv["valid"], (
                f"Driver alignment failed for RHEL {version}: {drv['errors']}"
            )
            tl.info(
                f"✓ Driver repos version-scoped for RHEL {version}"
            )

        tl.passed("Dual-Version EUS Catalog test passed")

    except AssertionError as e:
        tl.failed("Dual-Version EUS Catalog test failed", str(e))
        raise
    except Exception as e:
        tl.failed(
            "Unexpected error in Dual-Version EUS Catalog test", str(e)
        )
        raise
