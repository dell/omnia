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

"""Business logic service for ParseCatalog API."""

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.catalog.generator import generate_root_json_from_catalog
from common.config import load_config
from container import container
from core.jobs.value_objects import CorrelationId, JobId
from infra.id_generator import UUIDv4Generator
from orchestrator.catalog.commands.parse_catalog import ParseCatalogCommand

logger = logging.getLogger(__name__)


class CatalogParseError(Exception):
    """Exception raised when catalog parsing fails."""


class InvalidFileFormatError(CatalogParseError):
    """Exception raised when the uploaded file has an invalid format."""


class InvalidJSONError(CatalogParseError):
    """Exception raised when the JSON content is invalid."""


@dataclass
class ParseResult:
    """Result of a catalog parse operation."""

    success: bool
    message: str


class ParseCatalogService:  # pylint: disable=too-few-public-methods
    """Service for parsing catalog files."""

    def __init__(self, output_root: Optional[str] = None):
        """Initialize the ParseCatalog service.

        Args:
            output_root: Root directory for generated output files.
                        If None, uses working_dir from config.
        """
        if output_root is None:
            try:
                config = load_config()
                working_dir = Path(config.artifact_store.working_dir)
                working_dir.mkdir(parents=True, exist_ok=True)
                self.output_root = str(working_dir / "tmp" / "generator")
            except (FileNotFoundError, ValueError):
                self.output_root = "/tmp/build_stream/tmp/generator"
        else:
            self.output_root = output_root

        Path(self.output_root).mkdir(parents=True, exist_ok=True)

    async def parse_catalog(
        self,
        filename: str,
        contents: bytes,
        job_id: str,
    ) -> ParseResult:
        """Parse a catalog from uploaded file contents.

        Args:
            filename: Name of the uploaded file.
            contents: Raw bytes content of the uploaded file.
            job_id: The job identifier for the orchestrator.

        Returns:
            ParseResult containing the operation status and details.

        Raises:
            InvalidFileFormatError: If file is not a JSON file.
            InvalidJSONError: If JSON content is malformed or not a dict.
            CatalogParseError: If catalog processing fails.
        """
        logger.info("Starting catalog parse for file: %s", filename)

        # Note: Job validation is handled by the orchestrator use case
        self._validate_file_format(filename)
        json_data = self._parse_json_content(contents)
        self._validate_json_structure(json_data)

        return await self._process_catalog_via_orchestrator(json_data, job_id)

    async def _process_catalog_via_orchestrator(self, json_data: dict, job_id: str) -> ParseResult:
        """Process catalog using the orchestrator use case."""
        # Create command for orchestrator
        uuid_gen = UUIDv4Generator()

        # Convert json_data back to bytes as expected by orchestrator
        json_bytes = json.dumps(json_data).encode('utf-8')

        command = ParseCatalogCommand(
            job_id=JobId(job_id),
            correlation_id=CorrelationId(str(uuid_gen.generate())),
            filename="uploaded.json",
            content=json_bytes,
        )

        # Execute via orchestrator use case
        use_case = container.parse_catalog_use_case()
        result = use_case.execute(command)

        # Convert orchestrator result to API result
        return ParseResult(
            success=True,
            message=result.message,
        )

    def _validate_file_format(self, filename: str) -> None:
        """Validate that the file has a .json extension."""
        if not filename.endswith(".json"):
            logger.warning("Invalid file format received: %s", filename)
            raise InvalidFileFormatError(
                "Invalid file format. Only JSON files are accepted."
            )

    def _parse_json_content(self, contents: bytes) -> dict:
        """Parse JSON content from bytes."""
        try:
            return json.loads(contents.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON content")
            raise InvalidJSONError(f"Invalid JSON data: {e.msg}") from e
        except UnicodeDecodeError as e:
            logger.error("Failed to decode file content as UTF-8")
            raise InvalidJSONError("File content is not valid UTF-8 text") from e

    def _validate_json_structure(self, json_data: object) -> None:
        """Validate that JSON data is a dictionary."""
        if not isinstance(json_data, dict):
            logger.warning("JSON data is not a dictionary")
            raise InvalidJSONError(
                "Invalid JSON data. The data must be a dictionary."
            )

    async def _process_catalog(self, json_data: dict) -> ParseResult:
        """Process the catalog data and generate output files.

        Args:
            json_data: Validated catalog data as a dictionary.

        Returns:
            ParseResult with success status and output path.

        Raises:
            CatalogParseError: If processing fails.
        """
        temp_file_path = None
        try:
            temp_file_path = self._write_temp_file(json_data)
            logger.debug("Wrote catalog to temporary file: %s", temp_file_path)

            generate_root_json_from_catalog(
                catalog_path=temp_file_path,
                output_root=self.output_root,
            )

            logger.info("Catalog parsed successfully, output at: %s", self.output_root)
            return ParseResult(
                success=True,
                message="Catalog parsed successfully",
            )

        except FileNotFoundError as e:
            logger.error("Required file not found during processing")
            raise CatalogParseError("Required file not found during processing") from e
        except Exception as e:
            logger.error("Catalog processing failed")
            raise CatalogParseError("Failed to process catalog") from e
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                logger.debug("Cleaned up temporary file: %s", temp_file_path)

    def _write_temp_file(self, json_data: dict) -> str:
        """Write JSON data to a temporary file.

        Args:
            json_data: Data to write to the file.

        Returns:
            Path to the temporary file.
        """
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as f:
            json.dump(json_data, f)
            return f.name
