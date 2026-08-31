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
#!/usr/bin/python
# pylint: disable=import-error,no-name-in-module,line-too-long,too-many-locals
"""
Ansible module to bulk-update /etc/hosts across multiple remote hosts
in parallel via SSH.

Designed for HPC clusters with 500-2000 nodes where serial Ansible
loops are prohibitively slow.  This module is responsible ONLY for
/etc/hosts management.  Munge key status is handled separately in
the calling playbook tasks.

Usage in playbook:
  bulk_update_hosts:
    hosts: "{{ reachable_hosts }}"
    ip_name_map: "{{ ip_name_map }}"
    ssh_key_path: "/root/.ssh/oim_rsa"
    nodes_to_remove: []
    ssh_max_parallel: 20
    ssh_connect_timeout: 10
  register: bulk_update_result
"""
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from ansible.module_utils.basic import AnsibleModule


# ─── Hosts-file content generation ──────────────────────────────────────────

def _build_hosts_block(ip_name_map):
    """Build the OMNIA MANAGED HOSTS block content.

    Returns a string containing the full managed block including markers.
    Sorted by hostname for deterministic output.
    """
    lines = ["# BEGIN OMNIA MANAGED HOSTS"]
    for hostname in sorted(ip_name_map.keys()):
        ip_addr = ip_name_map[hostname]
        lines.append(f"{ip_addr} {hostname}")
    lines.append("# END OMNIA MANAGED HOSTS")
    return "\n".join(lines)


def _build_cleanup_sed(ip_name_map, nodes_to_remove):
    """Build sed commands to remove stale /etc/hosts entries.

    Cleans up:
      - Old managed block markers and content
      - Unmanaged entries matching Omnia node IPs or hostnames
      - Entries for explicitly removed nodes
    """
    all_ips = list(ip_name_map.values())
    all_names = list(ip_name_map.keys()) + list(nodes_to_remove or [])

    cmds = [
        # Remove old managed block markers and content (idempotent)
        "sed -i '/^# BEGIN OMNIA MANAGED HOSTS$/,/^# END OMNIA MANAGED HOSTS$/d' /etc/hosts 2>/dev/null || true",
    ]
    if all_ips:
        ip_pattern = "|".join(_regex_escape(ip) for ip in all_ips)
        cmds.append(
            f"sed -i -E '/^({ip_pattern})[[:space:]]/d' /etc/hosts 2>/dev/null || true"
        )
    if all_names:
        name_pattern = "|".join(all_names)
        cmds.append(
            f"sed -i -E '/[[:space:]]({name_pattern})$/d' /etc/hosts 2>/dev/null || true"
        )
    return "\n".join(cmds)


def _regex_escape(text):
    """Escape regex special characters in a string for sed patterns."""
    special = r'\.^$*+?{}[]|()'
    return "".join(f"\\{c}" if c in special else c for c in text)


# ─── Remote execution ──────────────────────────────────────────────────────

def _ssh_run(host, script, ssh_key_path, ssh_connect_timeout):
    """Execute a script on a remote host via SSH.

    Returns (host, success, stdout, stderr).
    """
    cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", f"ConnectTimeout={ssh_connect_timeout}",
        "-o", "BatchMode=yes",
        "-o", "LogLevel=ERROR",
        "-i", ssh_key_path,
        f"root@{host}",
        "bash -s",
    ]
    try:
        result = subprocess.run(
            cmd,
            input=script,
            capture_output=True,
            text=True,
            timeout=ssh_connect_timeout + 30,
            check=False,
        )
        return (host, result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (host, False, "", f"SSH timeout after {ssh_connect_timeout + 30}s")
    except Exception as exc:  # pylint: disable=broad-except
        return (host, False, "", str(exc))


def _update_single_host(host, cleanup_sed, hosts_block, ssh_key_path,
                        ssh_connect_timeout):
    """Update /etc/hosts on a single remote host.

    Steps:
      1. Run sed cleanup to remove stale entries
      2. Append the new managed hosts block
    """
    script = f"""set -o pipefail
{cleanup_sed}
cat >> /etc/hosts << 'OMNIA_HOSTS_EOF'
{hosts_block}
OMNIA_HOSTS_EOF
"""
    return _ssh_run(host, script, ssh_key_path, ssh_connect_timeout)


# ─── Main module ────────────────────────────────────────────────────────────

def run_module():
    """Ansible module entry point."""
    module_args = {
        "hosts": {"type": "list", "required": True, "elements": "str"},
        "ip_name_map": {"type": "dict", "required": True},
        "ssh_key_path": {"type": "str", "required": True},
        "nodes_to_remove": {
            "type": "list", "required": False, "default": [],
            "elements": "str",
        },
        "ssh_max_parallel": {
            "type": "int", "required": False, "default": 20,
        },
        "ssh_connect_timeout": {
            "type": "int", "required": False, "default": 10,
        },
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    hosts = module.params["hosts"]
    ip_name_map = module.params["ip_name_map"]
    ssh_key_path = module.params["ssh_key_path"]
    nodes_to_remove = module.params["nodes_to_remove"]
    ssh_max_parallel = module.params["ssh_max_parallel"]
    ssh_connect_timeout = module.params["ssh_connect_timeout"]

    result = {
        "changed": False,
        "hosts_updated": [],
        "hosts_failed": [],
        "total_hosts": len(hosts),
        "per_host_results": {},
    }

    if module.check_mode:
        result["changed"] = len(hosts) > 0
        module.exit_json(**result)

    if not hosts:
        module.exit_json(**result)

    # Build content once (same for every node)
    hosts_block = _build_hosts_block(ip_name_map)
    cleanup_sed = _build_cleanup_sed(ip_name_map, nodes_to_remove)

    # Parallel SSH execution
    with ThreadPoolExecutor(max_workers=min(ssh_max_parallel, len(hosts))) as pool:
        futures = {
            pool.submit(
                _update_single_host,
                host, cleanup_sed, hosts_block,
                ssh_key_path, ssh_connect_timeout,
            ): host
            for host in hosts
        }

        for future in as_completed(futures):
            host = futures[future]
            try:
                _, success, stdout, stderr = future.result()
                result["per_host_results"][host] = {
                    "success": success,
                    "stdout": stdout.strip() if stdout else "",
                    "stderr": stderr.strip() if stderr else "",
                }
                if success:
                    result["hosts_updated"].append(host)
                else:
                    result["hosts_failed"].append(host)
            except Exception as exc:  # pylint: disable=broad-except
                result["per_host_results"][host] = {
                    "success": False,
                    "stdout": "",
                    "stderr": str(exc),
                }
                result["hosts_failed"].append(host)

    result["changed"] = len(result["hosts_updated"]) > 0

    if result["hosts_failed"]:
        module.warn(
            f"Failed to update /etc/hosts on {len(result['hosts_failed'])} host(s): "
            f"{', '.join(result['hosts_failed'])}"
        )

    module.exit_json(**result)


def main():
    """Module entry point."""
    run_module()


if __name__ == "__main__":
    main()
