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
import shlex
import subprocess
from urllib.parse import urlparse, urlunparse

from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type  # pylint: disable=invalid-name

DOCUMENTATION = r'''
---
module: generate_local_repo_access
short_description: Generate repo_status.yml with repository URLs
description:
    - Queries Pulp API to get all available distributions
    - Generates YAML with repository URLs in the required format
options:
    pulp_server_ip:
        description: Pulp server IP address
        required: true
        type: str
    pulp_server_port:
        description: Pulp server port
        required: true
        type: int
    pulp_protocol:
        description: Protocol (http or https)
        required: true
        type: str
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
    certs_dir:
        description: Certificate directory path
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

author:
    - Dell Technologies
'''

EXAMPLES = r'''
- name: Generate repo_status.yml
  generate_local_repo_access:
    pulp_server_ip: 192.168.1.100
    pulp_server_port: 2225
    pulp_protocol: https
    cluster_os_type: rhel
    cluster_os_version: "9.4"
    repo_config: partial
    output_path: "{{ output_dir }}/repo_status.yml"
    certs_dir: /opt/omnia/pulp_config/settings/certs
    local_repo_config_path: /opt/omnia/input/repo_manager_config.yml
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


class LocalRepoAccessGenerator:  # pylint: disable=too-many-instance-attributes
    """Generate repo_status.yml with repository URLs from Pulp distributions."""

    # Order in which file distributions are grouped for the legacy type-level URLs.
    KNOWN_FILE_TYPES = ('tarball', 'manifest', 'pip_module', 'git', 'iso', 'shell',
                        'ansible_galaxy_collection')

    def __init__(self, module):
        self.module = module
        self.pulp_server_ip = module.params['pulp_server_ip']
        self.pulp_server_port = module.params['pulp_server_port']
        self.pulp_protocol = module.params['pulp_protocol']
        self.cluster_os_type = module.params['cluster_os_type']
        self.cluster_os_version = module.params['cluster_os_version']
        self.output_path = module.params['output_path']
        self.certs_dir = module.params['certs_dir']
        self.local_repo_config_path = module.params.get('local_repo_config_path', '')
        self.repo_config = module.params.get('repo_config', 'partial')
        self.overall_status = module.params.get('overall_status', 'success')
        self.ssl_certificates = module.params.get('ssl_certificates', {})

        self.base_url = f"{self.pulp_protocol}://{self.pulp_server_ip}:{self.pulp_server_port}"
        self.rpm_distributions = []
        self.file_distributions = []
        self.python_distributions = []

    def run_pulp_command(self, cmd):
        """Run a pulp CLI command and return JSON output."""
        try:
            # Use shlex.split to safely parse command arguments
            cmd_list = shlex.split(cmd)
            result = subprocess.run(
                cmd_list,
                shell=False,
                capture_output=True,
                text=True,
                timeout=60,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
            return []
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            return []

    def fetch_distributions(self):
        """Fetch all relevant distributions from Pulp."""
        self.rpm_distributions = self.run_pulp_command(
            "/usr/local/bin/pulp rpm distribution list"
        )
        self.file_distributions = self.run_pulp_command(
            "/usr/local/bin/pulp file distribution list"
        )
        self.python_distributions = self.run_pulp_command(
            "/usr/local/bin/pulp python distribution list"
        )

    def _normalise_base_url(self, base_url):
        """Return base_url with exactly one trailing slash.

        Some Pulp plugins (e.g. pulp_python) report a content host of ``pulp``
        instead of the public Pulp server. Rewrite that to the configured Pulp
        server IP and port so cluster nodes can resolve the URL.
        """
        if not base_url:
            return ''
        parsed = urlparse(base_url)
        if parsed.hostname and parsed.hostname.lower() == 'pulp':
            netloc = f"{self.pulp_server_ip}:{self.pulp_server_port}"
            parsed = parsed._replace(netloc=netloc)
            base_url = urlunparse(parsed)
        return base_url.rstrip('/') + '/'

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

        Expected layout: offline_repo/cluster/<arch>/<os>/<ver>/<type>/[...]
        Returns a dict with arch, os_type, os_version, content_type and
        the trailing segments, or None if the path does not match.
        """
        if not base_path:
            return None
        parts = base_path.strip('/').split('/')
        if len(parts) < 6 or parts[0] != 'offline_repo' or parts[1] != 'cluster':
            return None
        return {
            'arch': parts[2],
            'os_type': parts[3],
            'os_version': parts[4],
            'content_type': parts[5],
            'rest': parts[6:],
        }

    def _extract_repo_name_from_distribution(self, dist):
        """Extract the repository name from a distribution.

        Returns tuple of (arch, repo_name) or (None, None) if cannot parse.
        """
        base_url = dist.get('base_url', '')
        base_path = dist.get('base_path', '')
        name = dist.get('name', '')

        if not base_url:
            return None, None

        # Try to parse from base_path first
        parsed = self._parse_base_path(base_path)
        if parsed and parsed['content_type'] == 'rpms':
            arch = parsed['arch']
            rest = parsed['rest']
            if not rest:
                return None, None

            # The repo name is the last part of the path
            repo_name = rest[-1] if rest else ''

            # Strip the ``<arch>_<os>_<ver>_`` prefix if present
            prefix = f"{arch}_{self.cluster_os_type}_{self.cluster_os_version}_"
            if repo_name.startswith(prefix):
                repo_name = repo_name[len(prefix):]

            return arch, repo_name

        # Fallback: derive architecture and repo name from the distribution name
        arch = None
        if name.startswith('x86_64_'):
            arch = 'x86_64'
        elif name.startswith('aarch64_'):
            arch = 'aarch64'
        else:
            return None, None

        prefix = f"{arch}_{self.cluster_os_type}_{self.cluster_os_version}_"
        if name.startswith(prefix):
            repo_name = name[len(prefix):]
        else:
            repo_name = name.split('_', 1)[1] if '_' in name else name

        return arch, repo_name

    def parse_rpm_distributions(self):
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
        repositories = {}

        for dist in self.rpm_distributions:
            base_url = dist.get('base_url', '')
            arch, repo_name = self._extract_repo_name_from_distribution(dist)

            if not arch or not repo_name:
                continue

            # Use the cluster_os_version as the version key
            version = self.cluster_os_version

            if version not in repositories:
                repositories[version] = {'x86_64': {}, 'aarch64': {}}

            if arch not in repositories[version]:
                repositories[version][arch] = {}

            # Use hyphen-friendly key
            key = self._yaml_key(repo_name)
            if base_url:
                repositories[version][arch][key] = {'url': self._normalise_base_url(base_url)}
            else:
                repositories[version][arch][key] = {}

        # Ensure both architectures exist even if empty
        if self.cluster_os_version not in repositories:
            repositories[self.cluster_os_version] = {'x86_64': {}, 'aarch64': {}}

        return repositories

    def _add_file_distribution(self, file_repos, dist):
        """Add a single file/python distribution to the file_repos map."""
        base_url = dist.get('base_url', '')
        base_path = dist.get('base_path', '')

        if not base_url:
            return

        parsed = self._parse_base_path(base_path)
        if not parsed:
            return

        arch = parsed['arch']
        content_type = parsed['content_type']
        rest = parsed['rest']

        if arch not in file_repos:
            file_repos[arch] = {}
        if content_type not in file_repos[arch]:
            file_repos[arch][content_type] = {}

        package_name = '/'.join(rest) if rest else ''
        if package_name:
            key = self._yaml_key(package_name)
            file_repos[arch][content_type][key] = self._normalise_base_url(base_url)

    def parse_file_distributions(self):
        """Parse file and python distributions by base_path."""
        file_repos = {'x86_64': {}, 'aarch64': {}}

        for dist in self.file_distributions:
            self._add_file_distribution(file_repos, dist)

        # Pulp python distributions are stored under the pip_module type.
        for dist in self.python_distributions:
            self._add_file_distribution(file_repos, dist)

        return file_repos

    def _legacy_type_url(self, file_repos, content_type):
        """Return the x86_64 type-level base URL for a content type."""
        arch = 'x86_64'
        if arch in file_repos and content_type in file_repos[arch]:
            for package_url in file_repos[arch][content_type].values():
                return self._type_level_url(package_url)
        return (
            f"{self.pulp_protocol}://{self.pulp_server_ip}:{self.pulp_server_port}"
            f"/pulp/content/offline_repo/cluster/{arch}/{self.cluster_os_type}"
            f"/{self.cluster_os_version}/{content_type}/"
        )

    def load_user_registries(self):
        """Load user registry configurations from repo_manager_config.yml.

        Returns:
            dict: Registry configurations with TLS settings
        """
        registries = {}

        if not self.local_repo_config_path or not os.path.exists(self.local_repo_config_path):
            return registries

        try:
            with open(self.local_repo_config_path, 'r', encoding='utf-8') as config_file:
                config = yaml.safe_load(config_file)

            if not config:
                return registries

            # Load user_registry entries
            user_registries = config.get('user_registry', []) or []
            for reg in user_registries:
                if not isinstance(reg, dict) or not reg.get('name'):
                    continue

                name = reg['name']
                registry_config = {}

                if reg.get('host'):
                    registry_config['host'] = reg['host']
                if reg.get('port'):
                    registry_config['port'] = reg['port']

                # TLS configuration
                tls_config = {}
                if reg.get('cert_path'):
                    tls_config['capath'] = reg['cert_path']
                if reg.get('client_cert_path'):
                    tls_config['clientcertpath'] = reg['client_cert_path']
                if reg.get('client_key_path'):
                    tls_config['clientkeypath'] = reg['client_key_path']
                if 'insecure' in reg:
                    tls_config['insecure'] = reg['insecure']

                if tls_config:
                    registry_config['tls'] = tls_config

                if registry_config:
                    registries[name] = registry_config

        except (OSError, yaml.YAMLError):
            pass

        return registries

    def generate_yaml_content(self):
        """Generate the repo_status.yml content using actual Pulp distribution URLs."""
        self.fetch_distributions()

        repositories = self.parse_rpm_distributions()
        file_repos = self.parse_file_distributions()
        registries = self.load_user_registries()

        # Build the data structure matching the expected format
        data = {
            'overall_status': str(self.overall_status).lower(),
            'cluster_os_type': str(self.cluster_os_type),
            'repo_config': str(self.repo_config),
            'repo_manager': {
                'port': self.pulp_server_port,
                'certificates': {
                    'server_crt': self.ssl_certificates.get(
                        'server_crt', f"{self.certs_dir}/pulp_webserver.crt"
                    ),
                    'server_key': self.ssl_certificates.get(
                        'server_key', f"{self.certs_dir}/pulp_webserver.key"
                    ),
                    'certs_dir': self.ssl_certificates.get('certs_dir', self.certs_dir),
                }
            },
            'repositories': repositories,
        }

        # Add registries section if any exist
        if registries:
            data['registries'] = registries

        # Add file_repos section
        if file_repos and (file_repos.get('x86_64') or file_repos.get('aarch64')):
            data['file_repos'] = file_repos

        # Add legacy base URLs
        data['tarball_base_url'] = self._legacy_type_url(file_repos, 'tarball')
        data['manifest_base_url'] = self._legacy_type_url(file_repos, 'manifest')
        data['pip_base_url'] = self._legacy_type_url(file_repos, 'pip_module')
        data['git_base_url'] = self._legacy_type_url(file_repos, 'git')
        data['offline_tarball_path'] = self._legacy_type_url(file_repos, 'tarball')
        data['offline_manifest_path'] = self._legacy_type_url(file_repos, 'manifest')
        data['offline_pip_module_path'] = self._legacy_type_url(file_repos, 'pip_module')
        data['offline_git_path'] = self._legacy_type_url(file_repos, 'git')
        data['offline_shell_path'] = self._legacy_type_url(file_repos, 'shell')
        data['offline_iso_path'] = self._legacy_type_url(file_repos, 'iso')
        data['offline_ansible_galaxy_collection_path'] = self._legacy_type_url(
            file_repos, 'ansible_galaxy_collection'
        )

        # Custom YAML dumper that quotes string values but not keys
        # and renders empty dicts as {} on same line
        class QuotedValueDumper(yaml.SafeDumper):
            """Custom YAML dumper that quotes string values and handles empty dicts."""

        def quoted_mapping_representer(dumper, mapping_data):
            # Empty dict should be rendered as {}
            if not mapping_data:
                return dumper.represent_mapping('tag:yaml.org,2002:map', mapping_data, flow_style=True)

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

        content = yaml.dump(
            data, Dumper=QuotedValueDumper, sort_keys=False, default_flow_style=False
        )
        return (
            content,
            len(self.rpm_distributions),
            len(self.file_distributions) + len(self.python_distributions)
        )

    def write_yaml(self, content):
        """Write the YAML content to file."""
        output_dir = os.path.dirname(self.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, mode=0o755)

        with open(self.output_path, 'w', encoding='utf-8') as output_file:
            output_file.write(content)

        os.chmod(self.output_path, 0o644)


def main():
    """Main entry point for the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            'pulp_server_ip': {'type': 'str', 'required': True},
            'pulp_server_port': {'type': 'int', 'required': True},
            'pulp_protocol': {'type': 'str', 'required': True, 'choices': ['http', 'https']},
            'cluster_os_type': {'type': 'str', 'required': True},
            'cluster_os_version': {'type': 'str', 'required': True},
            'output_path': {'type': 'str', 'required': True},
            'certs_dir': {'type': 'str', 'required': True},
            'local_repo_config_path': {'type': 'str', 'default': ''},
            'repo_config': {'type': 'str', 'default': 'partial'},
            'overall_status': {'type': 'str', 'default': 'success'},
            'ssl_certificates': {'type': 'dict', 'default': {}}
        },
        supports_check_mode=True
    )

    if not HAS_YAML:
        module.fail_json(msg="PyYAML is required for this module")

    generator = LocalRepoAccessGenerator(module)

    try:
        content, rpm_count, file_count = generator.generate_yaml_content()

        if not module.check_mode:
            generator.write_yaml(content)

        module.exit_json(
            changed=True,
            output_file=module.params['output_path'],
            rpm_repos_count=rpm_count,
            file_repos_count=file_count,
            msg=f"Generated repo_status.yml with {rpm_count} RPM repos and {file_count} file repos"
        )
    except (OSError, yaml.YAMLError) as err:
        module.fail_json(msg=f"Failed to generate repo_status.yml: {str(err)}")


if __name__ == '__main__':
    main()
