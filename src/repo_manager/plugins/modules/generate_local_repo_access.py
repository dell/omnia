#!/usr/bin/python3
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
Ansible module to generate repo_status.yml with repository URLs.

The module queries Pulp for RPM, file and Python distributions and builds a
repo_status.yml that reflects the actual Pulp distribution URLs. The offline
content layout is expected to be:

    offline_repo/cluster/<arch>/<os>/<version>/<type>/<package>

For RPM repositories the type is ``rpms`` and ``<package>`` is the repository
name (optionally with a version sub-directory). For other types the final
segment is the package name.
"""

from __future__ import absolute_import, division, print_function

import json
import os
import re
import subprocess
import tempfile

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.path_resolver import get_repo_manager_data_path
from ansible.module_utils.repo_manager.pulp_commands import (
    command_argv,
    pulp_file_commands,
    pulp_python_commands,
    pulp_rpm_commands,
)
from ansible.module_utils.repo_manager.repo_paths import PULP_CLI_EXECUTABLE
from ansible.module_utils.repo_manager.registry_utils import get_registry_authority
from ansible.module_utils.repo_manager.repo_settings import (
    PULP_CONTENT_ROUTE,
    PULP_DISTRIBUTION_ROOT,
    PULP_DISTRIBUTION_ROOT_PARTS,
)
from ansible.module_utils.repo_manager.repository_status_builder import (
    build_terminal_context_status,
    summarize_execution_contexts,
)
from ansible.module_utils.repo_manager.security_utils import (
    normalize_managed_python_distribution_url,
    normalize_pulp_distribution_url,
)

__metaclass__ = type  # pylint: disable=invalid-name

DOCUMENTATION = r'''
---
module: generate_local_repo_access
short_description: Generate repo_status.yml with repository URLs
description:
    - Queries the Pulp CLI to get all available distributions
    - Generates YAML with repository URLs in the required format
    - Marks status failed when catalog-required RPM distributions are missing
options:
    pulp_server_ip:
        description: Pulp server IP address
        required: true
        type: str
    pulp_server_port:
        description: Pulp server port
        required: true
        type: int
    cluster_os_type:
        description: Cluster OS type (rhel)
        required: true
        type: str
    cluster_os_version:
        description: Cluster OS version (10.0, etc.)
        required: true
        type: str
    output_path:
        description: Path to write repo_status.yml
        required: true
        type: str
    local_repo_config_path:
        description: Path to repo_manager_config.yml
        required: false
        type: str
    repo_config:
        description: Repository configuration type (partial, always, on_demand)
        required: false
        type: str
        default: "partial"
    overall_status:
        description: Overall status of the playbook (success/failed)
        required: false
        type: str
        default: "success"
    execution_contexts:
        description: Selected version and architecture contexts from the catalog
        required: false
        type: list
        elements: dict
    execution_results:
        description: Final results for contexts attempted by the download operation
        required: false
        type: list
        elements: dict
    pulp_cli_executable:
        description: Absolute path to the Pulp CLI executable.
        required: false
        type: path

author:
    - Dell Technologies
'''

EXAMPLES = r'''
- name: Generate repo_status.yml
  generate_local_repo_access:
    pulp_server_ip: 192.168.1.100
    pulp_server_port: 2225
    pulp_cli_executable: "{{ pulp_cli_executable }}"
    cluster_os_type: rhel
    cluster_os_version: "9.4"
    repo_config: partial
    output_path: "{{ output_dir }}/repo_status.yml"
    local_repo_config_path: "{{ omnia_base }}/input/repo_manager_config.yml"
'''

RETURN = r'''
rpm_repos_count:
    description: Number of RPM repositories found
    type: int
    returned: success
file_repos_count:
    description: Number of file repositories found
    type: int
    returned: success
repository_ready:
    description: Whether every catalog-required RPM repository has a published URL
    type: bool
    returned: success
missing_rpm_repositories:
    description: Missing RPM repository names grouped by version and architecture
    type: dict
    returned: success
published_status:
    description: Status written to repo_status.yml
    type: str
    returned: success
status_generation_error:
    description: Whether live Pulp status collection failed
    type: bool
    returned: success
msg:
    description: Status message
    type: str
    returned: always
'''

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


DEFAULT_DNF_REPOSITORY_PRIORITY = 99
AGGREGATED_REPOSITORY_NAME = 'repo_manager-additional'


def _validated_priority(value, config_path):
    """Return a valid DNF priority or raise a configuration error."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{config_path}.priority must be an integer")
    if value < 1 or value > 100:
        raise ValueError(f"{config_path}.priority must be between 1 and 100")
    return value


def _repo_version_config(config, cluster_os_version):
    """Return the repository configuration for the requested OS version."""
    repositories = config.get('repositories') or {}
    if not isinstance(repositories, dict):
        return {}
    for version, version_config in repositories.items():
        if str(version) == str(cluster_os_version):
            return version_config if isinstance(version_config, dict) else {}
    return {}


def _build_repo_priority_map(  # pylint: disable=too-many-locals,too-many-branches
        config, cluster_os_version):
    """Map ``(architecture, output repository name)`` to explicit priority.

    Pulp exposes all ``additional_repos`` as one distribution per architecture,
    so those source repositories must resolve to one effective DNF priority.
    """
    priorities = {}
    version_config = _repo_version_config(config, cluster_os_version)

    for arch, arch_config in version_config.items():
        if not isinstance(arch_config, dict):
            continue

        for repo_name, repo_config in arch_config.items():
            repo_path = f"repositories.{cluster_os_version}.{arch}.{repo_name}"
            if repo_name == 'user_repos':
                if not isinstance(repo_config, dict):
                    continue
                for user_name, user_config in repo_config.items():
                    if not isinstance(user_config, dict):
                        continue
                    priority = _validated_priority(
                        user_config.get('priority'), f"{repo_path}.{user_name}"
                    )
                    if priority is not None:
                        priorities[(arch, user_name)] = priority
                continue

            if repo_name == 'additional_repos':
                if not isinstance(repo_config, dict):
                    continue
                effective_priorities = set()
                has_explicit_priority = False
                for additional_name, additional_config in repo_config.items():
                    if not isinstance(additional_config, dict):
                        continue
                    if not str(additional_config.get('url') or '').strip():
                        continue
                    priority = _validated_priority(
                        additional_config.get('priority'),
                        f"{repo_path}.{additional_name}",
                    )
                    if priority is None:
                        effective_priorities.add(DEFAULT_DNF_REPOSITORY_PRIORITY)
                    else:
                        has_explicit_priority = True
                        effective_priorities.add(priority)

                if len(effective_priorities) > 1:
                    values = ', '.join(str(value) for value in sorted(effective_priorities))
                    raise ValueError(
                        f"{repo_path} is published as one Pulp repository and "
                        f"must use one effective priority; found {values}"
                    )
                if has_explicit_priority and effective_priorities:
                    priorities[(arch, AGGREGATED_REPOSITORY_NAME)] = next(
                        iter(effective_priorities)
                    )
                continue

            if not isinstance(repo_config, dict):
                continue
            priority = _validated_priority(repo_config.get('priority'), repo_path)
            if priority is not None:
                priorities[(arch, repo_name)] = priority

    return priorities


class LocalRepoAccessGenerator:  # pylint: disable=too-many-instance-attributes
    """Generate repo_status.yml with repository URLs from Pulp distributions."""

    # Order in which file distributions are grouped for the legacy type-level URLs.
    KNOWN_FILE_TYPES = ('tarball', 'manifest', 'pip_module', 'git', 'iso', 'shell',
                        'ansible_galaxy_collection')

    def __init__(self, module):
        self.module = module
        self.pulp_server_ip = module.params['pulp_server_ip']
        self.pulp_server_port = module.params['pulp_server_port']
        self.pulp_protocol = 'https'
        self.cluster_os_type = module.params['cluster_os_type']
        self.cluster_os_version = module.params['cluster_os_version']
        self.architectures = module.params['architectures']
        self.output_path = module.params['output_path']
        self.pulp_cli_executable = module.params.get(
            'pulp_cli_executable', PULP_CLI_EXECUTABLE
        )
        self.certs_dir = os.path.join(
            get_repo_manager_data_path(), 'pulp_config', 'settings', 'certs'
        )
        self.local_repo_config_path = module.params.get('local_repo_config_path', '')
        self.repo_config = module.params.get('repo_config', 'partial')
        self.overall_status = module.params.get('overall_status', 'success')
        self.execution_contexts = module.params.get('execution_contexts') or [{
            'context_id': f'{self.cluster_os_type}_{self.cluster_os_version}',
            'os_type': self.cluster_os_type,
            'os_version': self.cluster_os_version,
            'architectures': self.architectures,
        }]
        self.execution_results = module.params.get('execution_results') or []

        self.base_url = f"{self.pulp_protocol}://{self.pulp_server_ip}:{self.pulp_server_port}"
        self.rpm_distributions = []
        self.file_distributions = []
        self.python_distributions = []
        self.missing_rpm_repositories = {}
        self.missing_rpm_repositories_by_version = {}
        self._local_repo_config = None

    def run_pulp_command(self, cmd):
        """Run a pulp CLI command and return JSON output."""
        try:
            cmd_list = command_argv(
                cmd, executable=self.pulp_cli_executable
            )
            result = subprocess.run(
                cmd_list,
                shell=False,
                capture_output=True,
                text=True,
                timeout=60,
                check=False
            )
            if result.returncode != 0 or not result.stdout.strip():
                raise ValueError("Pulp distribution query failed")
            payload = json.loads(result.stdout)
            if not isinstance(payload, list):
                raise ValueError("Pulp distribution query returned invalid data")
            return payload
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as error:
            raise ValueError("Pulp distribution query failed") from error

    def fetch_distributions(self):
        """Fetch all relevant distributions from Pulp."""
        self.rpm_distributions = self.run_pulp_command(
            pulp_rpm_commands["list_distributions"]
        )
        self.file_distributions = self.run_pulp_command(
            pulp_file_commands["list_distributions"]
        )
        self.python_distributions = self.run_pulp_command(
            pulp_python_commands["list_distributions"]
        )

    def _normalise_base_url(self, base_url):
        """Return a distribution URL bound to the configured Pulp origin."""
        if not base_url:
            return ''
        return normalize_pulp_distribution_url(base_url, self.base_url)

    def _normalise_python_base_url(self, base_url, base_path):
        """Return a Python distribution URL bound to the public Pulp origin."""
        return normalize_managed_python_distribution_url(
            base_url, base_path, self.base_url
        )

    @staticmethod
    def _yaml_key(name):
        """Convert a repository/package name to a YAML-friendly key.

        Preserves hyphens for readability (e.g., kubernetes-v1-35).
        """
        # Replace characters that are not alphanumeric, underscore, or hyphen
        key = re.sub(r'[^0-9a-zA-Z_\-]', '_', name)
        key = re.sub(r'_+', '_', key)
        return key.strip('_')

    @staticmethod
    def _type_level_url(package_url):
        """Derive the parent type-level URL from a per-package distribution URL.

        Example:
            https://.../pulp/content/offline_repo/cluster/x86_64/rhel/10.0/tarball/geopm/
            -> https://.../pulp/content/offline_repo/cluster/x86_64/rhel/10.0/tarball/
        """
        if not package_url:
            return ''
        stripped = package_url.rstrip('/')
        return stripped[:stripped.rfind('/') + 1]

    def _parse_base_path(self, base_path):
        """Parse a distribution base_path into its components.

        Expected layout: <distribution-root>/<arch>/<os>/<ver>/<type>/[...]
        Returns a dict with arch, os_type, os_version, content_type and
        the trailing segments, or None if the path does not match.
        """
        if not base_path:
            return None
        parts = base_path.strip('/').split('/')
        root_size = len(PULP_DISTRIBUTION_ROOT_PARTS)
        if (
                len(parts) < root_size + 4
                or tuple(parts[:root_size]) != PULP_DISTRIBUTION_ROOT_PARTS
        ):
            return None
        return {
            'arch': parts[root_size],
            'os_type': parts[root_size + 1],
            'os_version': parts[root_size + 2],
            'content_type': parts[root_size + 3],
            'rest': parts[root_size + 4:],
        }

    def _context_values(self, context=None):
        """Return normalized OS, version and architectures for a context."""
        selected_context = context or {}
        return (
            selected_context.get('os_type', self.cluster_os_type),
            str(selected_context.get(
                'os_version', self.cluster_os_version
            )),
            list(selected_context.get(
                'architectures', self.architectures
            )),
        )

    def _extract_repo_name_from_distribution(self, dist, context=None):
        """Extract the repository name from a distribution.

        Returns tuple of (arch, repo_name) or (None, None) if it does not
        belong to the selected catalog context.
        """
        base_url = dist.get('base_url', '')
        base_path = dist.get('base_path', '')
        name = dist.get('name', '')
        selected_os_type, selected_os_version, selected_architectures = (
            self._context_values(context)
        )

        if not base_url:
            return None, None

        # Try to parse from base_path first
        parsed = self._parse_base_path(base_path)
        if parsed and parsed['content_type'] == 'rpms':
            arch = parsed['arch']
            if (arch not in selected_architectures or
                    parsed['os_type'] != selected_os_type or
                    parsed['os_version'] != selected_os_version):
                return None, None
            rest = parsed['rest']
            if not rest:
                return None, None

            # The repo name is the last part of the path
            repo_name = rest[-1] if rest else ''

            # Strip the ``<arch>_<os>_<ver>_`` prefix if present
            prefix = (
                f"{arch}_{selected_os_type}_{selected_os_version}_"
            )
            if repo_name.startswith(prefix):
                repo_name = repo_name[len(prefix):]

            return arch, repo_name

        # Fallback: derive architecture and repo name from the distribution name
        for arch in selected_architectures:
            prefix = f"{arch}_{selected_os_type}_{selected_os_version}_"
            if name.startswith(prefix):
                return arch, name[len(prefix):]
        return None, None

    def parse_rpm_distributions(self, context=None):
        """Parse RPM distributions and return a dict organized by version and arch.

        Returns:
            dict: {
                '<version>': {
                    '<arch>': {
                        '<repo_name>': {'url': '<url>'} or {}
                    }
                }
            }
        """
        _os_type, selected_os_version, selected_architectures = (
            self._context_values(context)
        )
        repositories = {}
        priority_map = _build_repo_priority_map(
            self._load_local_repo_config(), selected_os_version
        )

        for dist in self.rpm_distributions:
            base_url = dist.get('base_url', '')
            arch, repo_name = self._extract_repo_name_from_distribution(
                dist, context
            )

            if not arch or not repo_name:
                continue

            # Use the cluster_os_version as the version key
            version = selected_os_version

            if version not in repositories:
                repositories[version] = {
                    arch: {} for arch in selected_architectures
                }

            if arch not in repositories[version]:
                repositories[version][arch] = {}

            # Use hyphen-friendly key
            key = self._yaml_key(repo_name)
            if base_url:
                repo_output = {'url': self._normalise_base_url(base_url)}
                priority = priority_map.get((arch, repo_name))
                if priority is not None:
                    repo_output['priority'] = priority
                repositories[version][arch][key] = repo_output
            else:
                repositories[version][arch][key] = {}

        # Ensure every catalog-selected architecture exists even if empty.
        if selected_os_version not in repositories:
            repositories[selected_os_version] = {
                arch: {} for arch in selected_architectures
            }

        return repositories

    def find_missing_rpm_repositories(self, repositories, context=None):
        """Return catalog-required repositories missing a published URL.

        Older direct callers may omit ``referenced_repositories`` from their
        execution context. In that compatibility case there is no catalog
        requirement to validate here.
        """
        active_context = context or next(
            (
                item for item in self.execution_contexts
                if str(item.get('os_version')) ==
                str(self.cluster_os_version)
            ),
            {},
        )
        referenced = active_context.get('referenced_repositories')
        if not isinstance(referenced, dict):
            return {}

        selected_os_version = str(
            active_context.get('os_version', self.cluster_os_version)
        )
        selected_architectures = list(
            active_context.get('architectures', self.architectures)
        )
        version_repositories = repositories.get(
            selected_os_version, {}
        )
        missing = {}
        for architecture in selected_architectures:
            required = referenced.get(architecture, [])
            if not isinstance(required, list):
                continue
            published = version_repositories.get(architecture, {})
            available = {
                name for name, repository in published.items()
                if isinstance(repository, dict) and repository.get('url')
            }
            unavailable = [
                name for name in required
                if self._yaml_key(name) not in available
            ]
            if unavailable:
                missing[architecture] = unavailable
        return missing

    def _add_file_distribution(self, file_repos, dist, context=None,
                               python_distribution=False):
        """Add a single file/python distribution to the file_repos map."""
        base_url = dist.get('base_url', '')
        base_path = dist.get('base_path', '')
        selected_os_type, selected_os_version, selected_architectures = (
            self._context_values(context)
        )

        if not base_url:
            return

        parsed = self._parse_base_path(base_path)
        if not parsed:
            return

        arch = parsed['arch']
        if (arch not in selected_architectures or
                parsed['os_type'] != selected_os_type or
                parsed['os_version'] != selected_os_version):
            return
        content_type = parsed['content_type']
        if arch not in file_repos:
            file_repos[arch] = {}
        if content_type not in file_repos[arch]:
            file_repos[arch][content_type] = {}

        package_name = '/'.join(parsed['rest']) if parsed['rest'] else ''
        if package_name:
            key = self._yaml_key(package_name)
            if python_distribution:
                file_repos[arch][content_type][key] = (
                    self._normalise_python_base_url(
                        base_url, base_path
                    )
                )
            else:
                file_repos[arch][content_type][key] = (
                    self._normalise_base_url(base_url)
                )

    def parse_file_distributions(self, context=None):
        """Parse file and python distributions by base_path."""
        _os_type, _os_version, selected_architectures = (
            self._context_values(context)
        )
        file_repos = {arch: {} for arch in selected_architectures}

        for dist in self.file_distributions:
            self._add_file_distribution(file_repos, dist, context)

        # Pulp python distributions are stored under the pip_module type.
        for dist in self.python_distributions:
            self._add_file_distribution(
                file_repos, dist, context, python_distribution=True
            )

        return file_repos

    def _legacy_type_url(self, file_repos, content_type, os_version=None,
                         architectures=None):
        """Return the primary-context type-level URL for compatibility."""
        selected_architectures = architectures or self.architectures
        selected_version = os_version or self.cluster_os_version
        arch = selected_architectures[0]
        if arch in file_repos and content_type in file_repos[arch]:
            for package_url in file_repos[arch][content_type].values():
                return self._type_level_url(package_url)
        return (
            f"{self.pulp_protocol}://{self.pulp_server_ip}:{self.pulp_server_port}"
            f"{PULP_CONTENT_ROUTE}/{PULP_DISTRIBUTION_ROOT}/{arch}/"
            f"{self.cluster_os_type}"
            f"/{selected_version}/{content_type}/"
        )

    def _load_local_repo_config(self):
        """Load and cache repo_manager_config.yml without exposing credentials."""
        if self._local_repo_config is not None:
            return self._local_repo_config

        self._local_repo_config = {}
        if not self.local_repo_config_path or not os.path.exists(self.local_repo_config_path):
            return self._local_repo_config

        try:
            with open(self.local_repo_config_path, 'r', encoding='utf-8') as config_file:
                config = yaml.safe_load(config_file)
            if isinstance(config, dict):
                self._local_repo_config = config
        except (OSError, yaml.YAMLError):
            # Preserve the existing status-generation behavior when the optional
            # source configuration cannot be read.
            self._local_repo_config = {}

        return self._local_repo_config

    def load_user_registries(self):
        """Load user registry configurations from repo_manager_config.yml.

        Returns:
            dict: Registry configurations with TLS settings
        """
        registries = {}

        config = self._load_local_repo_config()
        configured_registries = config.get('registries') or {}
        for name, registry in configured_registries.items():
            if not isinstance(registry, dict):
                continue

            registry_config = {
                'base_url': registry.get('base_url', ''),
                'port': registry.get('port'),
                'host': get_registry_authority(registry),
            }
            tls_config = registry.get('tls') or {}
            if tls_config:
                # repo_status.yml is world-readable operational output. Keep
                # only the non-path setting required to describe reachability;
                # client-key and certificate paths remain internal inputs.
                registry_config['tls'] = {
                    'insecure': bool(tls_config.get('insecure', False)),
                }

            if registry_config:
                registries[name] = registry_config

        return registries

    def _empty_repository_map(self):
        """Return selected version/architecture keys without consumable URLs."""
        return {
            str(context['os_version']): {
                architecture: {}
                for architecture in context['architectures']
            }
            for context in self.execution_contexts
        }

    def _build_status_data(self, overall_status, status_by_version,
                           repositories):
        """Build fields common to successful and failed status documents."""
        primary_context = self.execution_contexts[0]
        return {
            'overall_status': overall_status,
            'cluster_os_type': str(primary_context['os_type']),
            'repo_config': str(self.repo_config),
            'execution_contexts': summarize_execution_contexts(
                self.execution_contexts
            ),
            'overall_status_by_version': status_by_version,
            'repo_manager': {
                'port': self.pulp_server_port,
                'certificates': {
                    'server_crt': os.path.join(
                        self.certs_dir, 'pulp_webserver.crt'
                    ),
                    'certs_dir': self.certs_dir,
                }
            },
            'repositories': repositories,
        }

    @staticmethod
    def _dump_yaml(data):
        """Serialize status with the established quoted-value format."""
        class QuotedValueDumper(yaml.SafeDumper):
            """Custom YAML dumper that quotes string values and handles empty dicts."""

        def quoted_mapping_representer(dumper, mapping_data):
            # Empty dict should be rendered as {}
            if not mapping_data:
                return dumper.represent_mapping(
                    'tag:yaml.org,2002:map', mapping_data, flow_style=True
                )

            pairs = []
            for key, value in mapping_data.items():
                key_node = dumper.represent_data(key)
                # Force keys to be unquoted (plain style)
                if isinstance(key, str):
                    key_node = dumper.represent_scalar('tag:yaml.org,2002:str', key, style=None)
                value_node = dumper.represent_data(value)
                pairs.append((key_node, value_node))
            return yaml.MappingNode('tag:yaml.org,2002:map', pairs)

        def quoted_str_representer(dumper, str_data):
            # Use double quotes for string values
            return dumper.represent_scalar('tag:yaml.org,2002:str', str_data, style='"')

        QuotedValueDumper.add_representer(dict, quoted_mapping_representer)
        QuotedValueDumper.add_representer(str, quoted_str_representer)

        return yaml.dump(
            data, Dumper=QuotedValueDumper, sort_keys=False, default_flow_style=False
        )

    def generate_failed_yaml_content(self):
        """Generate a fail-closed status without publishing repository URLs."""
        status_by_version, _aggregate_status = build_terminal_context_status(
            self.execution_contexts,
            self.execution_results,
            'failed',
        )
        for version in self.missing_rpm_repositories_by_version:
            status_by_version[str(version)] = 'failed'
        data = self._build_status_data(
            'failed', status_by_version, self._empty_repository_map()
        )
        for field_name in (
                'tarball_base_url', 'manifest_base_url', 'pip_base_url',
                'git_base_url', 'offline_tarball_path',
                'offline_manifest_path', 'offline_pip_module_path',
                'offline_git_path', 'offline_shell_path', 'offline_iso_path',
                'offline_ansible_galaxy_collection_path'):
            data[field_name] = ''
        return self._dump_yaml(data), 0, 0

    def generate_yaml_content(self):
        """Generate one terminal status from all selected catalog contexts."""
        if str(self.overall_status).lower() != 'success':
            return self.generate_failed_yaml_content()

        self.fetch_distributions()
        repositories = {}
        missing_by_version = {}
        for context in self.execution_contexts:
            context_repositories = self.parse_rpm_distributions(context)
            version = str(context['os_version'])
            repositories[version] = context_repositories[version]
            context_missing = self.find_missing_rpm_repositories(
                context_repositories, context
            )
            if context_missing:
                missing_by_version[version] = context_missing

        self.missing_rpm_repositories = (
            next(iter(missing_by_version.values()), {})
            if len(self.execution_contexts) == 1
            else missing_by_version
        )
        self.missing_rpm_repositories_by_version = missing_by_version
        if missing_by_version:
            return self.generate_failed_yaml_content()

        status_by_version, aggregate_status = build_terminal_context_status(
            self.execution_contexts,
            self.execution_results,
            self.overall_status,
        )
        if aggregate_status != 'success':
            return self.generate_failed_yaml_content()

        primary_context = self.execution_contexts[0]
        primary_file_repos = self.parse_file_distributions(primary_context)
        registries = self.load_user_registries()
        data = self._build_status_data(
            aggregate_status, status_by_version, repositories
        )
        if registries:
            data['registries'] = registries
        if primary_file_repos and any(primary_file_repos.values()):
            data['file_repos'] = primary_file_repos

        legacy_url_args = (
            str(primary_context['os_version']),
            list(primary_context['architectures']),
        )
        data['tarball_base_url'] = self._legacy_type_url(
            primary_file_repos, 'tarball', *legacy_url_args)
        data['manifest_base_url'] = self._legacy_type_url(
            primary_file_repos, 'manifest', *legacy_url_args)
        data['pip_base_url'] = self._legacy_type_url(
            primary_file_repos, 'pip_module', *legacy_url_args)
        data['git_base_url'] = self._legacy_type_url(
            primary_file_repos, 'git', *legacy_url_args)
        data['offline_tarball_path'] = data['tarball_base_url']
        data['offline_manifest_path'] = data['manifest_base_url']
        data['offline_pip_module_path'] = data['pip_base_url']
        data['offline_git_path'] = data['git_base_url']
        data['offline_shell_path'] = self._legacy_type_url(
            primary_file_repos, 'shell', *legacy_url_args)
        data['offline_iso_path'] = self._legacy_type_url(
            primary_file_repos, 'iso', *legacy_url_args)
        data['offline_ansible_galaxy_collection_path'] = self._legacy_type_url(
            primary_file_repos, 'ansible_galaxy_collection', *legacy_url_args
        )

        return (
            self._dump_yaml(data),
            len(self.rpm_distributions),
            len(self.file_distributions) + len(self.python_distributions)
        )

    def write_yaml(self, content):
        """Atomically write validated YAML content to the configured path."""
        output_dir = os.path.dirname(self.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, mode=0o755)

        destination_directory = output_dir or os.curdir
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode='w', encoding='utf-8',
                    dir=destination_directory,
                    prefix=f".{os.path.basename(self.output_path)}.",
                    delete=False) as output_file:
                temporary_path = output_file.name
                output_file.write(content)
                output_file.flush()
                os.fsync(output_file.fileno())
            os.chmod(temporary_path, 0o644)
            os.replace(temporary_path, self.output_path)
            temporary_path = None
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)


def main():
    """Main entry point for the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            'pulp_server_ip': {'type': 'str', 'required': True},
            'pulp_server_port': {'type': 'int', 'required': True},
            'cluster_os_type': {'type': 'str', 'required': True},
            'cluster_os_version': {'type': 'str', 'required': True},
            'architectures': {
                'type': 'list', 'elements': 'str', 'required': True
            },
            'output_path': {'type': 'str', 'required': True},
            'pulp_cli_executable': {
                'type': 'path', 'default': PULP_CLI_EXECUTABLE
            },
            'local_repo_config_path': {'type': 'str', 'default': ''},
            'repo_config': {'type': 'str', 'default': 'partial'},
            'overall_status': {'type': 'str', 'default': 'success'},
            'execution_contexts': {
                'type': 'list', 'elements': 'dict', 'default': []
            },
            'execution_results': {
                'type': 'list', 'elements': 'dict', 'default': []
            },
        },
        supports_check_mode=True
    )

    if not HAS_YAML:
        module.fail_json(msg="PyYAML is required for this module")

    generator = LocalRepoAccessGenerator(module)

    status_generation_error = False
    try:
        try:
            content, rpm_count, file_count = generator.generate_yaml_content()
        except (ValueError, yaml.YAMLError):
            status_generation_error = True
            content, rpm_count, file_count = (
                generator.generate_failed_yaml_content()
            )

        if not module.check_mode:
            generator.write_yaml(content)
        published_status = yaml.safe_load(content)['overall_status']
        repository_ready = (
            published_status == 'success' and not status_generation_error
        )
        module.exit_json(
            changed=not module.check_mode,
            output_file=module.params['output_path'],
            rpm_repos_count=rpm_count,
            file_repos_count=file_count,
            repository_ready=repository_ready,
            missing_rpm_repositories=generator.missing_rpm_repositories,
            published_status=published_status,
            status_generation_error=status_generation_error,
            msg=(
                "Generated terminal repo_status.yml"
                if not status_generation_error
                else "Generated fail-closed repo_status.yml after status collection failure"
            ),
        )
    except (OSError, ValueError, yaml.YAMLError):
        module.fail_json(
            msg="Failed to write terminal repo_status.yml"
        )


if __name__ == '__main__':
    main()
