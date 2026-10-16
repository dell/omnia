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

"""Catalog parser.

Loads and validates a catalog JSON file against CatalogSchema.json and
materializes it into model objects.
"""

import os

from api.logging_utils import log_secure_info
from jsonschema import validate, ValidationError
from .exceptions import UnsupportedSchemaVersionError
from .models import Catalog, FunctionalPackage, OsPackage, InfrastructurePackage, Driver
from .utils import load_json_file

# Supported catalog schema versions for this release.
# Version 1: Legacy catalogs (Omnia <2.3, no SchemaVersion field).
# Version 2: Omnia 2.3+ catalogs with explicit SchemaVersion.
SUPPORTED_SCHEMA_VERSIONS = {1, 2}


_BASE_DIR = os.path.dirname(__file__)
_DEFAULT_SCHEMA_PATH = os.path.join(_BASE_DIR, "resources", "CatalogSchema.json")

def ParseCatalog(file_path: str, schema_path: str = _DEFAULT_SCHEMA_PATH) -> Catalog:
    """Parse a catalog JSON file and validate it against the JSON schema.

    Args:
        file_path: Path to the catalog JSON file.
        schema_path: Path to the JSON schema used for validation.

    Returns:
        A populated Catalog instance built from the validated JSON data.
    """

    log_secure_info('info', f"Parsing catalog from {file_path} using schema {schema_path}")
    schema = load_json_file(schema_path)
    catalog_json = load_json_file(file_path)

    log_secure_info('debug', "Validating catalog JSON against schema")
    try:
        validate(instance=catalog_json, schema=schema)
    except ValidationError:
        log_secure_info('error', f"Catalog validation failed for {file_path}")
        raise
    data = catalog_json["Catalog"]

    # Extract schema_version. Legacy catalogs (Omnia <2.3) may lack this
    # field; default to 1 for backward compatibility but log a warning.
    schema_version = data.get("SchemaVersion", data.get("schema_version"))
    if schema_version is None:
        schema_version = 1
        log_secure_info(
            'warning',
            f"Catalog missing 'SchemaVersion' field in {file_path}; "
            f"defaulting to schema_version=1 (legacy)"
        )

    # Validate schema version is in the supported set (ER-BSM-002).
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise UnsupportedSchemaVersionError(
            schema_version=schema_version,
            supported=SUPPORTED_SCHEMA_VERSIONS,
        )

    identifier = data.get("Identifier", "")

    functional_packages = [
        FunctionalPackage(
            id=key,
            name=pkg["Name"],
            version=pkg.get("Version", ""),
            supported_os=[f"{os['Name']} {os['Version']}" for os in pkg["SupportedOS"]],
            uri="",
            type=pkg["Type"],
            architecture=pkg["Architecture"],
            tag=pkg.get("Tag", ""),
            sources=pkg.get("Sources", []),
        )
        for key, pkg in data["FunctionalPackages"].items()
    ]

    os_packages = [
        OsPackage(
            id=key,
            name=pkg["Name"],
            version=pkg.get("Version", ""),
            supported_os=[f"{os['Name']} {os['Version']}" for os in pkg["SupportedOS"]],
            uri="",
            architecture=pkg["Architecture"],
            sources=pkg.get("Sources", []),
            type=pkg["Type"],
            tag=pkg.get("Tag", ""),
        )
        for key, pkg in data["OSPackages"].items()
    ]

    infrastructure_packages = [
        InfrastructurePackage(
            id=key,
            name=pkg["Name"],
            version=pkg["Version"],
            uri=pkg.get("Uri", ""),
            architecture=pkg.get("Architecture", []),
            config=pkg["SupportedFunctions"],
            type=pkg["Type"],
            sources=pkg.get("Sources", []),
            tag=pkg.get("Tag", ""),
        )
        for key, pkg in data["InfrastructurePackages"].items()
    ]

    driver_packages = data.get("DriverPackages", {})
    drivers = [
        Driver(
            id=key,
            name=drv["Name"],
            version=drv["Version"],
            uri=drv["Uri"],
            architecture=drv["Architecture"],
            config=drv["Config"],
            type=drv["Type"],
        )
        for key, drv in driver_packages.items()
    ]

    catalog = Catalog(
        name=data["Name"],
        version=data["Version"],
        schema_version=schema_version,
        identifier=identifier,
        functional_layer=data["FunctionalLayer"],
        base_os=data["BaseOS"],
        infrastructure=data["Infrastructure"],
        drivers_layer=data.get("Drivers", []),
        drivers=drivers,
        functional_packages=functional_packages,
        os_packages=os_packages,
        infrastructure_packages=infrastructure_packages,
        miscellaneous=data.get("Miscellaneous", []),
    )

    log_secure_info(
        'info',
        f"Parsed catalog {catalog.name} v{catalog.version} "
        f"(schema_version={catalog.schema_version}, "
        f"composite_id={catalog.composite_id}): "
        f"{len(functional_packages)} functional, {len(os_packages)} OS, "
        f"{len(infrastructure_packages)} infrastructure, {len(drivers)} drivers"
    )

    return catalog
