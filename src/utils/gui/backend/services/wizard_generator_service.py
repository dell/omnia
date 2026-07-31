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
"""Wizard configuration generation service.

Orchestrates the generation of all deployment configuration files from wizard data.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from ..config.settings import get_settings
from ..core.exceptions import GenerationError
from ..utils.file_io import write_yaml, ensure_directory
from .config_file_generators import (
    generate_omnia_config,
    generate_network_spec,
    generate_gitlab_config,
    generate_build_stream_config,
    generate_discovery_config,
    generate_high_availability_config,
    generate_telemetry_config,
    generate_telemetry_storage_config,
    generate_user_registry_credential,
    generate_pxe_mapping_file,
    generate_provision_config,
    generate_storage_config,
    generate_additional_cloud_init,
    generate_security_config,
    generate_admin_inventory_csv
)

logger = logging.getLogger(__name__)

GENERATED_CONFIG_FILENAMES = [
    "pxe_mapping_file.csv",
    "provision_config.yml",
    "omnia_config.yml",
    "network_spec.yml",
    "gitlab_config.yml",
    "build_stream_config.yml",
    "discovery_config.yml",
    "high_availability_config.yml",
    "telemetry_config.yml",
    "telemetry_storage_config.yml",
    "user_registry_credential.yml",
    "storage_config.yml",
    "additional_cloud_init.yml",
    "security_config.yml",
    "admin_inventory.csv"
]


class WizardGeneratorService:
    """Service for generating deployment configuration files from wizard data."""

    def __init__(self, settings=None):
        """Initialize the service.

        Args:
            settings: Optional settings instance. If None, uses default.
        """
        self.settings = settings or get_settings()

        logger.info(
            "WizardGeneratorService initialized with output_dir: %s",
            self.settings.output_dir,
        )

    def __repr__(self) -> str:
        return f"WizardGeneratorService(output_dir={self.settings.output_dir!r})"

    def generate_all_configs(
        self,
        job_id: str = None,
        update_job: Optional[Callable] = None,
        wizard_data: Dict[str, Any] = None,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Generate deployment configuration files from wizard data.

        Note: Catalog is now generated separately from catalog management.
        This function only generates the deployment YAML configuration files.

        Args:
            job_id: Optional job ID for progress tracking
            update_job: Optional function to update job progress
            wizard_data: Optional wizard data from frontend
            output_dir: Optional output directory override

        Returns:
            Dictionary with generation results
        """
        try:
            logger.info(
                "generate_all_configs called with job_id=%s, update_job=%s, wizard_data=%s",
                job_id,
                update_job is not None,
                wizard_data is not None,
            )
            if job_id:
                logger.info("Starting generation for job %s", job_id)

            # Validate wizard data before generation
            if not wizard_data:
                raise GenerationError(
                    "No wizard data provided. "
                    "Please complete the configuration wizard first."
                )

            # Check if wizard data has any meaningful content
            config_keys = (
                "pxe_mapping_data", "dns_enabled",
                "default_lease_time", "language",
                "kernel_version_override",
                "additional_cloud_init_config_file",
                "mounts", "cloud_init_common",
                "slurm_cluster", "service_k8s_cluster",
                "service_k8s_cluster_ha",
                "enable_build_stream",
                "enable_bmc_discovery", "gitlab_host",
                "telemetry_sources", "telemetry_sinks",
                "user_registry_name", "user_registry",
                "user_repo_url_x86_64",
                "user_repo_url_aarch64",
                "user_registry_username", "Networks",
            )
            has_any_config_data = any(
                wizard_data.get(key) for key in config_keys
            )

            if not has_any_config_data:
                raise GenerationError(
                    "No configuration data provided. "
                    "Please fill in at least one "
                    "configuration field before generating."
                )

            # Determine and create the output directory
            input_dir = (
                output_dir.expanduser().resolve()
                if output_dir
                else self.settings.output_dir
            )
            try:
                input_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise GenerationError(
                    f"Failed to create output directory "
                    f"{input_dir}: {e}"
                ) from e

            # Generate input files from wizard data if provided
            if wizard_data:
                logger.info(
                    "Generating deployment configuration "
                    "files from wizard data",
                )
                if update_job and job_id:
                    update_job(job_id, progress=20)

                # Optional list of filenames to generate (e.g. BMC flow only needs a subset)
                files_to_generate = (
                    wizard_data.pop("files_to_generate", None)
                    if isinstance(wizard_data, dict)
                    else None
                )

                self._generate_input_files_from_wizard(
                    wizard_data, job_id, update_job,
                    input_dir, files_to_generate,
                )

                logger.info("Deployment configuration files generation completed")

            return {
                "config_files_generated": True,
                "input_dir": str(input_dir)
            }
        except GenerationError:
            raise
        except Exception as e:
            logger.exception("Configuration generation failed")
            raise GenerationError("Configuration generation failed") from e

    def _generate_input_files_from_wizard(
        self,
        wizard_data: Dict[str, Any],
        job_id: str = None,
        update_job: Optional[Callable] = None,
        input_dir: Path = None,
        files_to_generate: Optional[list] = None,
    ):
        """Generate input files from wizard data.

        Args:
            files_to_generate: Optional list of filenames to generate. When omitted,
                all configured generators are run.
        """
        logger.info("Generating input files from wizard data")

        # Ensure output directory exists
        input_dir.mkdir(parents=True, exist_ok=True)

        gen_args = (wizard_data, input_dir, write_yaml)
        dir_args = (wizard_data, input_dir, ensure_directory)
        generator_specs = [
            ("pxe_mapping_file.csv", generate_pxe_mapping_file, dir_args),
            ("provision_config.yml", generate_provision_config, gen_args),
            ("storage_config.yml", generate_storage_config, gen_args),
            ("additional_cloud_init.yml", generate_additional_cloud_init, gen_args),
            ("security_config.yml", generate_security_config, gen_args),
            ("omnia_config.yml", generate_omnia_config, gen_args),
            ("network_spec.yml", generate_network_spec, gen_args),
            ("gitlab_config.yml", generate_gitlab_config, gen_args),
            ("build_stream_config.yml", generate_build_stream_config, gen_args),
            ("discovery_config.yml", generate_discovery_config, gen_args),
            ("high_availability_config.yml", generate_high_availability_config, gen_args),
            ("telemetry_config.yml", generate_telemetry_config, gen_args),
            ("telemetry_storage_config.yml", generate_telemetry_storage_config, gen_args),
            ("user_registry_credential.yml", generate_user_registry_credential, gen_args),
            ("admin_inventory.csv", generate_admin_inventory_csv, dir_args),
        ]

        selected_specs = [
            spec for spec in generator_specs
            if files_to_generate is None or spec[0] in files_to_generate
        ]

        # Clean up old generated files before generating new ones
        # This prevents stale files from previous generations from being included
        files_to_clean = (
            files_to_generate
            if files_to_generate is not None
            else GENERATED_CONFIG_FILENAMES
        )
        for filename in files_to_clean:
            file_path = input_dir / filename
            if file_path.exists():
                file_path.unlink()
                logger.info("Deleted old file: %s", filename)

        if not selected_specs:
            logger.info("No generators selected for the requested files")
            return

        progress = 20
        increment = 80 // len(selected_specs)
        for filename, gen, args in selected_specs:
            gen(*args)
            progress = min(100, progress + increment)
            if update_job and job_id:
                update_job(job_id, progress=progress)

        if update_job and job_id:
            update_job(job_id, progress=100)

        logger.info("Input files generated from wizard data")
