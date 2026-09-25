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

"""Immutable contracts for PXE boot and post-boot cluster verification."""

PXEBOOT_STATUS = "pxeboot_status.yml"
OMNIA_CONFIG = "omnia_config.yml"
STORAGE_CONFIG = "storage_config.yml"
ENV_CATALOG_FILE_PATH = "CATALOG_FILE_PATH"

PING_RETRIES = 3
PING_RETRY_DELAY_SECONDS = 5
SSH_RETRIES = 3
SSH_RETRY_DELAY_SECONDS = 10

KUBERNETES_TEST_IMAGE_DEFAULT = "docker.io/library/busybox:1.36"
KUBERNETES_WAIT_TIMEOUT_SECONDS = 300
RECOVERY_WAIT_TIMEOUT_SECONDS = 900
RECOVERY_POLL_SECONDS = 15
SLURM_JOB_TIMEOUT_SECONDS = 180
SLURM_ACCOUNTING_TIMEOUT_SECONDS = 30
SLURM_ACCOUNTING_POLL_SECONDS = 2
SLURM_TEST_JOB_COMMAND = "hostname -s"
SLURM_CONCURRENT_JOB_COMMAND = "sleep 5; hostname -s"
SLURM_QUEUE_HOLDER_COMMAND = "sleep 30; hostname -s"
SLURM_QUEUE_FOLLOWER_COMMAND = "hostname -s"
PAM_ACCESS_SETTLE_SECONDS = 5
PAM_SESSION_TERMINATION_TIMEOUT_SECONDS = 30
SLURM_DRAIN_REASON = "omnia_fvt_validation"
ETCD_RAFT_INDEX_DELTA_MAX = 100
APPTAINER_IMAGE_DIRECTORY = "/hpc_tools/container_images"
APPTAINER_SCRIPT_DIRECTORY = "/hpc_tools/scripts"
APPTAINER_DOWNLOAD_SCRIPT = "/hpc_tools/scripts/download_container_image.sh"
APPTAINER_IMAGE_LIST = "/hpc_tools/scripts/container_image.list"
APPTAINER_DOWNLOAD_TIMEOUT_SECONDS = 1800
LONG_OPERATION_POLL_SECONDS = 20
APPTAINER_DOWNLOAD_MAX_RSS_KIB = 1048576
APPTAINER_JOB_TIMEOUT_SECONDS = 300
APPTAINER_CONCURRENT_JOB_COUNT = 3
APPTAINER_ARRAY_SIZE = 3
APPTAINER_GPU_MEMORY_SETTLE_SECONDS = 5

KUBERNETES_PREFIX = "service_kube_"
KUBERNETES_CONTROL_PLANE_PREFIX = "service_kube_control_plane_"
KUBERNETES_PRIMARY_CONTROL_PLANE_PREFIX = "service_kube_control_plane_first_"
KUBERNETES_NODE_PREFIX = "service_kube_node_"

SLURM_CONTROL_PREFIX = "slurm_control_node_"
SLURM_COMPUTE_PREFIX = "slurm_node_"
SLURM_LOGIN_PREFIX = "login_node_"
SLURM_COMPILER_PREFIX = "login_compiler_node_"
SLURM_LOGIN_PREFIXES: tuple[str, ...] = (
    SLURM_LOGIN_PREFIX,
    SLURM_COMPILER_PREFIX,
)
SLURM_SUBMISSION_PREFIXES: tuple[str, ...] = (
    SLURM_CONTROL_PREFIX,
    *SLURM_LOGIN_PREFIXES,
)
SLURM_PREFIXES: tuple[str, ...] = (
    SLURM_CONTROL_PREFIX,
    SLURM_COMPUTE_PREFIX,
    *SLURM_LOGIN_PREFIXES,
)
CATALOG_ROLE_PREFIXES: tuple[str, ...] = (
    KUBERNETES_CONTROL_PLANE_PREFIX,
    KUBERNETES_NODE_PREFIX,
    *SLURM_PREFIXES,
)

_UCX_DISCOVERY_COMMAND = (
    "for profile in /etc/profile.d/doca_mpi.sh /etc/profile.d/ucx.sh; do "
    'if test -r "$profile"; then . "$profile"; fi; done; '
    'ucx_info_path="$(command -v ucx_info 2>/dev/null || true)"; '
    'if ! test -x "$ucx_info_path"; then '
    "for candidate in "
    "/hpc_tools/benchmarks/ucx/bin/ucx_info "
    "/usr/mpi/gcc/openmpi-4.1.9a1/bin/ucx_info "
    "/opt/mellanox/hpcx/ucx/bin/ucx_info "
    "/opt/mellanox/ucx/bin/ucx_info "
    "/usr/local/bin/ucx_info /usr/bin/ucx_info; do "
    'if test -x "$candidate"; then ucx_info_path="$candidate"; break; fi; '
    "done; fi; "
    'if ! test -x "$ucx_info_path"; then '
    "echo 'ucx_info executable not found in the DOCA, system, or shared-tool "
    "locations' >&2; exit 127; fi; "
    "printf 'UCX_EXECUTABLE|%s\\n' \"$ucx_info_path\"; "
)

_OPENMPI_DISCOVERY_COMMAND = (
    "for profile in /etc/profile.d/doca_mpi.sh /etc/profile.d/openmpi.sh; do "
    'if test -r "$profile"; then . "$profile"; fi; done; '
    'mpirun_path="$(command -v mpirun 2>/dev/null || true)"; '
    'if ! test -x "$mpirun_path"; then '
    "for candidate in "
    "/hpc_tools/benchmarks/openmpi/bin/mpirun "
    "/usr/mpi/gcc/openmpi-4.1.9a1/bin/mpirun "
    "/usr/local/bin/mpirun /usr/bin/mpirun; do "
    'if test -x "$candidate"; then mpirun_path="$candidate"; break; fi; '
    "done; fi; "
    'if ! test -x "$mpirun_path"; then '
    "echo 'mpirun executable not found in the DOCA, system, or shared-tool "
    "locations' >&2; exit 127; fi; "
    'mpicc_path="${mpirun_path%/mpirun}/mpicc"; '
    'if ! test -x "$mpicc_path"; then '
    "echo 'mpicc was not found beside the selected mpirun' >&2; exit 127; fi; "
    "printf 'OPENMPI_EXECUTABLE|%s\\n' \"$mpirun_path\"; "
    "printf 'OPENMPI_COMPILER|%s\\n' \"$mpicc_path\"; "
)

PXEBOOT_COMMANDS: dict[str, str] = {
    "ping": "ping -c 1 -W 2 %s",
    "ssh_probe": "true",
    "cloud_init": (
        "cloud-init status --long; printf '\\n---JSON---\\n'; "
        "cloud-init status --format json"
    ),
    "hostname": "hostname -s",
    "hostname_resolution": "getent ahostsv4 %s",
    "node_services": "systemctl is-active %s",
    "apptainer_runtime": (
        "command -v apptainer >/dev/null 2>&1 && apptainer --version"
    ),
    "apptainer_shared_artifacts": (
        "test -d /hpc_tools/container_images && "
        "test -x /hpc_tools/scripts/download_container_image.sh && "
        "test -r /hpc_tools/scripts/container_image.list && "
        "bash -n /hpc_tools/scripts/download_container_image.sh"
    ),
    "apptainer_shared_mount": "findmnt -n -o SOURCE,FSTYPE,TARGET /hpc_tools",
    "apptainer_find_sif": (
        "find /hpc_tools/container_images -maxdepth 1 -type f "
        "-name '*.sif' -printf '%p|%m|%s|%T@\\n' | sort"
    ),
    "apptainer_inspect": "apptainer inspect %s",
    "apptainer_checksum": "sha256sum %s",
    "apptainer_non_root": ("cd /tmp && runuser -u %s -- apptainer exec %s id -u"),
    "apptainer_ldap_read": "runuser -u %s -- test -r %s",
    "apptainer_exec_hostname": "apptainer exec %s hostname -s",
    "apptainer_download": "timeout %s /hpc_tools/scripts/download_container_image.sh",
    "apptainer_download_memory": (
        "timeout %s /hpc_tools/scripts/download_container_image.sh & "
        "command_pid=$!; peak=0; "
        'while kill -0 "$command_pid" 2>/dev/null; do '
        'rss=$(ps -eo pid=,ppid=,rss= | awk -v root="$command_pid" \''
        "{ parent[$1]=$2; memory[$1]=$3 } "
        "END { for (process in parent) { current=process; seen=0; "
        "while (current in parent && seen++ < 100) { "
        "if (current == root) { total += memory[process]; break } "
        "if (parent[current] == current) break; current=parent[current] } } "
        "print total+0 }'); "
        'if test "$rss" -gt "$peak"; then peak=$rss; fi; sleep 1; done; '
        'wait "$command_pid"; status=$?; '
        'printf \'%%s|%%s\\n\' "$status" "$peak"; exit "$status"'
    ),
    "apptainer_pulp_policy": (
        "grep -Eq 'PULP_SERVER=' /hpc_tools/scripts/download_container_image.sh && "
        "grep -Eq 'PULP_IMAGE=' /hpc_tools/scripts/download_container_image.sh && "
        "test \"$(grep -Ec '^[[:space:]]*timeout .*apptainer pull' "
        '/hpc_tools/scripts/download_container_image.sh)" -eq 1 && '
        "grep -Fq 'apptainer pull' /hpc_tools/scripts/download_container_image.sh && "
        "grep -Fq '$PULP_IMAGE' "
        "/hpc_tools/scripts/download_container_image.sh"
    ),
    "apptainer_missing_image_contract": (
        "grep -Eq 'FAILED_COUNT' /hpc_tools/scripts/download_container_image.sh && "
        "grep -Eq 'exit .*EXIT_CODE' /hpc_tools/scripts/download_container_image.sh"
    ),
    "apptainer_srun": (
        "timeout %s srun --nodes=1 --ntasks=1 --nodelist=%s "
        "apptainer exec %s sh -c "
        '\'printf "OMNIA_JOB_ID=%%s\\n" "$SLURM_JOB_ID"; hostname -s\''
    ),
    "apptainer_srun_non_root": (
        "timeout %s runuser -u %s -- srun --nodes=1 --ntasks=1 "
        "--nodelist=%s apptainer exec %s hostname -s"
    ),
    "apptainer_multi_srun": (
        "timeout %s srun --nodes=%s --ntasks=%s apptainer exec %s hostname -s"
    ),
    "apptainer_srun_nfs": (
        "timeout %s srun --nodes=1 --ntasks=1 --nodelist=%s "
        "apptainer exec --bind /hpc_tools:/hpc_tools %s "
        "test -r /hpc_tools/container_images/%s"
    ),
    "apptainer_srun_environment": (
        "timeout %s srun --nodes=1 --ntasks=1 --nodelist=%s "
        "apptainer exec %s sh -c "
        '\'test -n "$SLURM_JOB_ID" && test -n "$SLURM_NODEID" && '
        'printf "%%s|%%s\\n" "$SLURM_JOB_ID" "$SLURM_NODEID"\''
    ),
    "apptainer_invalid_sif": (
        "timeout %s srun --nodes=1 --ntasks=1 --nodelist=%s "
        "apptainer exec /hpc_tools/container_images/.omnia-invalid.sif true"
    ),
    "apptainer_restricted_prepare": "cp -- %s %s && chmod 0600 %s",
    "apptainer_restricted_cleanup": "rm -f -- %s",
    "apptainer_restricted_exec": "runuser -u nobody -- apptainer exec %s true",
    "apptainer_concurrent_srun": ("timeout %s bash -c %s"),
    "apptainer_array_submit": (
        "timeout %s sbatch --parsable --wait --array=0-%s "
        "--output=/dev/null --error=/dev/null --wrap=%s"
    ),
    "apptainer_process_probe": "pgrep -af %s",
    "apptainer_gpu_host_count": (
        "nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | wc -l"
    ),
    "apptainer_gpu_container_count": (
        "apptainer exec --nv %s sh -c "
        "'nvidia-smi --query-gpu=name --format=csv,noheader | wc -l'"
    ),
    "apptainer_gpu_memory": (
        "nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null"
    ),
    "apptainer_gpu_workload": "apptainer exec --nv %s nvidia-smi -L",
    "apptainer_infiniband": (
        "apptainer exec --bind /dev/infiniband:/dev/infiniband %s "
        "test -d /dev/infiniband"
    ),
    "kubernetes_nodes": (
        "KUBECONFIG=/etc/kubernetes/admin.conf kubectl get nodes -o json"
    ),
    "kubernetes_pods": (
        "KUBECONFIG=/etc/kubernetes/admin.conf kubectl get pods -A -o json"
    ),
    "kubernetes_storage": (
        "KUBECONFIG=/etc/kubernetes/admin.conf "
        "kubectl get storageclass,pv,pvc -A -o json"
    ),
    "kubernetes_readyz": (
        "KUBECONFIG=/etc/kubernetes/admin.conf kubectl get --raw='/readyz?verbose'"
    ),
    "kubernetes_storage_classes": (
        "KUBECONFIG=/etc/kubernetes/admin.conf kubectl get storageclass -o json"
    ),
    "kubernetes_client_version": (
        "KUBECONFIG=/etc/kubernetes/admin.conf kubectl version -o json"
    ),
    "kubeadm_version": "kubeadm version -o short",
    "kubelet_version": "kubelet --version",
    "crio_version": "crio --version",
    "kubernetes_namespace_create": (
        "KUBECONFIG=/etc/kubernetes/admin.conf kubectl create namespace %s"
    ),
    "kubernetes_namespace_delete": (
        "KUBECONFIG=/etc/kubernetes/admin.conf "
        "kubectl delete namespace %s --ignore-not-found=true "
        "--wait=true --timeout=180s"
    ),
    "kubernetes_apply_base64": (
        "printf '%%s' '%s' | base64 -d | "
        "KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f -"
    ),
    "kubernetes_wait_pods": (
        "KUBECONFIG=/etc/kubernetes/admin.conf kubectl wait "
        "--namespace %s --for=condition=Ready pod --all --timeout=%ss"
    ),
    "kubernetes_get_namespace": (
        "KUBECONFIG=/etc/kubernetes/admin.conf "
        "kubectl get pod,pvc --namespace %s -o json"
    ),
    "kubernetes_read_probe": (
        "KUBECONFIG=/etc/kubernetes/admin.conf "
        "kubectl exec --namespace %s workload -- cat /data/probe"
    ),
    "kubernetes_set_test_pv_delete_policy": (
        "KUBECONFIG=/etc/kubernetes/admin.conf "
        "kubectl patch persistentvolume %s --type=merge "
        '--patch \'{"spec":{"persistentVolumeReclaimPolicy":"Delete"}}\''
    ),
    "kubernetes_delete_test_pv": (
        "KUBECONFIG=/etc/kubernetes/admin.conf "
        "kubectl delete persistentvolume %s --ignore-not-found=true "
        "--wait=true --timeout=180s"
    ),
    "kubernetes_etcd_health": (
        "KUBECONFIG=/etc/kubernetes/admin.conf kubectl exec "
        "--namespace kube-system %s -- etcdctl "
        "--endpoints=https://127.0.0.1:2379 "
        "--cacert=/etc/kubernetes/pki/etcd/ca.crt "
        "--cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt "
        "--key=/etc/kubernetes/pki/etcd/healthcheck-client.key "
        "endpoint health --cluster --write-out=json"
    ),
    "kubernetes_etcd_status": (
        "KUBECONFIG=/etc/kubernetes/admin.conf kubectl exec "
        "--namespace kube-system %s -- etcdctl "
        "--endpoints=https://127.0.0.1:2379 "
        "--cacert=/etc/kubernetes/pki/etcd/ca.crt "
        "--cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt "
        "--key=/etc/kubernetes/pki/etcd/healthcheck-client.key "
        "endpoint status --cluster --write-out=json"
    ),
    "kubernetes_etcd_members": (
        "KUBECONFIG=/etc/kubernetes/admin.conf kubectl exec "
        "--namespace kube-system %s -- etcdctl "
        "--endpoints=https://127.0.0.1:2379 "
        "--cacert=/etc/kubernetes/pki/etcd/ca.crt "
        "--cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt "
        "--key=/etc/kubernetes/pki/etcd/healthcheck-client.key "
        "member list --write-out=json"
    ),
    "kubernetes_node_ready": (
        'test "$(KUBECONFIG=/etc/kubernetes/admin.conf kubectl get node %s '
        '-o jsonpath=\'{.status.conditions[?(@.type=="Ready")].status}\')" '
        "= True"
    ),
    "ip_addresses": "ip -j address show",
    "etcd_mount": "findmnt -J /var/lib/etcd",
    "etcd_mount_identity": "findmnt -n -o SOURCE,UUID,FSTYPE /var/lib/etcd",
    "etcd_block_devices": (
        "lsblk -J -b -o NAME,PATH,PKNAME,TYPE,FSTYPE,LABEL,UUID,"
        "MOUNTPOINTS,MODEL,ROTA,TRAN"
    ),
    "etcd_root_source": "findmnt -n -o SOURCE /",
    "etcd_fstab": (
        'awk \'!/^[[:space:]]*#/ && NF >= 4 && $2 == "/var/lib/etcd" '
        '{print $1 "|" $2 "|" $3 "|" $4}\' /etc/fstab'
    ),
    "etcd_permissions": "stat -c '%U|%G|%a' /var/lib/etcd",
    "etcd_manifest_data_dir": (
        "grep -Eq -- '--data-dir(=|[[:space:]]+)/var/lib/etcd([[:space:]]|$)' "
        "/etc/kubernetes/manifests/etcd.yaml"
    ),
    "etcd_boot_log": (
        "stat -c '%Y' /var/log/diskless-etcd-mount.log 2>/dev/null || "
        "stat -c '%Y' /var/log/etcd-disk-setup.log"
    ),
    "node_boot_time": 'date -d "$(uptime -s)" +%s',
    "node_boot_id": "cat /proc/sys/kernel/random/boot_id",
    "slurm_nodes": "scontrol show nodes --oneliner",
    "slurm_partitions": "sinfo --noheader --Node --format='%N|%P|%T|%a'",
    "slurm_node_state": "sinfo --noheader --nodes=%s --format='%T'",
    "slurm_srun_node": (
        "timeout 60 srun --nodes=1 --ntasks=1 --nodelist=%s --immediate=30 "
        '/bin/sh -c \'printf "OMNIA_JOB_ID=%%s\\n" "$SLURM_JOB_ID"; '
        "hostname -s'"
    ),
    "slurm_job_details": (
        "sacct --noheader --parsable2 --jobs=%s --format=State,NodeList | head -1"
    ),
    "slurm_queue_snapshot": "squeue --noheader --format='%i|%T|%N|%R'",
    "slurm_submit_concurrent_job": (
        "sbatch --parsable --nodes=1 --ntasks=1 --exclusive --nodelist=%s "
        "--output=/tmp/omnia-fvt-concurrent-%%j.out "
        "--error=/tmp/omnia-fvt-concurrent-%%j.err "
        f"--wrap='{SLURM_CONCURRENT_JOB_COMMAND}'"
    ),
    "slurm_concurrent_job_stdout": "cat /tmp/omnia-fvt-concurrent-%s.out",
    "slurm_concurrent_job_stderr": "cat /tmp/omnia-fvt-concurrent-%s.err",
    "slurm_cleanup_concurrent_job": (
        "rm -f /tmp/omnia-fvt-concurrent-%s.out /tmp/omnia-fvt-concurrent-%s.err"
    ),
    "slurm_insufficient_resources": (
        "nodes=$(sinfo --noheader --Node | wc -l); "
        "sbatch --immediate=5 --nodes=$((nodes + 1)) --wrap='hostname'"
    ),
    "slurm_submit_drain_job": (
        "job=$(sbatch --parsable --nodelist=%s --wrap='sleep 60'); "
        "job=${job%%;*}; "
        'sleep 3; state=$(squeue --noheader --jobs="$job" --format=%%T); '
        'printf \'%%s|%%s\' "$job" "$state"'
    ),
    "slurm_submit_queue_holder": (
        "sbatch --parsable --nodes=1 --ntasks=1 --exclusive --nodelist=%s "
        "--output=/tmp/omnia-fvt-queue-%%j.out "
        "--error=/tmp/omnia-fvt-queue-%%j.err "
        f"--wrap='{SLURM_QUEUE_HOLDER_COMMAND}'"
    ),
    "slurm_submit_queue_follower": (
        "sbatch --parsable --nodes=1 --ntasks=1 --exclusive --nodelist=%s "
        "--output=/tmp/omnia-fvt-queue-%%j.out "
        "--error=/tmp/omnia-fvt-queue-%%j.err "
        f"--wrap='{SLURM_QUEUE_FOLLOWER_COMMAND}'"
    ),
    "slurm_queue_job_state": "squeue --noheader --jobs=%s --format='%%T|%%R'",
    "slurm_queue_job_stdout": "cat /tmp/omnia-fvt-queue-%s.out",
    "slurm_queue_job_stderr": "cat /tmp/omnia-fvt-queue-%s.err",
    "slurm_cleanup_queue_job": (
        "rm -f /tmp/omnia-fvt-queue-%s.out /tmp/omnia-fvt-queue-%s.err"
    ),
    "slurm_drain_node": ("scontrol update NodeName=%s State=DRAIN Reason=%s"),
    "slurm_resume_node": "scontrol update NodeName=%s State=RESUME",
    "slurm_cancel_job": "scancel %s",
    "slurm_job_accounting": (
        "sacct --noheader --parsable2 --jobs=%s --format=State | head -1"
    ),
    "slurm_user_sbatch": ("su - %s -c \"sbatch --parsable --wait --wrap='hostname'\""),
    "slurm_user_running_jobs": (
        "squeue --noheader --user=%s --states=RUNNING --format='%%i|%%N'"
    ),
    "ldap_missing_identity": "getent passwd %s",
    "cross_node_ssh": (
        "ssh -o BatchMode=yes -o ConnectTimeout=10 "
        "-o StrictHostKeyChecking=accept-new -- root@%s true"
    ),
    "slurm_config": "scontrol show config",
    "slurm_controller_config_files": (
        "for file in slurm slurmdbd cgroup gres acct_gather helpers "
        "job_container mpi oci topology burst_buffer; do "
        "path=/etc/slurm/$file.conf; "
        'if test -f "$path"; then '
        'printf \'%s|%s|\' "$file" "$path"; '
        "sha256sum \"$path\" | cut -d' ' -f1; fi; done"
    ),
    "slurm_client_config_files": (
        "for file in slurm cgroup gres acct_gather helpers "
        "job_container mpi oci topology burst_buffer; do "
        "path=/var/spool/slurmd/conf-cache/$file.conf; "
        'if test -f "$path"; then '
        'printf \'%s|%s|\' "$file" "$path"; '
        "sha256sum \"$path\" | cut -d' ' -f1; fi; done"
    ),
    "slurm_config_content": "cat /etc/slurm/%s.conf",
    "slurm_effective_config_hash": "scontrol show config | sha256sum | cut -d' ' -f1",
    "slurm_config_mount": "findmnt -J /etc/slurm",
    "slurm_reconfigure": "scontrol reconfigure",
    "slurm_hardware": "scontrol show nodes --oneliner",
    "openmpi": _OPENMPI_DISCOVERY_COMMAND + '"$mpirun_path" --version',
    "slurm_mpi_plugins": "srun --mpi=list 2>&1",
    "openmpi_compile": ("srun --nodes=1 --ntasks=1 --nodelist=%s bash -lc %s"),
    "openmpi_job": (
        "srun --nodes=%s --ntasks=%s --ntasks-per-node=1 "
        "--nodelist=%s --mpi=%s --export=%s %s"
    ),
    "ucx": _UCX_DISCOVERY_COMMAND + '"$ucx_info_path" -v',
    "ucx_transports": (
        _UCX_DISCOVERY_COMMAND + '"$ucx_info_path" -v; "$ucx_info_path" -d'
    ),
    "infiniband": "ibstat",
    "infiniband_slots": "dmidecode -t slot",
    "infiniband_netdev_map": "ibdev2netdev",
    "infiniband_pci_map": (
        "for device in /sys/class/infiniband/*; do "
        'test -e "$device" || continue; '
        'printf \'%s|%s\\n\' "$(basename "$device")" '
        '"$(basename "$(readlink -f "$device/device")")"; done'
    ),
    "infiniband_ofed": "ofed_info -s",
    "infiniband_ping": "ping -c 2 -W 3 %s",
    "gpu": (
        "nvidia-smi --query-gpu=index,name,driver_version,memory.total "
        "--format=csv,noheader"
    ),
    "gpu_job": (
        "srun --nodes=1 --ntasks=1 --gres=gpu:1 --nodelist=%s "
        "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader"
    ),
    "gpu_memory_stress": (
        "set -eu; work=$(mktemp -d /tmp/omnia-gpu-check-XXXXXX); "
        "trap 'rm -rf \"$work\"' EXIT; "
        "printf '%%s' '%s' | base64 -d > \"$work/stress.cu\"; "
        'nvcc -O2 -o "$work/stress" "$work/stress.cu"; '
        'srun --nodes=1 --ntasks=1 --gres=gpu:1 "$work/stress"'
    ),
    "slurm_job_state": (
        "state=$(squeue --noheader --jobs=%s --format='%%T|%%N' | head -1); "
        'if test -z "$state"; then '
        "state=$(sacct --noheader --parsable2 --jobs=%s "
        "--format=State,NodeList | head -1); fi; printf '%%s' \"$state\""
    ),
    "slurm_user_target_job": (
        "su - %s -c \"sbatch --parsable --nodelist=%s --wrap='sleep 45'\""
    ),
    "node_reboot": "systemctl reboot",
    "pam_adopt_integration": (
        "policy=missing; usepam=disabled; module=missing; "
        "if grep -Eq '^[[:space:]]*account[[:space:]]+required"
        "[[:space:]]+pam_slurm_adopt\\.so' /etc/pam.d/sshd; "
        "then policy=configured; fi; "
        "if sshd -T | grep -Eq '^usepam yes$'; then usepam=enabled; fi; "
        "if test -e /usr/lib64/security/pam_slurm_adopt.so; "
        "then module=available; fi; "
        'printf \'%s|%s|%s\' "$policy" "$usepam" "$module"'
    ),
}

KUBERNETES_REQUIRED_POD_PREFIXES: tuple[str, ...] = (
    "etcd-",
    "kube-apiserver-",
    "kube-controller-manager-",
    "kube-scheduler-",
    "kube-proxy-",
    "kube-vip-",
    "coredns-",
)

KUBERNETES_CNI_POD_PREFIXES: dict[str, tuple[str, ...]] = {
    "calico": ("calico-kube-controllers-", "calico-node-"),
    "flannel": ("kube-flannel-",),
}

KUBERNETES_CSI_POD_PREFIXES: tuple[str, ...] = (
    "isilon-controller-",
    "isilon-node-",
    "snapshot-controller-",
)
KUBERNETES_CSI_SNAPSHOT_POD_PREFIXES: tuple[str, ...] = (
    "snapshot-controller-",
    "isilon-controller-",
    "isilon-node-",
)

SLURM_ROLE_SERVICES: dict[str, tuple[str, ...]] = {
    SLURM_CONTROL_PREFIX: ("slurmctld", "slurmdbd", "mariadb", "munge"),
    SLURM_COMPUTE_PREFIX: ("slurmd", "munge"),
    SLURM_LOGIN_PREFIX: ("slurmd", "munge"),
    SLURM_COMPILER_PREFIX: ("slurmd", "munge"),
}
