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
    generate_security_config
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
    "security_config.yml"
]


class WizardGeneratorService:
    """Service for generating deployment configuration files from wizard data."""
    
    def __init__(self, settings=None):
        """Initialize the service.
        
        Args:
            settings: Optional settings instance. If None, uses default.
        """
        self.settings = settings or get_settings()
        
        logger.info("WizardGeneratorService initialized with output_dir: %s", self.settings.output_dir)
    
    def __repr__(self) -> str:
        return f"WizardGeneratorService(output_dir={self.settings.output_dir!r})"
    
    def generate_all_configs(self, job_id: str = None, update_job: Optional[Callable] = None, wizard_data: Dict[str, Any] = None, output_dir: Optional[Path] = None) -> Dict[str, Any]:
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
                raise GenerationError("No wizard data provided. Please complete the configuration wizard first.")
            
            # Check if wizard data has any meaningful content
            has_any_config_data = any([
                wizard_data.get("pxe_mapping_data"),
                wizard_data.get("dns_enabled"),
                wizard_data.get("default_lease_time"),
                wizard_data.get("language"),
                wizard_data.get("kernel_version_override"),
                wizard_data.get("additional_cloud_init_config_file"),
                wizard_data.get("mounts"),
                wizard_data.get("cloud_init_common"),
                wizard_data.get("slurm_cluster"),
                wizard_data.get("service_k8s_cluster"),
                wizard_data.get("service_k8s_cluster_ha"),
                wizard_data.get("enable_build_stream"),
                wizard_data.get("enable_bmc_discovery"),
                wizard_data.get("gitlab_host"),
                wizard_data.get("telemetry_sources"),
                wizard_data.get("telemetry_sinks"),
                wizard_data.get("user_registry_name"),
                wizard_data.get("user_registry"),
                wizard_data.get("user_repo_url_x86_64"),
                wizard_data.get("user_repo_url_aarch64"),
                wizard_data.get("user_registry_username"),
                wizard_data.get("Networks"),
            ])

            if not has_any_config_data:
                raise GenerationError("No configuration data provided. Please fill in at least one configuration field before generating.")

            # Determine and create the output directory
            input_dir = output_dir.expanduser().resolve() if output_dir else self.settings.output_dir
            try:
                input_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise GenerationError(f"Failed to create output directory {input_dir}: {str(e)}")

            # Generate input files from wizard data if provided
            if wizard_data:
                logger.info("Generating deployment configuration files from wizard data")
                if update_job and job_id:
                    update_job(job_id, progress=20)

                # Optional list of filenames to generate (e.g. BMC flow only needs a subset)
                files_to_generate = wizard_data.pop("files_to_generate", None) if isinstance(wizard_data, dict) else None

                self._generate_input_files_from_wizard(wizard_data, job_id, update_job, input_dir, files_to_generate)
                
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
    
    def _generate_input_files_from_wizard(self, wizard_data: Dict[str, Any], job_id: str = None, update_job: Optional[Callable] = None, input_dir: Path = None, files_to_generate: Optional[list] = None):
        """Generate input files from wizard data.

        Args:
            files_to_generate: Optional list of filenames to generate. When omitted,
                all configured generators are run.
        """
        logger.info("Generating input files from wizard data")

        # Ensure output directory exists
        input_dir.mkdir(parents=True, exist_ok=True)

        generator_specs = [
            ("pxe_mapping_file.csv", generate_pxe_mapping_file, (wizard_data, input_dir, ensure_directory)),
            ("provision_config.yml", generate_provision_config, (wizard_data, input_dir, write_yaml)),
            ("storage_config.yml", generate_storage_config, (wizard_data, input_dir, write_yaml)),
            ("additional_cloud_init.yml", generate_additional_cloud_init, (wizard_data, input_dir, write_yaml)),
            ("security_config.yml", generate_security_config, (wizard_data, input_dir, write_yaml)),
            ("omnia_config.yml", generate_omnia_config, (wizard_data, input_dir, write_yaml)),
            ("network_spec.yml", generate_network_spec, (wizard_data, input_dir, write_yaml)),
            ("gitlab_config.yml", generate_gitlab_config, (wizard_data, input_dir, write_yaml)),
            ("build_stream_config.yml", generate_build_stream_config, (wizard_data, input_dir, write_yaml)),
            ("discovery_config.yml", generate_discovery_config, (wizard_data, input_dir, write_yaml)),
            ("high_availability_config.yml", generate_high_availability_config, (wizard_data, input_dir, write_yaml)),
            ("telemetry_config.yml", generate_telemetry_config, (wizard_data, input_dir, write_yaml)),
            ("telemetry_storage_config.yml", generate_telemetry_storage_config, (wizard_data, input_dir, write_yaml)),
            ("user_registry_credential.yml", generate_user_registry_credential, (wizard_data, input_dir, write_yaml)),
        ]

        selected_specs = [
            spec for spec in generator_specs
            if files_to_generate is None or spec[0] in files_to_generate
        ]

        # Clean up old generated files before generating new ones
        # This prevents stale files from previous generations from being included
        files_to_clean = files_to_generate if files_to_generate is not None else GENERATED_CONFIG_FILENAMES
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
