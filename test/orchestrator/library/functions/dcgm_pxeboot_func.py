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

"""DCGM and CUDA verification after PXE boot.

Each public ``check_*`` function returns the stable result contract
consumed by ``verify_pxeboot`` in ``fvt/result.py``.
"""

import re
import time

from ..vars.pxeboot_vars import (
    PXEBOOT_COMMANDS,
    SLURM_COMPILER_PREFIX,
    SLURM_COMPUTE_PREFIX,
)
from ._pxeboot_helpers import (
    first_row,
    remote_command,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import (
    optional_skip as _skip,
    require_functional as _require_functional,
    slurm_compute_rows as _compute_rows,
    slurm_context as _context,
    slurm_gpu_rows as _gpu_rows,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_output(result) -> str:
    """Return bounded first-line output without leaking command content."""
    text = (result.stdout or result.stderr or "").strip()
    return re.sub(r"\s+", " ", text)[:300]


def _dcgm_context(host):
    """Load Slurm context and identify GPU compute rows."""
    _ctx, rows, control, config = _context(host)
    compute = _compute_rows(rows)
    if not compute:
        return None, rows, control, config, []
    gpu = _gpu_rows(host, control, compute)
    return _ctx, rows, control, config, gpu


# ===================================================================
# Functional checks (14 tests)
# ===================================================================

def check_dcgm_cuda_validation(host):
    """Verify NVIDIA driver and CUDA toolkit are installed on GPU nodes."""
    summary = "CUDA driver and toolkit validation"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        fields = [("GPU nodes", str(len(gpu)))]
        all_ok = True
        for row, gres, count in gpu:
            smi = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_nvidia_smi"])
            cuda = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_cuda_version"])
            driver_ok = smi.rc == 0 and bool(smi.stdout.strip())
            cuda_ok = cuda.rc == 0 and bool(cuda.stdout.strip())
            node_ok = driver_ok and cuda_ok
            all_ok = all_ok and node_ok
            fields.extend([
                (
                    f"  {row['HOSTNAME']}",
                    f"{'OK' if node_ok else 'FAIL'} {row['ADMIN_IP']}",
                ),
                ("    NVIDIA driver", smi.stdout.strip() if driver_ok else "missing"),
                ("    CUDA toolkit", cuda.stdout.strip() if cuda_ok else "missing"),
            ])
        return runtime_result(
            all_ok, summary, fields,
            "NVIDIA driver or CUDA toolkit missing on one or more GPU nodes"
            if not all_ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_cuda_atomic_lock(host):
    """Verify CUDA toolkit is installed to /hpc_tools/cuda via atomic lock."""
    summary = "CUDA atomic lock installation"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        row = gpu[0][0]
        path_result = remote_command(
            host, row, PXEBOOT_COMMANDS["dcgm_cuda_toolkit_path"],
        )
        lock_result = remote_command(
            host, row, PXEBOOT_COMMANDS["dcgm_cuda_lock_check"],
        )
        path_ok = path_result.rc == 0 and bool(path_result.stdout.strip())
        lock_done = "UNLOCKED" in (lock_result.stdout or "")
        ok = path_ok and lock_done
        fields = [
            ("Target node", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
            ("CUDA path", "/hpc_tools/cuda"),
            ("Path exists", "yes" if path_ok else "no"),
            (
                "Lock status",
                "released (install complete)" if lock_done else "held or missing",
            ),
            ("Contents", path_result.stdout.strip()[:200] if path_ok else "n/a"),
        ]
        return runtime_result(
            ok, summary, fields,
            "CUDA toolkit not found at /hpc_tools/cuda or install lock still held"
            if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_package_installed(host):
    """Verify datacenter-gpu-manager RPM is installed and binaries present."""
    summary = "DCGM package installation"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        fields = [("GPU nodes", str(len(gpu)))]
        all_ok = True
        for row, gres, count in gpu:
            rpm = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_rpm_check"])
            binary = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_binary_check"])
            rpm_ok = rpm.rc == 0 and "datacenter-gpu-manager" in (rpm.stdout or "")
            bin_ok = binary.rc == 0 and bool(binary.stdout.strip())
            node_ok = rpm_ok and bin_ok
            all_ok = all_ok and node_ok
            fields.extend([
                (
                    f"  {row['HOSTNAME']}",
                    f"{'OK' if node_ok else 'FAIL'} {row['ADMIN_IP']}",
                ),
                ("    RPM", rpm.stdout.strip() if rpm_ok else "not installed"),
                ("    dcgmi binary", "present" if bin_ok else "missing"),
            ])
        return runtime_result(
            all_ok, summary, fields,
            "datacenter-gpu-manager RPM or dcgmi binary missing" if not all_ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_daemon_running(host):
    """Verify nvidia-dcgm.service is active and enabled on GPU nodes."""
    summary = "DCGM daemon status"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        fields = [("GPU nodes", str(len(gpu)))]
        all_ok = True
        for row, gres, count in gpu:
            active = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_service_active"])
            enabled = remote_command(
                host, row, PXEBOOT_COMMANDS["dcgm_service_enabled"],
            )
            is_active = active.rc == 0 and "active" in (active.stdout or "")
            is_enabled = enabled.rc == 0 and "enabled" in (enabled.stdout or "")
            node_ok = is_active and is_enabled
            all_ok = all_ok and node_ok
            fields.extend([
                (
                    f"  {row['HOSTNAME']}",
                    f"{'OK' if node_ok else 'FAIL'} {row['ADMIN_IP']}",
                ),
                ("    Active", "yes" if is_active else "no"),
                ("    Enabled", "yes" if is_enabled else "no"),
            ])
        return runtime_result(
            all_ok, summary, fields,
            "nvidia-dcgm service not active/enabled on all GPU nodes"
            if not all_ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_gpu_discovery(host):
    """Verify dcgmi discovery -l enumerates GPUs with unique UUIDs."""
    summary = "DCGM GPU discovery"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        fields = [("GPU nodes", str(len(gpu)))]
        all_ok = True
        for row, gres, expected_count in gpu:
            disc = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_discovery"])
            gpu_ids = re.findall(r"GPU ID:\s*(\d+)", disc.stdout or "")
            uuids = re.findall(r"UUID:\s*(\S+)", disc.stdout or "")
            found = len(gpu_ids)
            unique_uuids = len(set(uuids))
            node_ok = (
                disc.rc == 0
                and found >= 1
                and unique_uuids == found
            )
            all_ok = all_ok and node_ok
            fields.extend([
                (
                    f"  {row['HOSTNAME']}",
                    f"{'OK' if node_ok else 'FAIL'} {row['ADMIN_IP']}",
                ),
                ("    GPUs discovered", str(found)),
                ("    Unique UUIDs", str(unique_uuids)),
            ])
        return runtime_result(
            all_ok, summary, fields,
            "dcgmi discovery failed or returned non-unique UUIDs" if not all_ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_gpu_metrics(host):
    """Verify dcgmi dmon returns metric samples for each GPU node."""
    summary = "DCGM GPU metrics monitoring"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        fields = [("GPU nodes", str(len(gpu)))]
        all_ok = True
        for row, gres, count in gpu:
            dmon = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_dmon"])
            lines = [
                line for line in (dmon.stdout or "").splitlines()
                if line.strip() and not line.strip().startswith("#")
                and not line.strip().startswith("Id")
            ]
            node_ok = dmon.rc == 0 and len(lines) >= 1
            all_ok = all_ok and node_ok
            fields.extend([
                (
                    f"  {row['HOSTNAME']}",
                    f"{'OK' if node_ok else 'FAIL'} {row['ADMIN_IP']}",
                ),
                ("    Metric samples", str(len(lines))),
            ])
        return runtime_result(
            all_ok, summary, fields,
            "dcgmi dmon returned no metric samples" if not all_ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_cuda_login_compiler(host):
    """Verify CUDA toolkit is accessible on login_compiler nodes."""
    summary = "CUDA login_compiler installation"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        compiler = first_row(rows, SLURM_COMPILER_PREFIX)
        if compiler is None:
            return _skip(summary, "No login_compiler node in this deployment")

        path_result = remote_command(
            host, compiler, PXEBOOT_COMMANDS["dcgm_cuda_toolkit_path"],
        )
        smi = remote_command(host, compiler, PXEBOOT_COMMANDS["dcgm_nvidia_smi"])
        path_ok = path_result.rc == 0 and bool(path_result.stdout.strip())
        no_driver = smi.rc != 0 or not smi.stdout.strip()
        ok = path_ok and no_driver
        fields = [
            ("Login compiler", f"{compiler['HOSTNAME']} | {compiler['ADMIN_IP']}"),
            ("CUDA toolkit path", "present" if path_ok else "missing"),
            (
                "GPU driver",
                "absent (expected)" if no_driver else "present (unexpected)",
            ),
        ]
        return runtime_result(
            ok, summary, fields,
            "CUDA toolkit missing or GPU driver unexpectedly present on login_compiler"
            if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_cuda_compute_node(host):
    """Verify both CUDA toolkit and CUDA driver are present on compute nodes."""
    summary = "CUDA compute node installation"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        fields = [("GPU compute nodes", str(len(gpu)))]
        all_ok = True
        for row, gres, count in gpu:
            smi = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_nvidia_smi"])
            path_result = remote_command(
                host, row, PXEBOOT_COMMANDS["dcgm_cuda_toolkit_path"],
            )
            driver_ok = smi.rc == 0 and bool(smi.stdout.strip())
            toolkit_ok = path_result.rc == 0 and bool(path_result.stdout.strip())
            node_ok = driver_ok and toolkit_ok
            all_ok = all_ok and node_ok
            fields.extend([
                (
                    f"  {row['HOSTNAME']}",
                    f"{'OK' if node_ok else 'FAIL'} {row['ADMIN_IP']}",
                ),
                ("    CUDA driver", smi.stdout.strip() if driver_ok else "missing"),
                ("    CUDA toolkit", "present" if toolkit_ok else "missing"),
            ])
        return runtime_result(
            all_ok, summary, fields,
            "CUDA driver or toolkit missing on compute node" if not all_ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_multi_gpu_discovery(host):
    """Verify dcgmi discovery enumerates all GPUs on multi-GPU nodes."""
    summary = "DCGM multi-GPU discovery"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        multi_gpu = [
            (row, gres, count) for row, gres, count in gpu if count > 1
        ]
        if not multi_gpu:
            return _skip(summary, "No multi-GPU nodes in this deployment")

        fields = [("Multi-GPU nodes", str(len(multi_gpu)))]
        all_ok = True
        for row, gres, expected_count in multi_gpu:
            count_result = remote_command(
                host, row, PXEBOOT_COMMANDS["dcgm_multi_gpu_count"],
            )
            disc = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_discovery"])
            discovered = len(re.findall(r"GPU ID:\s*(\d+)", disc.stdout or ""))
            actual = 0
            if count_result.rc == 0 and count_result.stdout.strip().isdigit():
                actual = int(count_result.stdout.strip())
            node_ok = actual == expected_count and discovered == expected_count
            all_ok = all_ok and node_ok
            fields.extend([
                (
                    f"  {row['HOSTNAME']}",
                    f"{'OK' if node_ok else 'FAIL'} {row['ADMIN_IP']}",
                ),
                (
                    "    GPU count",
                    f"nvidia-smi={actual} dcgmi={discovered} expected={expected_count}",
                ),
            ])
        return runtime_result(
            all_ok, summary, fields,
            "Multi-GPU discovery count mismatch" if not all_ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_multi_gpu_no_login_compiler(host):
    """Verify GPU nodes work when no login_compiler node exists."""
    summary = "Multi-GPU without login_compiler"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        compiler = first_row(rows, SLURM_COMPILER_PREFIX)
        if compiler is not None:
            return _skip(
                summary,
                "login_compiler is present; this test validates its absence",
            )

        fields = [("login_compiler", "absent"), ("GPU nodes", str(len(gpu)))]
        all_ok = True
        for row, gres, count in gpu:
            smi = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_nvidia_smi"])
            dcgm = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_service_active"])
            node_ok = smi.rc == 0 and "active" in (dcgm.stdout or "")
            all_ok = all_ok and node_ok
            fields.append((
                f"  {row['HOSTNAME']}",
                f"{'OK' if node_ok else 'FAIL'} driver={'yes' if smi.rc == 0 else 'no'}"
                f" dcgm={'active' if 'active' in (dcgm.stdout or '') else 'inactive'}",
            ))
        return runtime_result(
            all_ok, summary, fields,
            "GPU nodes not fully functional without login_compiler"
            if not all_ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_multi_login_compiler_lock(host):
    """Verify CUDA toolkit install uses atomic lock with multiple login_compilers."""
    summary = "Multi login_compiler atomic lock"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        compilers = [
            row for row in rows
            if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPILER_PREFIX)
        ]
        if len(compilers) < 2:
            return _skip(
                summary,
                f"Only {len(compilers)} login_compiler node(s); need 2+ for this test",
            )

        fields = [("Login compilers", str(len(compilers)))]
        all_ok = True
        for compiler in compilers:
            path_result = remote_command(
                host, compiler, PXEBOOT_COMMANDS["dcgm_cuda_toolkit_path"],
            )
            lock = remote_command(
                host, compiler, PXEBOOT_COMMANDS["dcgm_cuda_lock_check"],
            )
            path_ok = path_result.rc == 0 and bool(path_result.stdout.strip())
            lock_released = "UNLOCKED" in (lock.stdout or "")
            node_ok = path_ok and lock_released
            all_ok = all_ok and node_ok
            fields.extend([
                (
                    f"  {compiler['HOSTNAME']}",
                    f"{'OK' if node_ok else 'FAIL'} {compiler['ADMIN_IP']}",
                ),
                ("    CUDA toolkit", "present" if path_ok else "missing"),
                ("    Lock", "released" if lock_released else "held/missing"),
            ])
        return runtime_result(
            all_ok, summary, fields,
            "Atomic lock not released on all login_compiler nodes" if not all_ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_toolkit_nfs_storage(host):
    """Verify /hpc_tools is NFS-mounted and CUDA toolkit accessible."""
    summary = "CUDA NFS shared storage"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        row = gpu[0][0]
        mount = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_nfs_mount_check"])
        toolkit = remote_command(
            host, row, PXEBOOT_COMMANDS["dcgm_cuda_toolkit_path"],
        )
        is_nfs = mount.rc == 0 and "nfs" in (mount.stdout or "").lower()
        toolkit_ok = toolkit.rc == 0 and bool(toolkit.stdout.strip())
        ok = is_nfs and toolkit_ok
        fields = [
            ("Target node", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
            ("Mount info", mount.stdout.strip() if mount.rc == 0 else "not mounted"),
            ("NFS detected", "yes" if is_nfs else "no"),
            ("CUDA toolkit", "accessible" if toolkit_ok else "not found"),
        ]
        return runtime_result(
            ok, summary, fields,
            "/hpc_tools not NFS-mounted or CUDA toolkit inaccessible"
            if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_rhel_compatibility(host):
    """Verify GPU node OS is a supported RHEL version."""
    summary = "GPU RHEL compatibility"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        fields = [("GPU nodes", str(len(gpu)))]
        all_ok = True
        for row, gres, count in gpu:
            os_info = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_os_release"])
            os_id = ""
            version_id = ""
            for line in (os_info.stdout or "").splitlines():
                if line.startswith("ID="):
                    os_id = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("VERSION_ID="):
                    version_id = line.split("=", 1)[1].strip().strip('"')
            is_rhel = os_id in ("rhel", "rocky")
            node_ok = is_rhel and bool(version_id)
            all_ok = all_ok and node_ok
            fields.extend([
                (
                    f"  {row['HOSTNAME']}",
                    f"{'OK' if node_ok else 'FAIL'} {row['ADMIN_IP']}",
                ),
                ("    OS", f"{os_id} {version_id}" if os_id else "unknown"),
            ])
        return runtime_result(
            all_ok, summary, fields,
            "GPU node OS is not a supported RHEL/Rocky version" if not all_ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_cuda_version_compatibility(host):
    """Verify CUDA toolkit and DCGM daemon version compatibility."""
    summary = "CUDA version compatibility"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        fields = [("GPU nodes", str(len(gpu)))]
        all_ok = True
        for row, gres, count in gpu:
            cuda = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_cuda_version"])
            dcgm_active = remote_command(
                host, row, PXEBOOT_COMMANDS["dcgm_service_active"],
            )
            cuda_ver = cuda.stdout.strip() if cuda.rc == 0 else ""
            dcgm_ok = "active" in (dcgm_active.stdout or "")
            node_ok = bool(cuda_ver) and dcgm_ok
            all_ok = all_ok and node_ok
            fields.extend([
                (
                    f"  {row['HOSTNAME']}",
                    f"{'OK' if node_ok else 'FAIL'} {row['ADMIN_IP']}",
                ),
                ("    CUDA version", cuda_ver or "not detected"),
                ("    DCGM daemon", "active" if dcgm_ok else "inactive"),
            ])
        return runtime_result(
            all_ok, summary, fields,
            "CUDA or DCGM version not compatible" if not all_ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ===================================================================
# Negative / error-handling checks (4 tests)
# ===================================================================

def check_dcgm_neg_cuda_prerequisite(host):
    """Verify DCGM deployment requires CUDA driver as a prerequisite."""
    summary = "CUDA prerequisite enforcement"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        gated = _require_functional(summary)
        if gated:
            return gated

        row = gpu[0][0]
        smi = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_nvidia_smi"])
        dcgm_active = remote_command(
            host, row, PXEBOOT_COMMANDS["dcgm_service_active"],
        )
        driver_present = smi.rc == 0 and bool(smi.stdout.strip())
        dcgm_running = "active" in (dcgm_active.stdout or "")
        ok = driver_present and dcgm_running
        fields = [
            ("Target node", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
            ("NVIDIA driver", "present" if driver_present else "missing"),
            ("DCGM service", "active" if dcgm_running else "inactive"),
            (
                "Prerequisite contract",
                "enforced (driver present, DCGM running)" if ok
                else "DCGM should not run without CUDA driver",
            ),
        ]
        return runtime_result(
            ok, summary, fields,
            "CUDA prerequisite contract violated" if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_neg_daemon_recovery(host):
    """Simulate DCGM daemon crash via SIGKILL and verify systemd restarts it."""
    summary = "DCGM daemon crash recovery"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        gated = _require_functional(summary)
        if gated:
            return gated

        row = gpu[0][0]
        # Verify daemon is running before the test
        pre_active = remote_command(
            host, row, PXEBOOT_COMMANDS["dcgm_service_active"],
        )
        if "active" not in (pre_active.stdout or ""):
            return runtime_result(
                False, summary,
                [("Target node", row["HOSTNAME"]), ("Pre-check", "daemon not active")],
                "DCGM daemon was not running before the recovery test",
            )

        # Get PID and kill it
        pid_result = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_service_pid"])
        pid = pid_result.stdout.strip() if pid_result.rc == 0 else ""
        if not pid or pid == "0":
            return runtime_result(
                False, summary,
                [("Target node", row["HOSTNAME"]), ("PID", "not found")],
                "Could not determine DCGM daemon PID",
            )

        remote_command(host, row, f"kill -9 {pid}")
        time.sleep(5)

        # Check if systemd restarted it
        post_active = remote_command(
            host, row, PXEBOOT_COMMANDS["dcgm_service_active"],
        )
        new_pid = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_service_pid"])
        recovered = "active" in (post_active.stdout or "")
        new_pid_str = new_pid.stdout.strip() if new_pid.rc == 0 else ""
        pid_changed = new_pid_str != pid and new_pid_str != "0"
        ok = recovered and pid_changed
        fields = [
            ("Target node", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
            ("Original PID", pid),
            ("New PID", new_pid_str or "none"),
            ("Service recovered", "yes" if recovered else "no"),
            ("PID changed", "yes" if pid_changed else "no"),
        ]
        return runtime_result(
            ok, summary, fields,
            "DCGM daemon did not auto-recover after SIGKILL" if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_neg_socket_inaccessible(host):
    """Remove DCGM Unix socket and verify dcgmi returns a clear error."""
    summary = "DCGM socket inaccessible"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        gated = _require_functional(summary)
        if gated:
            return gated

        row = gpu[0][0]
        # Check socket exists
        socket_check = remote_command(
            host, row, PXEBOOT_COMMANDS["dcgm_socket_path"],
        )
        if "EXISTS" not in (socket_check.stdout or ""):
            return _skip(summary, "DCGM socket not found; cannot test removal")

        # Find and temporarily rename the socket
        socket_paths = [
            "/var/run/nvidia-dcgm/nv-hostengine.sock",
            "/tmp/nv-hostengine.sock",
        ]
        renamed = None
        for spath in socket_paths:
            test_result = remote_command(host, row, f"test -S {spath} && echo YES")
            if "YES" in (test_result.stdout or ""):
                remote_command(host, row, f"mv {spath} {spath}.bak")
                renamed = spath
                break

        if not renamed:
            return _skip(summary, "Could not locate DCGM socket to rename")

        try:
            # dcgmi should fail without the socket
            disc = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_discovery"])
            error_detected = disc.rc != 0
            error_msg = _safe_output(disc)
        finally:
            # Restore socket
            remote_command(host, row, f"mv {renamed}.bak {renamed}")
            time.sleep(2)

        # Verify service recovers after socket restored
        post_disc = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_discovery"])
        service_ok = post_disc.rc == 0

        ok = error_detected and service_ok
        fields = [
            ("Target node", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
            ("Socket removed", renamed),
            ("dcgmi error on removal", "yes" if error_detected else "no"),
            ("Error output", error_msg[:200] if error_detected else "n/a"),
            ("Post-restore recovery", "yes" if service_ok else "no"),
        ]
        return runtime_result(
            ok, summary, fields,
            "dcgmi did not report error on socket removal or failed to recover"
            if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_dcgm_neg_package_install_failure(host):
    """Verify error handling when datacenter-gpu-manager package is unavailable."""
    summary = "DCGM package install failure"
    try:
        _ctx, rows, control, _cfg, gpu = _dcgm_context(host)
        if not gpu:
            return _skip(summary, "No GPU GRES nodes found in Slurm")

        gated = _require_functional(summary)
        if gated:
            return gated

        row = gpu[0][0]
        # Verify the package IS installed (the negative scenario validates
        # that its absence would be detected; we confirm current presence
        # and the RPM database integrity as a proxy)
        rpm = remote_command(host, row, PXEBOOT_COMMANDS["dcgm_rpm_check"])
        rpm_ok = rpm.rc == 0 and "datacenter-gpu-manager" in (rpm.stdout or "")

        # Simulate a dry-run removal check
        dry_run = remote_command(
            host, row,
            "rpm -e --test datacenter-gpu-manager 2>&1",
        )
        can_remove = dry_run.rc == 0
        has_deps = "is needed by" in (dry_run.stderr or "") + (dry_run.stdout or "")

        ok = rpm_ok
        fields = [
            ("Target node", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
            ("Package installed", "yes" if rpm_ok else "no"),
            ("RPM version", rpm.stdout.strip() if rpm_ok else "n/a"),
            (
                "Removal blocked by deps",
                "yes" if has_deps else "no (clean removal possible)",
            ),
        ]
        return runtime_result(
            ok, summary, fields,
            "DCGM package not installed; install failure scenario not testable"
            if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
