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
Build Stream — Precheck Verification Functions.

Mirror the checks of ``build_stream.yml --tags precheck`` (role
``precheck_build_stream``), one result per test case:

  environment   omnia.env variables, OIM hostname/domain, admin IPv4
  data path     no NFS export lets remote root write OMNIA_DATA_PATH
  containers    pulp, minio-server and registry running
  credentials   repo_manager and image_build_manager credential stores
  domain files  per domain: credential store, vault key and every input
                file build_stream.yml --tags execute uploads to GitLab
"""

import ipaddress
import re
from typing import Any, Dict, List

from omnia_auto import read_remote_env

from library.functions.probe_func import (
    Probe,
    container_running,
    domain_input_path,
    env_var_set,
    file_present,
    run_cmd,
    summarize_probes,
)
from library.vars.common_vars import (
    ENV_OMNIA_DATA_PATH,
    GITLAB_UPLOADED_INPUT_FILES,
    PREPARE_BASE_CREDENTIAL_FILES,
    ENV_SYSTEM_ADMIN_IPV4,
    ENV_SYSTEM_DOMAIN_NAME,
    ENV_SYSTEM_HOSTNAME,
    NFS_NO_ROOT_SQUASH,
    PRECHECK_REQUIRED_CONTAINERS,
    PRECHECK_REQUIRED_CREDENTIALS,
    PRECHECK_REQUIRED_ENV_VARS,
)

_IPV4_CIDR = re.compile(r"inet (\d+\.\d+\.\d+\.\d+)/")


def check_precheck_environment(host: Any) -> Dict[str, Any]:
    """Verify omnia.env sets every variable the precheck reads.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    return summarize_probes("environment",
                            [env_var_set(host, name) for name in PRECHECK_REQUIRED_ENV_VARS])


def _identity_probe(host: Any, env_name: str, cmd_key: str, label: str) -> Probe:
    """Compare one omnia.env identity value with the OIM."""
    try:
        expected = read_remote_env(host, env_name)
    except ValueError:
        return f"{env_name} vs {label}", "omnia.env value NOT SET", False
    result = run_cmd(host, cmd_key)
    actual = result.stdout.strip() if result.rc == 0 else ""
    ok = actual == expected
    state = f"{actual}" if ok else f"MISMATCH (omnia.env={expected!r}, {label}={actual!r})"
    return f"{env_name} vs {label}", state, ok


def check_precheck_oim_identity(host: Any) -> Dict[str, Any]:
    """Verify hostname -s and hostname -d match SYSTEM_HOSTNAME/SYSTEM_DOMAIN_NAME.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    return summarize_probes("oim_identity", [
        _identity_probe(host, ENV_SYSTEM_HOSTNAME, "hostname_short", "hostname -s"),
        _identity_probe(host, ENV_SYSTEM_DOMAIN_NAME, "hostname_domain", "hostname -d"),
    ])


def check_precheck_admin_ipv4(host: Any) -> Dict[str, Any]:
    """Verify SYSTEM_ADMIN_NIC_IPV4 is assigned to a global interface on the OIM.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    try:
        expected = str(ipaddress.IPv4Address(read_remote_env(host, ENV_SYSTEM_ADMIN_IPV4)))
    except (ipaddress.AddressValueError, ValueError) as exc:
        return summarize_probes("admin_ipv4", [(ENV_SYSTEM_ADMIN_IPV4, str(exc), False)])
    result = run_cmd(host, "local_ipv4")
    addresses = sorted(set(_IPV4_CIDR.findall(result.stdout)))
    assigned = result.rc == 0 and expected in addresses
    return summarize_probes("admin_ipv4", [
        (ENV_SYSTEM_ADMIN_IPV4, expected, True),
        ("Global IPv4 addresses", ", ".join(addresses) or "none", True),
        (f"{expected} assigned", "yes" if assigned else "NOT ASSIGNED", assigned),
    ])


def _unsafe_exports(exports: str, data_path: str) -> List[str]:
    """Return exports with no_root_squash that cover or sit inside data_path."""
    unsafe = []
    for line in exports.splitlines():
        parts = line.split()
        if len(parts) < 2 or NFS_NO_ROOT_SQUASH not in line:
            continue
        export = parts[0].rstrip("/") or "/"
        if (data_path == export or data_path.startswith(f"{export.rstrip('/')}/")
                or export.startswith(f"{data_path}/")):
            unsafe.append(export)
    return unsafe


def check_precheck_data_path_export(host: Any) -> Dict[str, Any]:
    """Verify no NFS export lets remote root write OMNIA_DATA_PATH.

    The playbook watcher runs requests from the queue under the data path as
    root, so an export with no_root_squash on it, a parent or a child fails.
    An NFS-mounted data path is reported (the product only warns).

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    probe = env_var_set(host, ENV_OMNIA_DATA_PATH)
    if not probe[2]:
        return summarize_probes("data_path_export", [probe])
    resolved = run_cmd(host, "realpath", path=probe[1])
    data_path = resolved.stdout.strip() if resolved.rc == 0 else probe[1].rstrip("/")
    unsafe = _unsafe_exports(run_cmd(host, "nfs_exports").stdout, data_path)
    fstype = run_cmd(host, "path_fstype", path=data_path).stdout.strip() or "unknown"
    return summarize_probes("data_path_export", [
        ("OMNIA_DATA_PATH (resolved)", data_path, True),
        ("Filesystem type", f"{fstype} (NFS mount: ensure root_squash)"
         if fstype.startswith("nfs") else fstype, True),
        (f"Exports with {NFS_NO_ROOT_SQUASH}", ", ".join(unsafe) or "none", not unsafe),
    ])


def check_precheck_containers(host: Any) -> Dict[str, Any]:
    """Verify the prerequisite containers (pulp, minio-server, registry) run.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    return summarize_probes("containers",
                            [container_running(host, name)
                             for name in PRECHECK_REQUIRED_CONTAINERS])


def check_precheck_credentials(host: Any) -> Dict[str, Any]:
    """Verify the repo_manager and image_build_manager credential stores exist.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    probes: List[Probe] = []
    for domain, filename in PRECHECK_REQUIRED_CREDENTIALS.items():
        try:
            probes.append(file_present(host, f"{domain_input_path(host, domain)}/{filename}"))
        except ValueError as exc:
            probes.append((f"{domain} credentials", str(exc), False))
    return summarize_probes("credentials", probes)


def check_precheck_domain_files(host: Any, domain: str) -> Dict[str, Any]:
    """Verify one domain's credential store, vault key and GitLab input files.

    The files are the ones ``build_stream.yml --tags execute`` uploads to
    ``input/<domain>/`` in GitLab, which the pipelines then read.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    try:
        input_dir = domain_input_path(host, domain)
    except ValueError as exc:
        return summarize_probes(domain, [(f"{domain} input directory", str(exc), False)])
    names = [*PREPARE_BASE_CREDENTIAL_FILES[domain], *GITLAB_UPLOADED_INPUT_FILES[domain]]
    return summarize_probes(domain, [file_present(host, f"{input_dir}/{name}") for name in names])
