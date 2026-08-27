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

Validates catalog JSON **structure** when functional_groups_source is set
to 'catalog'. Checks:
- Valid JSON with 'catalog' root key
- Required sections present (functionallayer, groups, packages)
- Layers have 'name' and 'components' fields
- Groups have 'components' field (list)

Does NOT validate referential integrity (e.g. whether every package key
referenced by a group exists in catalog.packages). The catalog is produced
by repo_manager and may contain forward references or optional components
that are resolved at build time by parse_catalog.py.
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

    # Structural check: each layer should have 'name' and 'components'
    for idx, layer in enumerate(layers):
        if "name" not in layer:
            err = f"catalog: functionallayer[{idx}] is missing 'name' field."
            errors.append(err)
            if logger:
                logger.error(err)
        if "components" not in layer or not isinstance(layer.get("components"), list):
            layer_name = layer.get("name", f"<index {idx}>")
            err = f"catalog: functionallayer '{layer_name}' is missing or has non-list 'components' field."
            errors.append(err)
            if logger:
                logger.error(err)

    # Structural check: groups should be a dict, each group should have 'components' list
    if not isinstance(groups, dict):
        err = "catalog: 'groups' must be a dictionary."
        errors.append(err)
        if logger:
            logger.error(err)

    return errors
