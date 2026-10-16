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
Infrastructure Utilities for System Tests.

Reads the real `orchestrator_inventory.yml` produced by the Orchestrator
domain and drives the actual cluster (Kubernetes control plane, Slurm
control node, and individual functional-group nodes) over SSH. `kubectl`
and `sinfo`/`scontrol`/`sbatch` are not installed on the OIM/test-runner
host itself -- they only exist on the Kubernetes control-plane node and the
Slurm control node respectively, so all cluster-wide commands are executed
there via SSH, mirroring how the FVT suite's `host` fixture + remote
command helpers reach the real infrastructure (see
`orchestrator/library/functions/_pxeboot_helpers.py::remote_command`).
"""

import os
import subprocess
import time
import yaml
from typing import Dict, List, Tuple, Optional


OMNIA_DATA_PATH = os.getenv("OMNIA_DATA_PATH", "/opt/omnia")
OMNIA_PROJECT_NAME = os.getenv("OMNIA_PROJECT_NAME", "project_default")

DEFAULT_INVENTORY_PATH = os.getenv(
    "ORCHESTRATOR_INVENTORY_PATH",
    os.path.join(OMNIA_DATA_PATH, "orchestrator/output", OMNIA_PROJECT_NAME, "orchestrator_inventory.yml"),
)

# Substrings used to classify functional-group names found in the inventory.
KUBE_CONTROL_FIRST_HINT = "kube_control_plane_first"
KUBE_CONTROL_HINT = "kube_control_plane"
KUBE_NODE_HINT = "kube_node"
SLURM_CONTROL_HINT = "slurm_control_node"
SLURM_NODE_HINT = "slurm_node"
GPU_HINT = "gpu"
RHEL_10_0_HINT = "rhel_10_0"
RHEL_10_2_HINT = "rhel_10_2"


class InfrastructureUtils:
    """Utilities for executing commands against the real Omnia cluster."""

    _inventory_cache: Optional[dict] = None
    _inventory_path_cache: Optional[str] = None

    # ------------------------------------------------------------------
    # Inventory loading
    # ------------------------------------------------------------------

    @classmethod
    def load_inventory(cls, inventory_path: str = None) -> dict:
        """Load (and cache) the orchestrator_inventory.yml contents."""
        path = inventory_path or DEFAULT_INVENTORY_PATH
        if cls._inventory_cache is not None and cls._inventory_path_cache == path:
            return cls._inventory_cache
        if not os.path.exists(path):
            cls._inventory_cache = {}
            cls._inventory_path_cache = path
            return {}
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        cls._inventory_cache = data
        cls._inventory_path_cache = path
        return data

    @classmethod
    def get_groups(cls, inventory_path: str = None) -> Dict[str, Dict[str, dict]]:
        """Return {group_name: {hostname: host_vars}} from the inventory."""
        inventory = cls.load_inventory(inventory_path)
        children = (inventory.get("all") or {}).get("children") or {}
        groups = {}
        for group_name, group_data in children.items():
            hosts = (group_data or {}).get("hosts") or {}
            groups[group_name] = hosts
        return groups

    @classmethod
    def find_groups(cls, hint: str) -> List[str]:
        """Return group names whose name contains `hint`."""
        return [g for g in cls.get_groups().keys() if hint in g]

    @classmethod
    def get_group_hosts(cls, hint: str) -> Dict[str, dict]:
        """Return merged {hostname: host_vars} for all groups matching hint."""
        merged = {}
        groups = cls.get_groups()
        for group_name in cls.find_groups(hint):
            merged.update(groups.get(group_name, {}))
        return merged

    @classmethod
    def get_group_addresses(cls, hint: str) -> List[str]:
        """Return ansible_host addresses (fallback to hostnames) for a hint."""
        hosts = cls.get_group_hosts(hint)
        addresses = []
        for hostname, hostvars in hosts.items():
            addresses.append((hostvars or {}).get("ansible_host", hostname))
        return addresses

    @classmethod
    def get_kube_control_plane_host(cls) -> Optional[str]:
        """Return the first Kubernetes control-plane node address."""
        first = cls.get_group_addresses(KUBE_CONTROL_FIRST_HINT)
        if first:
            return first[0]
        control = cls.get_group_addresses(KUBE_CONTROL_HINT)
        return control[0] if control else None

    @classmethod
    def get_slurm_control_host(cls) -> Optional[str]:
        """Return the Slurm controller node address."""
        control = cls.get_group_addresses(SLURM_CONTROL_HINT)
        return control[0] if control else None

    @classmethod
    def get_kube_worker_hosts(cls) -> List[str]:
        return cls.get_group_addresses(KUBE_NODE_HINT)

    @classmethod
    def get_slurm_compute_hosts(cls) -> List[str]:
        return cls.get_group_addresses(SLURM_NODE_HINT)

    @classmethod
    def get_gpu_hosts(cls) -> List[str]:
        """Return addresses of nodes with GPUs.

        First checks inventory group names for a 'gpu' hint.  If none are
        found, probes every managed host for ``nvidia-smi`` (the inventory
        may classify GPU nodes under a generic group name such as
        ``slurm_node_rhel_10_0_x86_64``).  Results are cached.
        """
        if getattr(cls, "_gpu_hosts_cache", None) is not None:
            return cls._gpu_hosts_cache

        # Strategy 1: group-name hint
        groups = cls.get_groups()
        addresses = []
        for group_name in groups:
            if GPU_HINT in group_name.lower():
                addresses.extend(cls.get_group_addresses(group_name))

        if addresses:
            cls._gpu_hosts_cache = addresses
            return addresses

        # Strategy 2: hardware probe via nvidia-smi on all managed hosts
        for host in cls.get_all_managed_hosts():
            rc, stdout, _ = cls.ssh_command(
                host,
                "nvidia-smi --query-gpu=gpu_name --format=csv,noheader 2>/dev/null",
                timeout=10,
            )
            if rc == 0 and stdout.strip():
                addresses.append(host)

        cls._gpu_hosts_cache = addresses
        return addresses

    @classmethod
    def get_rhel_10_0_hosts(cls) -> List[str]:
        groups = cls.get_groups()
        addresses = []
        for group_name in groups:
            if RHEL_10_0_HINT in group_name:
                addresses.extend(cls.get_group_addresses(group_name))
        return addresses

    @classmethod
    def get_rhel_10_2_hosts(cls) -> List[str]:
        groups = cls.get_groups()
        addresses = []
        for group_name in groups:
            if RHEL_10_2_HINT in group_name:
                addresses.extend(cls.get_group_addresses(group_name))
        return addresses

    @classmethod
    def get_all_managed_hosts(cls) -> List[str]:
        """Return every real managed-node address in the inventory
        (excludes the kube-vip helper entry, which is not a real OS node)."""
        groups = cls.get_groups()
        addresses = []
        for group_name, hosts in groups.items():
            if group_name == "kube_vip_group":
                continue
            for hostname, hostvars in hosts.items():
                addresses.append((hostvars or {}).get("ansible_host", hostname))
        return addresses

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    @staticmethod
    def run_command(cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
        """Execute a shell command locally (on the OIM/test-runner host)."""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return -1, "", str(e)

    @staticmethod
    def ssh_command(host: str, cmd: str, user: str = "root",
                     timeout: int = 30) -> Tuple[int, str, str]:
        """Execute a command on a remote node via SSH.

        Uses an argument list (no shell=True locally) so that single/double
        quotes, parentheses, and pipes inside `cmd` (e.g. kubectl
        jsonpath/custom-columns expressions) reach the remote shell intact
        instead of being mangled by nested local shell quoting.
        """
        if not host:
            return -1, "", "No host provided"
        ssh_argv = [
            "ssh",
            "-o", "ConnectTimeout=5",
            "-o", "StrictHostKeyChecking=no",
            "-o", "BatchMode=yes",
            f"{user}@{host}",
            cmd,
        ]
        try:
            result = subprocess.run(
                ssh_argv, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return -1, "", str(e)

    # ------------------------------------------------------------------
    # Kubernetes (executed on the control-plane node, where kubectl lives)
    # ------------------------------------------------------------------

    @classmethod
    def kubectl(cls, kubectl_args: str, timeout: int = 30) -> Tuple[int, str, str]:
        """Run a kubectl command on the real Kubernetes control-plane node."""
        control_host = cls.get_kube_control_plane_host()
        if not control_host:
            return -1, "", "No Kubernetes control-plane node found in inventory"
        return cls.ssh_command(control_host, f"kubectl {kubectl_args}", timeout=timeout)

    @classmethod
    def kubectl_get_nodes(cls) -> Dict[str, str]:
        """Return {node_name: "True"|"False"} Ready status from the real cluster.

        Parses plain `kubectl get nodes` text output (NAME STATUS ROLES AGE
        VERSION) rather than a JSONPath/custom-columns expression, since the
        latter's parentheses/quotes are awkward to pass intact through SSH's
        single command-string transport.
        """
        rc, stdout, stderr = cls.kubectl("get nodes --no-headers")
        nodes = {}
        if rc == 0:
            for line in stdout.strip().split("\n"):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        status = parts[1]
                        nodes[parts[0]] = "True" if status == "Ready" else "False"
        return nodes

    @classmethod
    def kubectl_get_pods(cls, namespace: str = "default") -> Dict[str, str]:
        """Return {pod_name: status} by parsing plain `kubectl get pods` text.

        Columns are NAME READY STATUS RESTARTS AGE -> STATUS is parts[2].
        """
        rc, stdout, stderr = cls.kubectl(f"get pods -n {namespace} --no-headers")
        pods = {}
        if rc == 0:
            for line in stdout.strip().split("\n"):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        pods[parts[0]] = parts[2]
        return pods

    @classmethod
    def get_kubernetes_version(cls) -> Optional[str]:
        rc, stdout, stderr = cls.kubectl("version --short 2>/dev/null || kubectl version 2>/dev/null")
        if rc == 0 and stdout.strip():
            return stdout.strip()
        return None

    # ------------------------------------------------------------------
    # Slurm (executed on the real Slurm controller node)
    # ------------------------------------------------------------------

    @classmethod
    def slurm_cmd(cls, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """Run a Slurm CLI command on the real Slurm controller node."""
        control_host = cls.get_slurm_control_host()
        if not control_host:
            return -1, "", "No Slurm controller node found in inventory"
        return cls.ssh_command(control_host, command, timeout=timeout)

    @classmethod
    def scontrol_ping(cls) -> bool:
        rc, stdout, stderr = cls.slurm_cmd("scontrol ping")
        return rc == 0 and "UP" in stdout.upper()

    @classmethod
    def sinfo(cls) -> Dict[str, str]:
        """Return {node_name: state} from the real Slurm controller."""
        rc, stdout, stderr = cls.slurm_cmd("sinfo -N -h -o '%N %t'")
        nodes = {}
        if rc == 0:
            for line in stdout.strip().split("\n"):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        nodes[parts[0]] = parts[1]
        return nodes

    @classmethod
    def get_slurm_version(cls) -> Optional[str]:
        rc, stdout, stderr = cls.slurm_cmd("sinfo --version")
        if rc == 0 and stdout.strip():
            return stdout.strip()
        return None

    @classmethod
    def submit_slurm_job(cls, script: str = "sleep 10") -> Optional[str]:
        rc, stdout, stderr = cls.slurm_cmd(
            f"sbatch --wrap=\"{script}\" | grep -oP 'Submitted batch job \\K[0-9]+'"
        )
        if rc == 0 and stdout.strip():
            return stdout.strip()
        return None

    @classmethod
    def wait_for_slurm_job(cls, job_id: str, timeout: int = 60) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            rc, stdout, stderr = cls.slurm_cmd(f"squeue -j {job_id} -h")
            if rc != 0 or not stdout.strip():
                return True
            time.sleep(2)
        return False

    @classmethod
    def sacct(cls, job_id: str) -> Tuple[int, str, str]:
        return cls.slurm_cmd(f"sacct -j {job_id} --format=JobID,State --noheader")

    # ------------------------------------------------------------------
    # Generic per-node checks (direct SSH to the functional-group node)
    # ------------------------------------------------------------------

    @classmethod
    def get_os_version(cls, host: str, user: str = "root") -> Optional[str]:
        rc, stdout, stderr = cls.ssh_command(host, "cat /etc/redhat-release", user)
        return stdout.strip() if rc == 0 else None

    @classmethod
    def get_uptime(cls, host: str, user: str = "root") -> Optional[int]:
        rc, stdout, stderr = cls.ssh_command(
            host, "cat /proc/uptime | awk '{print $1}'", user
        )
        if rc == 0:
            try:
                return int(float(stdout.strip()))
            except ValueError:
                return None
        return None

    @classmethod
    def get_file_checksum(cls, host: str, filepath: str, user: str = "root") -> Optional[str]:
        rc, stdout, stderr = cls.ssh_command(
            host, f"sha256sum {filepath} 2>/dev/null | awk '{{print $1}}'", user
        )
        return stdout.strip() if rc == 0 and stdout.strip() else None

    @classmethod
    def get_nvidia_cuda_version(cls, host: str, user: str = "root") -> Optional[str]:
        rc, stdout, stderr = cls.ssh_command(
            host,
            "nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null",
            user,
        )
        return stdout.strip() if rc == 0 and stdout.strip() else None

    @classmethod
    def check_nfs_mount(cls, host: str, mount_point: str = "/mnt/nfs", user: str = "root") -> bool:
        rc, stdout, stderr = cls.ssh_command(
            host, f"mount | grep -q '{mount_point}' && echo yes || echo no", user
        )
        return rc == 0 and "yes" in stdout

    @classmethod
    def ldapsearch(cls, host: str, query: str = "-s base", user: str = "root") -> bool:
        rc, stdout, stderr = cls.ssh_command(
            host,
            f"ldapsearch -x {query} >/dev/null 2>&1 && echo ok || echo fail",
            user,
        )
        return rc == 0 and "ok" in stdout
