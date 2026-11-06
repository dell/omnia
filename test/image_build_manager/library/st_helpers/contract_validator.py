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
Contract Validator — Validates repo_status.yml and build_status.yml contracts.
"""

from typing import Dict, Any, List, Optional
import yaml
from pathlib import Path


class ContractValidator:
    """Validates Omnia contracts (repo_status.yml, build_status.yml)."""

    @staticmethod
    def validate_repo_status(contract: Dict[str, Any]) -> Dict[str, Any]:
        """Validate repo_status.yml contract.
        
        Args:
            contract: Loaded repo_status.yml dictionary
            
        Returns:
            Validation result with 'valid' bool and 'errors' list
        """
        errors = []
        
        # Check required top-level keys
        required_keys = ["cluster_os_type", "overall_status"]
        for key in required_keys:
            if key not in contract:
                errors.append(f"Missing required key: {key}")
        
        # Check overall_status value
        if contract.get("overall_status") not in ["success", "failure", "partial"]:
            errors.append(f"Invalid overall_status: {contract.get('overall_status')}")
        
        # Check for repositories key (actual structure)
        if "repositories" not in contract:
            errors.append("No repositories found in repo_status.yml")
            return {"valid": False, "errors": errors}
        
        repositories = contract.get("repositories", {})
        
        # Check for OS version keys in repositories
        os_versions = list(repositories.keys())
        if not os_versions:
            errors.append("No OS version keys found in repositories")
        
        # Validate each OS version
        for version in os_versions:
            version_data = repositories.get(version, {})
            if not isinstance(version_data, dict):
                errors.append(f"OS version {version} data is not a dictionary")
                continue
            
            # Check for architecture keys
            if "x86_64" not in version_data:
                errors.append(f"Missing x86_64 architecture for OS version {version}")
            else:
                arch_data = version_data["x86_64"]
                # Check for required repositories
                if not arch_data:
                    errors.append(f"No repositories found for {version}.x86_64")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    @staticmethod
    def validate_build_status(contract: Dict[str, Any]) -> Dict[str, Any]:
        """Validate build_status.yml contract.
        
        Args:
            contract: Loaded build_status.yml dictionary
            
        Returns:
            Validation result with 'valid' bool and 'errors' list
        """
        errors = []
        
        # Check required top-level keys
        required_keys = ["overall_status"]
        for key in required_keys:
            if key not in contract:
                errors.append(f"Missing required key: {key}")
        
        # Check overall_status value
        if contract.get("overall_status") not in ["success", "failure"]:
            errors.append(f"Invalid overall_status: {contract.get('overall_status')}")
        
        # Validate S3 configuration (can be s3_config or s3_configurations)
        s3_config = contract.get("s3_config") or contract.get("s3_configurations", {})
        if not s3_config:
            errors.append("No S3 configuration found")
        else:
            s3_required = ["endpoint_url", "bucket"] if "endpoint_url" in s3_config else ["endpoint", "bucket"]
            for key in s3_required:
                if key not in s3_config:
                    errors.append(f"Missing S3 config key: {key}")
        
        # Check for functional group artifacts (can be functional_groups or functional_group_images)
        functional_groups = contract.get("functional_groups") or contract.get("functional_group_images", [])
        if not functional_groups:
            errors.append("No functional groups found in build_status.yml")
            return {"valid": len(errors) == 0, "errors": errors}
        
        # Handle list format (functional_group_images)
        if isinstance(functional_groups, list):
            for arch_entry in functional_groups:
                if isinstance(arch_entry, dict):
                    for arch, groups in arch_entry.items():
                        if isinstance(groups, list):
                            for group in groups:
                                if isinstance(group, dict):
                                    # Check for required artifact keys
                                    required_artifacts = ["kernel", "initrd", "image"]
                                    for artifact in required_artifacts:
                                        if artifact not in group:
                                            fg_name = group.get("functional_group", "unknown")
                                            errors.append(f"Missing {artifact} artifact for FG {fg_name}")
                                        elif not group[artifact]:
                                            fg_name = group.get("functional_group", "unknown")
                                            errors.append(f"Empty {artifact} artifact path for FG {fg_name}")
        # Handle dict format (functional_groups)
        elif isinstance(functional_groups, dict):
            for fg_name, fg_data in functional_groups.items():
                if not isinstance(fg_data, dict):
                    errors.append(f"Functional group {fg_name} data is not a dictionary")
                    continue
                
                # Check for required artifact keys
                required_artifacts = ["kernel", "initrd", "image"]
                for artifact in required_artifacts:
                    if artifact not in fg_data:
                        errors.append(f"Missing {artifact} artifact for FG {fg_name}")
                    elif not fg_data[artifact]:
                        errors.append(f"Empty {artifact} artifact path for FG {fg_name}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    @staticmethod
    def validate_dual_os_versions(repo_status: Dict[str, Any], 
                                  build_status: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that both RHEL 10.0 EUS and 10.2 EUS are present.
        
        Args:
            repo_status: Loaded repo_status.yml
            build_status: Loaded build_status.yml
            
        Returns:
            Validation result with 'valid' bool and 'errors' list
        """
        errors = []
        
        # Check repo_status for both versions (look in repositories section)
        repositories = repo_status.get("repositories", {})
        repo_versions = list(repositories.keys())
        
        if "10.0" not in repo_versions:
            errors.append("RHEL 10.0 EUS not found in repo_status.yml")
        if "10.2" not in repo_versions:
            errors.append("RHEL 10.2 EUS not found in repo_status.yml")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    @staticmethod
    def validate_driver_alignment(repo_status: Dict[str, Any],
                                  os_version: str,
                                  required_drivers: Optional[List[str]] = None,
                                  ) -> Dict[str, Any]:
        """Validate driver repo version alignment with an OS version.

        Checks that the required driver repositories exist under the
        version-scoped ``repositories.<os_version>.x86_64`` section of
        ``repo_status.yml`` and that each URL encodes the correct OS
        version path segment (e.g. ``/rhel/10.2/``).

        Args:
            repo_status: Loaded repo_status.yml dictionary.
            os_version: OS version to check (e.g., "10.2").
            required_drivers: Driver repo names to verify.  Defaults to
                ``["cuda", "doca", "nvidia-hpc-sdk"]``.

        Returns:
            Dict with ``valid`` (bool), ``errors`` (list), and
            ``drivers`` (dict mapping driver name to its URL).
        """
        if required_drivers is None:
            required_drivers = ["cuda", "doca", "nvidia-hpc-sdk"]

        errors: List[str] = []
        found_drivers: Dict[str, str] = {}

        repositories = repo_status.get("repositories", {})
        version_repos = repositories.get(os_version, {})
        if not version_repos:
            errors.append(
                f"OS version {os_version} not found in repo_status.yml repositories"
            )
            return {"valid": False, "errors": errors, "drivers": found_drivers}

        arch_repos = version_repos.get("x86_64", {})
        if not arch_repos:
            errors.append(
                f"x86_64 architecture not found under repositories.{os_version}"
            )
            return {"valid": False, "errors": errors, "drivers": found_drivers}

        for driver in required_drivers:
            entry = arch_repos.get(driver)
            if not entry:
                errors.append(
                    f"Missing {driver} repository under {os_version}.x86_64"
                )
                continue

            url = entry.get("url", entry) if isinstance(entry, dict) else entry
            if not url or not isinstance(url, str):
                errors.append(f"Empty or invalid URL for {driver} under {os_version}")
                continue

            # Verify the URL encodes the correct OS version path segment
            version_segment = f"/rhel/{os_version}/"
            if version_segment not in url:
                errors.append(
                    f"{driver} URL does not contain expected version path "
                    f"'{version_segment}': {url}"
                )
            else:
                found_drivers[driver] = url

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "drivers": found_drivers,
        }
