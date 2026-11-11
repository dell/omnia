#!/usr/bin/python
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
"""Ansible interface for the Image Build Manager global dictionary."""

from __future__ import annotations

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.image_group_dictionary import (
    ImageGroupDictionaryRepository,
)


DOCUMENTATION = r"""
---
module: manage_image_group_dictionary
short_description: Query and update the catalog image-group dictionary
version_added: "2.3.0"
description:
  - Resolves catalog-mode compute image cache hits.
  - Atomically registers exact S3 artifact paths after successful builds.
  - Removes entries when an image group is pruned.
options:
  dictionary_path:
    description: Absolute path to image_group_dictionary.json.
    required: true
    type: path
  operation:
    description: Dictionary operation to perform.
    required: true
    type: str
    choices: [lookup, upsert, prune]
  candidates:
    description: Package-hash lookup candidates.
    type: list
    elements: dict
    default: []
  entries:
    description: Complete reusable image entries to register.
    type: list
    elements: dict
    default: []
  image_group_id:
    description: Image group whose entries must be removed.
    type: str
    default: ""
  catalog_schema_version:
    description: Catalog schema version recorded with dictionary updates.
    type: int
author:
  - Dell Omnia Team
"""

EXAMPLES = r"""
- name: Lookup catalog compute groups
  manage_image_group_dictionary:
    dictionary_path: "{{ output_project_dir }}/image_group_dictionary.json"
    operation: lookup
    candidates: "{{ dictionary_candidates }}"
  register: dictionary_lookup
"""

RETURN = r"""
hits:
  description: Entries found, keyed by functional group.
  returned: operation is lookup
  type: dict
misses:
  description: Functional groups not present in the dictionary.
  returned: operation is lookup
  type: list
dictionary_warnings:
  description: Non-fatal primary/backup load warning, when present.
  returned: always
  type: list
"""


def _warning_list(repository: ImageGroupDictionaryRepository) -> list[str]:
    """Return non-fatal repository recovery information."""
    warnings: list[str] = []
    if repository.load_error:
        warnings.append(repository.load_error)
    if repository.recovered_from_backup:
        warnings.append("Recovered image-group dictionary from backup")
    return warnings


def main() -> None:
    """Execute the requested dictionary operation."""
    module = AnsibleModule(
        argument_spec={
            "dictionary_path": {"type": "path", "required": True},
            "operation": {
                "type": "str",
                "required": True,
                "choices": ["lookup", "upsert", "prune"],
            },
            "candidates": {"type": "list", "elements": "dict", "default": []},
            "entries": {"type": "list", "elements": "dict", "default": []},
            "image_group_id": {"type": "str", "default": ""},
            "catalog_schema_version": {"type": "int", "required": False},
        },
        supports_check_mode=False,
    )
    repository = ImageGroupDictionaryRepository(
        module.params["dictionary_path"]
    )

    try:
        operation = module.params["operation"]
        if operation == "lookup":
            result = repository.lookup_many(module.params["candidates"])
            module.exit_json(
                changed=bool(result["hits"]),
                **result,
                dictionary_warnings=_warning_list(repository),
            )
        if operation == "upsert":
            count = repository.upsert(
                module.params["entries"],
                module.params["catalog_schema_version"],
            )
            module.exit_json(
                changed=count > 0,
                updated=count,
                dictionary_warnings=_warning_list(repository),
            )

        image_group_id = module.params["image_group_id"]
        if not image_group_id:
            module.fail_json(msg="image_group_id is required for prune")
        removed = repository.prune(image_group_id)
        module.exit_json(
            changed=removed > 0,
            removed=removed,
            dictionary_warnings=_warning_list(repository),
        )
    except (OSError, ValueError) as exc:
        module.fail_json(msg=f"Image-group dictionary operation failed: {exc}")


if __name__ == "__main__":
    main()
