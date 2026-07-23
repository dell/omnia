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
__metaclass__ = type

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
        description: Cluster OS type (rhel, rocky, etc.)
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

import json
import os
import re
import subprocess
from urllib.parse import urlparse, urlunparse
from ansible.module_utils.basic import AnsibleModule

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class LocalRepoAccessGenerator:
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

        self.base_url = "{}://{}:{}".format(
            self.pulp_protocol, self.pulp_server_ip, self.pulp_server_port
        )
        self.rpm_distributions = []
        self.file_distributions = []
        self.python_distributions = []

    def run_pulp_command(self, cmd):
        """Run a pulp CLI command and return JSON output."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
            return []
        except Exception:
            return []

    def fetch_distributions(self):
        """Fetch all relevant distributions from Pulp."""
        self.rpm_distributions = self.run_pulp_command(
            "/usr/local/bin/pulp rpm distribution list 2>/dev/null"
        )
        self.file_distributions = self.run_pulp_command(
            "/usr/local/bin/pulp file distribution list 2>/dev/null"
        )
        self.python_distributions = self.run_pulp_command(
            "/usr/local/bin/pulp python distribution list 2>/dev/null"
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
            netloc = "{}:{}".format(self.pulp_server_ip, self.pulp_server_port)
            parsed = parsed._replace(netloc=netloc)
            base_url = urlunparse(parsed)
        return base_url.rstrip('/') + '/'

    @staticmethod
    def _yaml_key(name):
        """Convert a repository/package name to a YAML-friendly key."""
        key = re.sub(r'[^0-9a-zA-Z_]', '_', name)
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

    def parse_rpm_distributions(self):
        """Parse RPM distributions by reading their base_path."""
        rpm_repos = {'x86_64': {}, 'aarch64': {}}

        for dist in self.rpm_distributions:
            base_url = dist.get('base_url', '')
            base_path = dist.get('base_path', '')
            name = dist.get('name', '')

            if not base_url:
                continue

            parsed = self._parse_base_path(base_path)
            if parsed and parsed['content_type'] == 'rpms':
                arch = parsed['arch']
                rest = parsed['rest']
                if not rest:
                    continue
                repo_name = rest[0]
                if len(rest) > 1:
                    repo_name = '{}_{}'.format(repo_name, '/'.join(rest[1:]))

                # Strip the ``<arch>_<os>_<ver>_`` prefix that some RPM
                # distributions embed in the repo name.
                prefix = "{}_{}_{}_".format(
                    arch, self.cluster_os_type, self.cluster_os_version
                )
                if repo_name.startswith(prefix):
                    repo_name = repo_name[len(prefix):]

                key = self._yaml_key(repo_name)
                if arch in rpm_repos:
                    rpm_repos[arch][key] = self._normalise_base_url(base_url)
                continue

            # Fallback: derive architecture and repo name from the distribution name.
            arch = None
            if name.startswith('x86_64_'):
                arch = 'x86_64'
            elif name.startswith('aarch64_'):
                arch = 'aarch64'
            else:
                continue

            prefix = "{}_{}_{}_".format(
                arch, self.cluster_os_type, self.cluster_os_version
            )
            if name.startswith(prefix):
                repo_name = name[len(prefix):]
            else:
                repo_name = name.split('_', 1)[1] if '_' in name else name

            key = self._yaml_key(repo_name)
            rpm_repos[arch][key] = self._normalise_base_url(base_url)

        return rpm_repos

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
        return "{}://{}:{}/pulp/content/offline_repo/cluster/{}/{}/{}/{}/".format(
            self.pulp_protocol, self.pulp_server_ip, self.pulp_server_port,
            arch, self.cluster_os_type, self.cluster_os_version, content_type
        )

    def _expected_repo_name(self, arch, name):
        """Build the Pulp repository name from config fields."""
        return "{}_{}_{}_{}".format(arch, self.cluster_os_type, self.cluster_os_version, name)

    def _find_pulp_url_for_user_repo(self, rpm_repos, arch, repo_name):
        """Return the Pulp distribution URL for a named user repo if it exists."""
        if arch not in rpm_repos:
            return None

        # Direct key match using the sanitized repo name.
        key = self._yaml_key(repo_name)
        if key in rpm_repos[arch]:
            return rpm_repos[arch][key]

        # Match by the repository name embedded in the distribution base_path.
        expected_name = self._expected_repo_name(arch, repo_name)
        for url in rpm_repos[arch].values():
            parsed = urlparse(url)
            if not parsed.path:
                continue
            path = parsed.path.rstrip('/')
            # Path ends with /rpms/<full_repo_name> or /rpms/<full_repo_name>/<version>
            if path.endswith('/' + expected_name):
                return url
            parts = path.split('/')
            if len(parts) >= 2 and parts[-2] == expected_name:
                return url

        return None

    def load_user_repos(self, rpm_repos=None):
        """Load user-defined repositories from repo_manager_config.yml.

        Maps each user repo name to its Pulp distribution URL. Falls back to
        the original URL from repo_manager_config.yml only when no matching
        Pulp distribution is found.
        """
        user_repos = {'x86_64': {}, 'aarch64': {}}
        rpm_repos = rpm_repos or {}

        if not self.local_repo_config_path or not os.path.exists(self.local_repo_config_path):
            return user_repos

        try:
            with open(self.local_repo_config_path, 'r') as f:
                config = yaml.safe_load(f)

            if not config:
                return user_repos

            for arch in ('x86_64', 'aarch64'):
                for repo in config.get('user_repo_url_{}'.format(arch), []) or []:
                    if not isinstance(repo, dict) or not repo.get('name') or not repo.get('url'):
                        continue
                    pulp_url = self._find_pulp_url_for_user_repo(
                        rpm_repos, arch, repo['name']
                    )
                    user_repos[arch][repo['name']] = pulp_url or repo['url']

        except Exception:
            pass

        return user_repos

    def generate_yaml_content(self):
        """Generate the repo_status.yml content using actual Pulp distribution URLs."""
        self.fetch_distributions()

        rpm_repos = self.parse_rpm_distributions()
        file_repos = self.parse_file_distributions()
        user_repos = self.load_user_repos(rpm_repos)

        data = {
            'overall_status': str(self.overall_status).lower(),
            'cluster_os_type': str(self.cluster_os_type),
            'cluster_os_version': str(self.cluster_os_version),
            'repo_config': str(self.repo_config),
            'repo_manager': {
                'port': self.pulp_server_port,
                'certificates': {
                    'server_crt': '{}/pulp_webserver.crt'.format(self.certs_dir),
                    'server_key': '{}/pulp_webserver.key'.format(self.certs_dir),
                    'certs_dir': self.certs_dir,
                },
            },
            'rpm_repos': rpm_repos,
            'file_repos': file_repos,
            'user_repos': user_repos,
            'tarball_base_url': self._legacy_type_url(file_repos, 'tarball'),
            'manifest_base_url': self._legacy_type_url(file_repos, 'manifest'),
            'pip_base_url': self._legacy_type_url(file_repos, 'pip_module'),
            'git_base_url': self._legacy_type_url(file_repos, 'git'),
            'offline_tarball_path': self._legacy_type_url(file_repos, 'tarball'),
            'offline_manifest_path': self._legacy_type_url(file_repos, 'manifest'),
            'offline_pip_module_path': self._legacy_type_url(file_repos, 'pip_module'),
            'offline_git_path': self._legacy_type_url(file_repos, 'git'),
            'offline_shell_path': self._legacy_type_url(file_repos, 'shell'),
            'offline_iso_path': self._legacy_type_url(file_repos, 'iso'),
            'offline_ansible_galaxy_collection_path': self._legacy_type_url(
                file_repos, 'ansible_galaxy_collection'
            ),
        }

        # Custom YAML dumper that quotes string values but not keys
        class QuotedValueDumper(yaml.SafeDumper):
            pass
        
        def quoted_mapping_representer(dumper, data):
            pairs = []
            for key, value in data.items():
                key_node = dumper.represent_data(key)
                # Force keys to be unquoted (plain style)
                if isinstance(key, str):
                    key_node = dumper.represent_scalar('tag:yaml.org,2002:str', key, style=None)
                value_node = dumper.represent_data(value)
                pairs.append((key_node, value_node))
            return yaml.MappingNode('tag:yaml.org,2002:map', pairs)
        
        def quoted_str_representer(dumper, data):
            # Use double quotes for string values
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
        
        QuotedValueDumper.add_representer(dict, quoted_mapping_representer)
        QuotedValueDumper.add_representer(str, quoted_str_representer)
        
        content = yaml.dump(data, Dumper=QuotedValueDumper, sort_keys=False, default_flow_style=False)
        return content, len(self.rpm_distributions), len(self.file_distributions) + len(self.python_distributions)

    def write_yaml(self, content):
        """Write the YAML content to file."""
        output_dir = os.path.dirname(self.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, mode=0o755)

        with open(self.output_path, 'w') as f:
            f.write(content)

        os.chmod(self.output_path, 0o644)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            pulp_server_ip=dict(type='str', required=True),
            pulp_server_port=dict(type='int', required=True),
            pulp_protocol=dict(type='str', required=True, choices=['http', 'https']),
            cluster_os_type=dict(type='str', required=True),
            cluster_os_version=dict(type='str', required=True),
            output_path=dict(type='str', required=True),
            certs_dir=dict(type='str', required=True),
            local_repo_config_path=dict(type='str', default=''),
            repo_config=dict(type='str', default='partial'),
            overall_status=dict(type='str', default='success')
        ),
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
            msg="Generated repo_status.yml with {} RPM repos and {} file repos".format(
                rpm_count, file_count
            )
        )
    except Exception as e:
        module.fail_json(msg="Failed to generate repo_status.yml: {}".format(str(e)))


if __name__ == '__main__':
    main()
