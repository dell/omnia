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

"""Business logic service for catalog roles API."""

import io
import json
import logging
import zipfile
from typing import Dict, List

from core.artifacts.exceptions import ArtifactNotFoundError
from core.artifacts.interfaces import ArtifactMetadataRepository, ArtifactStore
from core.artifacts.value_objects import ArtifactKind
from core.jobs.exceptions import InvalidStateTransitionError
from core.jobs.repositories import StageRepository
from core.jobs.value_objects import JobId, StageName, StageState, StageType

logger = logging.getLogger(__name__)

_FUNCTIONAL_LAYER_FILENAME = "functional_layer.json"


class ParseCatalogNotCompletedError(Exception):
    """Raised when the parse-catalog stage has not completed for the given job."""


class RolesNotFoundError(Exception):
    """Raised when no functional_layer.json can be found in the root-jsons archive."""


class CatalogRolesService:
    """Service for retrieving roles from the parse-catalog intermediate artifacts."""

    def __init__(
        self,
        artifact_store: ArtifactStore,
        artifact_metadata_repo: ArtifactMetadataRepository,
        stage_repo: StageRepository,
    ) -> None:
        self._artifact_store = artifact_store
        self._artifact_metadata_repo = artifact_metadata_repo
        self._stage_repo = stage_repo

    def get_roles(self, job_id: JobId) -> Dict[str, any]:
        """Return catalog metadata including roles, image_key, and architectures.

        Retrieves the root-jsons archive and catalog file artifacts stored by
        the parse-catalog stage. Validates that parse-catalog has completed.

        Args:
            job_id: The job identifier.

        Returns:
            Dictionary with keys:
                - roles: Sorted list of role name strings
                - image_key: Catalog identifier
                - architectures: List of supported architectures

        Raises:
            ParseCatalogNotCompletedError: If parse-catalog has not completed
                or artifacts are missing.
            RolesNotFoundError: If functional_layer.json cannot be parsed.
        """
        logger.info("Retrieving catalog metadata for job: %s", job_id)
        
        # Validate parse-catalog stage is completed
        self._validate_parse_catalog_completed(job_id)

        record = self._artifact_metadata_repo.find_by_job_stage_and_label(
            job_id=job_id,
            stage_name=StageName(StageType.PARSE_CATALOG.value),
            label="root-jsons",
        )

        if record is None:
            logger.warning(
                "root-jsons artifact not found for job %s; parse-catalog may not have completed",
                job_id,
            )
            raise ParseCatalogNotCompletedError(
                f"Parse-catalog stage has not completed for job: {job_id}"
            )

        logger.debug(
            "Found root-jsons artifact record for job %s (key=%s)",
            job_id,
            record.artifact_ref.key.value,
        )

        try:
            raw_bytes = self._artifact_store.retrieve(
                key=record.artifact_ref.key,
                kind=ArtifactKind.FILE,
            )
        except ArtifactNotFoundError as exc:
            logger.error(
                "root-jsons artifact file missing from store for job %s", job_id
            )
            raise ParseCatalogNotCompletedError(
                f"Root-jsons artifact not found in store for job: {job_id}"
            ) from exc

        # Extract roles from functional_layer.json
        roles = self._extract_roles_from_archive(raw_bytes, job_id)
        
        # Extract catalog metadata (Identifier and architectures)
        catalog_metadata = self._extract_catalog_metadata(job_id)
        
        result = {
            "roles": roles,
            "image_key": catalog_metadata["image_key"],
            "architectures": catalog_metadata["architectures"],
        }
        
        logger.info(
            "Returning catalog metadata for job %s: %d roles, image_key=%s, %d architectures",
            job_id,
            len(roles),
            result["image_key"],
            len(result["architectures"]),
        )
        return result

    def _extract_roles_from_archive(
        self, raw_bytes: bytes, job_id: JobId
    ) -> List[str]:
        """Extract role names from the root-jsons zip archive.

        Searches all entries in the archive for any file named
        ``functional_layer.json`` and returns the sorted top-level keys
        of the first one found.

        Args:
            raw_bytes: Raw bytes of the zip archive.
            job_id: Job identifier (used only for logging).

        Returns:
            Sorted list of role name strings.

        Raises:
            RolesNotFoundError: If no functional_layer.json is found or the
                file cannot be parsed.
        """
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes), "r") as zf:
                candidates = [
                    name
                    for name in zf.namelist()
                    if name.endswith(_FUNCTIONAL_LAYER_FILENAME)
                ]

                if not candidates:
                    logger.error(
                        "No %s found in root-jsons archive for job %s",
                        _FUNCTIONAL_LAYER_FILENAME,
                        job_id,
                    )
                    raise RolesNotFoundError(
                        f"No {_FUNCTIONAL_LAYER_FILENAME} found in the "
                        f"root-jsons archive for job: {job_id}"
                    )

                # Use the first functional_layer.json found (any arch/os/version)
                target = candidates[0]
                logger.debug(
                    "Reading roles from archive entry: %s (job=%s)", target, job_id
                )

                with zf.open(target) as f:
                    data = json.load(f)

        except zipfile.BadZipFile as exc:
            logger.error(
                "root-jsons artifact is not a valid zip archive for job %s", job_id
            )
            raise RolesNotFoundError(
                f"root-jsons artifact is not a valid archive for job: {job_id}"
            ) from exc
        except json.JSONDecodeError as exc:
            logger.error(
                "Failed to parse %s in archive for job %s",
                _FUNCTIONAL_LAYER_FILENAME,
                job_id,
            )
            raise RolesNotFoundError(
                f"Failed to parse {_FUNCTIONAL_LAYER_FILENAME} for job: {job_id}"
            ) from exc

        if not isinstance(data, dict):
            raise RolesNotFoundError(
                f"{_FUNCTIONAL_LAYER_FILENAME} does not contain a JSON object for job: {job_id}"
            )

        roles = sorted(data.keys())
        return roles

    def _validate_parse_catalog_completed(self, job_id: JobId) -> None:
        """Validate that parse-catalog stage has completed.

        Args:
            job_id: The job identifier.

        Raises:
            ParseCatalogNotCompletedError: If stage is not in COMPLETED state.
        """
        stage = self._stage_repo.find_by_job_and_name(
            job_id, StageName(StageType.PARSE_CATALOG.value)
        )

        if stage is None:
            logger.warning(
                "parse-catalog stage not found for job %s", job_id
            )
            raise ParseCatalogNotCompletedError(
                f"Parse-catalog stage not found for job: {job_id}"
            )

        if stage.stage_state != StageState.COMPLETED:
            logger.warning(
                "parse-catalog stage not completed for job %s (state=%s)",
                job_id,
                stage.stage_state.value,
            )
            raise ParseCatalogNotCompletedError(
                f"Parse-catalog stage is in {stage.stage_state.value} state, "
                f"must be COMPLETED before querying roles"
            )

    def _extract_catalog_metadata(self, job_id: JobId) -> Dict[str, any]:
        """Extract catalog Identifier and architectures from catalog-file artifact.

        Args:
            job_id: The job identifier.

        Returns:
            Dictionary with 'image_key' and 'architectures' keys.

        Raises:
            ParseCatalogNotCompletedError: If catalog-file artifact not found.
            RolesNotFoundError: If catalog cannot be parsed.
        """
        # Find catalog-file artifact
        catalog_record = self._artifact_metadata_repo.find_by_job_stage_and_label(
            job_id=job_id,
            stage_name=StageName(StageType.PARSE_CATALOG.value),
            label="catalog-file",
        )

        if catalog_record is None:
            logger.error(
                "catalog-file artifact not found for job %s", job_id
            )
            raise ParseCatalogNotCompletedError(
                f"Catalog file artifact not found for job: {job_id}"
            )

        try:
            catalog_bytes = self._artifact_store.retrieve(
                key=catalog_record.artifact_ref.key,
                kind=ArtifactKind.FILE,
            )
        except ArtifactNotFoundError as exc:
            logger.error(
                "catalog-file missing from store for job %s", job_id
            )
            raise ParseCatalogNotCompletedError(
                f"Catalog file not found in store for job: {job_id}"
            ) from exc

        try:
            catalog_data = json.loads(catalog_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error(
                "Failed to parse catalog file for job %s", job_id
            )
            raise RolesNotFoundError(
                f"Failed to parse catalog file for job: {job_id}"
            ) from exc

        # Extract Identifier (image_key)
        catalog_obj = catalog_data.get("Catalog", {})
        image_key = catalog_obj.get("Identifier", "")
        if not image_key:
            logger.warning(
                "No Identifier found in catalog for job %s", job_id
            )
            image_key = "unknown"

        # Extract architectures from functional packages
        architectures = set()
        functional_packages = catalog_obj.get("FunctionalPackages", {})
        
        # Handle both dictionary and array formats
        if isinstance(functional_packages, dict):
            # Dictionary format: {"package_id": {"Architecture": [...]}}
            for pkg_id, pkg_data in functional_packages.items():
                if isinstance(pkg_data, dict):
                    arch_list = pkg_data.get("Architecture", [])
                    if isinstance(arch_list, list):
                        architectures.update(arch_list)
                    elif isinstance(arch_list, str):
                        architectures.add(arch_list)
        elif isinstance(functional_packages, list):
            # Array format: [{"Architecture": [...]}, ...]
            for pkg in functional_packages:
                if not isinstance(pkg, dict):
                    continue
                arch_list = pkg.get("Architecture", [])
                if isinstance(arch_list, list):
                    architectures.update(arch_list)
                elif isinstance(arch_list, str):
                    architectures.add(arch_list)

        # Also check OS packages for architectures
        os_packages = catalog_obj.get("OSPackages", {})
        
        # Handle both dictionary and array formats
        if isinstance(os_packages, dict):
            # Dictionary format: {"os_package_id": {"Architecture": [...]}}
            for pkg_id, pkg_data in os_packages.items():
                if isinstance(pkg_data, dict):
                    arch_list = pkg_data.get("Architecture", [])
                    if isinstance(arch_list, list):
                        architectures.update(arch_list)
                    elif isinstance(arch_list, str):
                        architectures.add(arch_list)
        elif isinstance(os_packages, list):
            # Array format: [{"Architecture": [...]}, ...]
            for pkg in os_packages:
                if not isinstance(pkg, dict):
                    continue
                arch_list = pkg.get("Architecture", [])
                if isinstance(arch_list, list):
                    architectures.update(arch_list)
                elif isinstance(arch_list, str):
                    architectures.add(arch_list)

        return {
            "image_key": image_key,
            "architectures": sorted(list(architectures)),
        }
