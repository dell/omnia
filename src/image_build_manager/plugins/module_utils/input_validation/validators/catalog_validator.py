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
Catalog JSON validator for image_build_manager.

Validates catalog JSON structure and referential integrity when
functional_groups_source is set to 'catalog'. Checks:
- Required top-level keys (catalog.functionallayer, catalog.groups, catalog.packages)
- Referential integrity: layer -> groups -> packages
- Dangling references (groups not in catalog, packages not in group)
"""
import json
import os

from ansible.module_utils.input_validation.messages import (  # pylint: disable=E0401
    image_build_messages as msg,
)


def validate(catalog_file, logger=None):
    """
    Run L2 validation on a catalog JSON file.

    Args:
        catalog_file (str): Absolute path to catalog JSON file.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    errors = []

    if not catalog_file or not os.path.isfile(catalog_file):
        errors.append(msg.CATALOG_FILE_NOT_FOUND_MSG)
        if logger:
            logger.error(msg.CATALOG_FILE_NOT_FOUND_MSG)
        return errors

    try:
        with open(catalog_file, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        err = f"catalog: Failed to parse catalog JSON: {exc}"
        errors.append(err)
        if logger:
            logger.error(err)
        return errors

    if "catalog" not in raw:
        errors.append(msg.CATALOG_MISSING_ROOT_KEY_MSG)
        if logger:
            logger.error(msg.CATALOG_MISSING_ROOT_KEY_MSG)
        return errors

    catalog = raw["catalog"]

    # Check required sections
    layers = catalog.get("functionallayer", [])
    if not layers:
        errors.append(msg.CATALOG_NO_FUNCTIONAL_LAYERS_MSG)
        if logger:
            logger.error(msg.CATALOG_NO_FUNCTIONAL_LAYERS_MSG)

    groups = catalog.get("groups")
    if groups is None:
        errors.append(msg.CATALOG_MISSING_GROUPS_MSG)
        if logger:
            logger.error(msg.CATALOG_MISSING_GROUPS_MSG)
        groups = {}

    packages = catalog.get("packages")
    if packages is None:
        errors.append(msg.CATALOG_MISSING_PACKAGES_MSG)
        if logger:
            logger.error(msg.CATALOG_MISSING_PACKAGES_MSG)
        packages = {}

    # Referential integrity: layers -> groups
    for layer in layers:
        layer_name = layer.get("name", "<unnamed>")
        for comp in layer.get("components", []):
            if comp not in groups:
                err = msg.catalog_dangling_component_msg(layer_name, comp)
                errors.append(err)
                if logger:
                    logger.error(err)

    # Referential integrity: groups -> packages
    for group_name, group_data in groups.items():
        for pkg_key in group_data.get("components", []):
            if pkg_key not in packages:
                err = msg.catalog_dangling_package_msg(group_name, pkg_key)
                errors.append(err)
                if logger:
                    logger.error(err)

    return errors
