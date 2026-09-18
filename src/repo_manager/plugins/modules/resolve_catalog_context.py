#!/usr/bin/python3
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Resolve the strict Repo Manager catalog execution context."""

import logging

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.catalog_resolver import (
    CatalogResolutionError,
    load_multiple_catalogs,
    resolve_catalog_context,
)


DOCUMENTATION = r"""
---
module: resolve_catalog_context
short_description: Resolve Repo Manager catalog execution contexts
description:
  - Loads one or more Repo Manager catalogs from a file or directory.
  - Resolves their operating-system, version, architecture, platform, and
    referenced-repository execution context.
  - Returns the complete context without modifying the host.
options:
  catalog_path:
    description:
      - Path to a catalog JSON file or a directory containing catalog files.
    required: true
    type: path
author:
  - Dell Technologies
"""

EXAMPLES = r"""
- name: Resolve Repo Manager catalog contexts
  omnia.repo_manager.resolve_catalog_context:
    catalog_path: "{{ catalog_path }}"
  register: resolved_catalog_context
"""

RETURN = r"""
catalog_context:
  description:
    - Resolved catalog execution context and referenced repositories.
  returned: success
  type: dict
  contains:
    os_type:
      description: Operating-system family shared by the selected catalogs.
      type: str
      returned: success
    execution_contexts:
      description: Ordered OS-version and architecture execution contexts.
      type: list
      elements: dict
      returned: success
    platform_capabilities:
      description: Package and repository capabilities for the OS family.
      type: dict
      returned: success
"""


def main():
    """Load the selected catalog and return its OS/version/architectures."""
    module = AnsibleModule(
        argument_spec={
            "catalog_path": {"type": "path", "required": True},
        },
        supports_check_mode=True,
    )
    logger = logging.getLogger("repo_manager.catalog_context")
    try:
        catalogs = load_multiple_catalogs(module.params["catalog_path"], logger)
        context = resolve_catalog_context(catalogs, logger)
        module.exit_json(changed=False, catalog_context=context)
    except CatalogResolutionError as error:
        module.fail_json(
            msg=f"Unable to resolve the catalog execution context: {error}"
        )
    except FileNotFoundError:
        module.fail_json(
            msg=(
                "Unable to resolve the catalog execution context: "
                "CATALOG_FILE_PATH does not identify an existing catalog"
            )
        )
    except OSError:
        module.fail_json(
            msg=(
                "Unable to resolve the catalog execution context: "
                "the selected catalog could not be read"
            )
        )
    except ValueError:
        module.fail_json(
            msg=(
                "Unable to resolve the catalog execution context: "
                "catalog functional layers are invalid or unsupported"
            )
        )


if __name__ == "__main__":
    main()
