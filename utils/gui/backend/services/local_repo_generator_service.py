"""Local repository configuration generation service.

Generates local_repo_config.yml and user_registry_credential.yml independently
from the deployment wizard.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ..config.settings import get_settings
from ..core.exceptions import GenerationError
from .config_file_generators import (
    generate_local_repo_config,
    generate_user_registry_credential,
)

logger = logging.getLogger(__name__)


class LocalRepoGeneratorService:
    """Service for generating local repository configuration files."""

    def __init__(self, settings=None):
        """Initialize the service.

        Args:
            settings: Optional settings instance. If None, uses default.
        """
        self.settings = settings or get_settings()
        logger.info("LocalRepoGeneratorService initialized with output_dir: %s", self.settings.output_dir)

    def generate_local_repo_configs(
        self,
        job_id: str = None,
        update_job=None,
        data: Dict[str, Any] = None,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Generate local_repo_config.yml and user_registry_credential.yml.

        Args:
            job_id: Optional job ID for progress tracking
            update_job: Optional function to update job progress
            data: Local repo management data from the frontend
            output_dir: Optional output directory override

        Returns:
            Dictionary with generation results
        """
        try:
            logger.info("generate_local_repo_configs called with job_id=%s, data=%s", job_id, data is not None)

            if not data:
                raise GenerationError("No local repo data provided.")

            input_dir = output_dir.expanduser().resolve() if output_dir else self.settings.output_dir
            try:
                input_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise GenerationError(f"Failed to create output directory {input_dir}: {str(e)}")

            if update_job and job_id:
                update_job(job_id, progress=30)

            # Generate local_repo_config.yml (handles both per-OS and legacy payloads)
            generate_local_repo_config(data, input_dir, None)

            if update_job and job_id:
                update_job(job_id, progress=70)

            # Generate user_registry_credential.yml if credentials are enabled
            generate_user_registry_credential(data, input_dir, None)

            if update_job and job_id:
                update_job(job_id, progress=100)

            logger.info("Local repo configuration files generated successfully at %s", input_dir)
            return {
                "config_files_generated": True,
                "input_dir": str(input_dir),
            }
        except GenerationError:
            raise
        except Exception as e:
            logger.exception("Local repo config generation failed")
            raise GenerationError("Local repo config generation failed") from e
