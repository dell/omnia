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

"""Resolve RHEL subscription repository URLs for one catalog context."""
# pylint: disable=import-error,no-name-in-module

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.rhel_subscription import (
    BUILTIN_REPOSITORIES,
    SubscriptionRepositoryError,
    parse_redhat_repo,
    resolve_subscription_repositories,
)


DOCUMENTATION = r"""
---
module: resolve_rhel_subscription_repositories
short_description: Resolve RHEL subscription repositories for Pulp
description:
  - Resolves catalog-selected repositories against copied RHSM configuration.
  - Prefers EUS unless the effective standard setting requests standard only.
  - Returns Pulp-ready URLs and copied mTLS certificate paths.
version_added: "1.0.0"
options:
  repo_file:
    description: Path to the copied redhat.repo file.
    required: true
    type: path
  certificate_directory:
    description: Protected directory containing copied entitlement certificates.
    required: true
    type: path
  cluster_os_version:
    description: Active RHEL numeric minor version.
    required: true
    type: str
  architectures:
    description: Architectures in the active catalog context.
    required: true
    type: list
    elements: str
  repository_names_by_arch:
    description: Empty-URL repositories requiring subscription discovery.
    required: true
    type: dict
  repository_configurations_by_arch:
    description: Flattened repository configuration for each architecture.
    required: true
    type: dict
  global_standard:
    description: Select standard repositories instead of EUS-first resolution.
    required: false
    type: bool
    default: false
  global_policy:
    description: Global repository policy inherited by repository records.
    required: false
    type: str
    default: partial
    choices: [always, partial]
  global_caching:
    description: Global caching setting inherited by repository records.
    required: false
    type: bool
    default: true
  builtin_repositories:
    description: Backward-compatible logical RHEL subscription repositories.
    required: false
    type: list
    elements: str
author:
  - Dell Technologies (@dell)
"""

EXAMPLES = r"""
- name: Resolve active RHEL subscription repositories
  resolve_rhel_subscription_repositories:
    repo_file: /protected/rhel/redhat.repo
    certificate_directory: /protected/rhel
    cluster_os_version: "10.0"
    architectures: [x86_64]
    repository_names_by_arch:
      x86_64: [baseos, appstream]
    repository_configurations_by_arch:
      x86_64:
        baseos: {}
        appstream: {}
"""

RETURN = r"""
repositories_by_arch:
  description: Pulp-ready subscription repository records by architecture.
  returned: success
  type: dict
unresolved_by_arch:
  description: Repository names not supplied by the selected subscription channel.
  returned: success
  type: dict
"""


def main():
    """Resolve subscription repository records without exposing TLS paths."""
    module = AnsibleModule(
        argument_spec={
            "repo_file": {"type": "path", "required": True},
            "certificate_directory": {"type": "path", "required": True},
            "cluster_os_version": {"type": "str", "required": True},
            "architectures": {
                "type": "list", "elements": "str", "required": True,
            },
            "repository_names_by_arch": {
                "type": "dict", "required": True,
            },
            # Callers protect this mapping with task-level ``no_log``. Marking
            # the nested dictionary itself ``no_log`` makes Ansible redact
            # ordinary scalar values (for example priorities) from returned
            # certificate paths, corrupting valid entitlement filenames.
            "repository_configurations_by_arch": {
                "type": "dict", "required": True,
            },
            "global_standard": {
                "type": "bool", "required": False, "default": False,
            },
            "global_policy": {
                "type": "str", "required": False, "default": "partial",
                "choices": ["always", "partial"],
            },
            "global_caching": {
                "type": "bool", "required": False, "default": True,
            },
            "builtin_repositories": {
                "type": "list", "elements": "str", "required": False,
                "default": list(BUILTIN_REPOSITORIES),
            },
        },
        supports_check_mode=True,
    )

    try:
        repo_sections = parse_redhat_repo(module.params["repo_file"])
        repositories, unresolved = resolve_subscription_repositories(
            repo_sections=repo_sections,
            certificate_directory=module.params["certificate_directory"],
            os_version=module.params["cluster_os_version"],
            architectures=module.params["architectures"],
            repository_names_by_arch=module.params[
                "repository_names_by_arch"
            ],
            repository_configurations_by_arch=module.params[
                "repository_configurations_by_arch"
            ],
            global_standard=module.params["global_standard"],
            global_policy=module.params["global_policy"],
            global_caching=module.params["global_caching"],
            builtin_repositories=module.params["builtin_repositories"],
        )
    except (SubscriptionRepositoryError, TypeError, ValueError):
        module.fail_json(
            msg="RHEL subscription repositories could not be resolved safely"
        )

    module.exit_json(
        changed=False,
        repositories_by_arch=repositories,
        unresolved_by_arch=unresolved,
    )


if __name__ == "__main__":
    main()
