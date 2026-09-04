#!/usr/bin/python3
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Resolve the strict Repo Manager catalog execution context."""

import logging

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.catalog_resolver import (
    load_multiple_catalogs,
    resolve_catalog_context,
)


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
    except (OSError, ValueError) as error:
        module.fail_json(msg=str(error))


if __name__ == "__main__":
    main()
