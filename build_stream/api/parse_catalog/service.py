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
from typing import Optional

from core.catalog.generator import generate_root_json_from_catalog

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
    output_path: Optional[str] = None


class ParseCatalogService:  # pylint: disable=too-few-public-methods
    """Service for parsing catalog files."""

    DEFAULT_OUTPUT_ROOT = "out/generator"

    def __init__(self, output_root: Optional[str] = None):
        """Initialize the ParseCatalog service.

        Args:
            output_root: Root directory for generated output files.
        """
        self.output_root = output_root or self.DEFAULT_OUTPUT_ROOT

    async def parse_catalog(
        self,
        filename: str,
        contents: bytes,
    ) -> ParseResult:
        """Parse a catalog from uploaded file contents.

        Args:
            filename: Name of the uploaded file.
            contents: Raw bytes content of the uploaded file.

        Returns:
            ParseResult containing the operation status and details.

        Raises:
            InvalidFileFormatError: If file is not a JSON file.
            InvalidJSONError: If JSON content is malformed or not a dict.
            CatalogParseError: If catalog processing fails.
        """
        logger.info("Starting catalog parse for file: %s", filename)

        self._validate_file_format(filename)
        json_data = self._parse_json_content(contents)
        self._validate_json_structure(json_data)

        return await self._process_catalog(json_data)

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
                output_path=self.output_root,
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
