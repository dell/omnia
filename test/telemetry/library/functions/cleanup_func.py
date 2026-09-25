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
Telemetry — Cleanup Verification Functions.

Functions for verifying that telemetry cleanup has properly removed
K8s resources (pods, PVCs, services, deployments, statefulsets)
from the telemetry namespace.
"""

from typing import Dict, Any, List

from omnia_auto import read_remote_env

from .telemetry_func import run_on_kube_vip

from library.vars.common_vars import (
    CMDS,
    TELEMETRY_NAMESPACE,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    IDRAC_POD_PREFIX,
    IDRAC_STS_NAME,
    LDMS_AGG_STS_NAME,
    LDMS_STORE_NAME,
    VECTOR_LDMS_APP_NAME,
    VECTOR_OME_APP_NAME,
    VM_POD_PREFIXES,
    VMAGENT_POD_PREFIX,
    VL_POD_PREFIXES,
    VLAGENT_POD_PREFIX,
    KAFKA_POD_PREFIXES,
    KAFKA_BRIDGE_PREFIX,
)


# =============================================================================
# HELPER — get pod count by prefix
# =============================================================================

def _get_pod_count_by_prefix(host, prefix, namespace=None):
    """Return count of pods matching a prefix in the namespace.

    Args:
        host: testinfra host connected to kube_vip.
        prefix: pod name prefix to search for.
        namespace: K8s namespace (default: telemetry).

    Returns:
        int: number of matching pods.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_pod_count"].format(namespace=ns, prefix=prefix)
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0


def _get_resource_count(host, resource_type, namespace=None):
    """Return count of a K8s resource type in the namespace.

    Args:
        host: testinfra host connected to kube_vip.
        resource_type: K8s resource type (pods, pvc, svc, etc.).
        namespace: K8s namespace (default: telemetry).

    Returns:
        int: number of resources found.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_count_resources"].format(
        resource=resource_type, namespace=ns,
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0


# =============================================================================
# SOURCE CLEANUP VERIFICATION
# =============================================================================

def verify_idrac_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify iDRAC telemetry resources have been removed.

    Checks that no iDRAC pods (statefulset or standalone) remain.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    pod_count = _get_pod_count_by_prefix(host, IDRAC_POD_PREFIX, ns)
    if pod_count == 0:
        return {
            "success": True,
            "details": f"No iDRAC pods found in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Found {pod_count} iDRAC pod(s) still running",
        "error": f"{pod_count} iDRAC pod(s) remain in namespace '{ns}'",
    }


def verify_ldms_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify LDMS resources (aggregator + store + Vector-LDMS) removed.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    remaining = []
    for prefix, label in [
        (LDMS_AGG_STS_NAME, "LDMS aggregator"),
        (LDMS_STORE_NAME, "LDMS store"),
        (VECTOR_LDMS_APP_NAME, "Vector-LDMS bridge"),
    ]:
        count = _get_pod_count_by_prefix(host, prefix, ns)
        if count > 0:
            remaining.append(f"{label} ({count} pods)")

    if not remaining:
        return {
            "success": True,
            "details": f"No LDMS/Vector-LDMS pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Remaining: {', '.join(remaining)}",
        "error": f"LDMS resources still present: {', '.join(remaining)}",
    }


def verify_ome_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify OME resources (Vector-OME bridge) removed.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    count = _get_pod_count_by_prefix(host, VECTOR_OME_APP_NAME, ns)
    if count == 0:
        return {
            "success": True,
            "details": f"No Vector-OME pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Found {count} Vector-OME pod(s) still running",
        "error": f"{count} Vector-OME pod(s) remain in namespace '{ns}'",
    }


def verify_ufm_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify UFM telemetry resources removed.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    count = _get_pod_count_by_prefix(host, "ufm-external", ns)
    if count == 0:
        return {
            "success": True,
            "details": f"No UFM pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Found {count} UFM pod(s) still running",
        "error": f"{count} UFM pod(s) remain in namespace '{ns}'",
    }


def verify_vast_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify VAST telemetry resources removed.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    count = _get_pod_count_by_prefix(host, "vast-external", ns)
    if count == 0:
        return {
            "success": True,
            "details": f"No VAST pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Found {count} VAST pod(s) still running",
        "error": f"{count} VAST pod(s) remain in namespace '{ns}'",
    }


def verify_sfm_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify SFM telemetry resources removed.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    count = _get_pod_count_by_prefix(host, "sfm-telemetry", ns)
    if count == 0:
        return {
            "success": True,
            "details": f"No SFM pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Found {count} SFM pod(s) still running",
        "error": f"{count} SFM pod(s) remain in namespace '{ns}'",
    }


# =============================================================================
# SINK CLEANUP VERIFICATION
# =============================================================================

def verify_kafka_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify Kafka resources (cluster + bridge + operator) removed.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    remaining = []
    for prefix, label in [
        (KAFKA_POD_PREFIXES["broker"], "Kafka brokers"),
        (KAFKA_POD_PREFIXES["controller"], "Kafka controllers"),
        (KAFKA_BRIDGE_PREFIX, "Kafka bridge"),
        ("strimzi", "Strimzi operator"),
    ]:
        count = _get_pod_count_by_prefix(host, prefix, ns)
        if count > 0:
            remaining.append(f"{label} ({count} pods)")

    if not remaining:
        return {
            "success": True,
            "details": f"No Kafka pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Remaining: {', '.join(remaining)}",
        "error": f"Kafka resources still present: {', '.join(remaining)}",
    }


def verify_victoria_metrics_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify VictoriaMetrics resources removed.

    Checks vmstorage, vminsert, vmselect, vmagent, and operator pods.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    remaining = []
    for prefix, label in [
        (VM_POD_PREFIXES["vmstorage"], "vmstorage"),
        (VM_POD_PREFIXES["vminsert"], "vminsert"),
        (VM_POD_PREFIXES["vmselect"], "vmselect"),
        (VMAGENT_POD_PREFIX, "vmagent"),
        ("victoria-metrics-operator", "VM operator"),
    ]:
        count = _get_pod_count_by_prefix(host, prefix, ns)
        if count > 0:
            remaining.append(f"{label} ({count} pods)")

    if not remaining:
        return {
            "success": True,
            "details": f"No VictoriaMetrics pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Remaining: {', '.join(remaining)}",
        "error": (
            f"VictoriaMetrics resources still present: "
            f"{', '.join(remaining)}"
        ),
    }


def verify_victoria_logs_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify VictoriaLogs resources removed.

    Checks vlstorage, vlinsert, vlselect, and vlagent pods.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    remaining = []
    for prefix, label in [
        (VL_POD_PREFIXES["vlstorage"], "vlstorage"),
        (VL_POD_PREFIXES["vlinsert"], "vlinsert"),
        (VL_POD_PREFIXES["vlselect"], "vlselect"),
        (VLAGENT_POD_PREFIX, "vlagent"),
    ]:
        count = _get_pod_count_by_prefix(host, prefix, ns)
        if count > 0:
            remaining.append(f"{label} ({count} pods)")

    if not remaining:
        return {
            "success": True,
            "details": f"No VictoriaLogs pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Remaining: {', '.join(remaining)}",
        "error": (
            f"VictoriaLogs resources still present: "
            f"{', '.join(remaining)}"
        ),
    }


# =============================================================================
# FINAL STATE VERIFICATION
# =============================================================================

def verify_no_pods_remaining(host, namespace=None) -> Dict[str, Any]:
    """Verify no pods remain in the telemetry namespace.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str),
                        count (int).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    count = _get_resource_count(host, "pods", ns)
    if count == 0:
        return {
            "success": True,
            "details": f"No pods in namespace '{ns}'",
            "error": "",
            "count": 0,
        }
    return {
        "success": False,
        "details": f"{count} pod(s) still present in namespace '{ns}'",
        "error": f"{count} pod(s) remain after full cleanup",
        "count": count,
    }


def verify_no_pvcs_remaining(host, namespace=None) -> Dict[str, Any]:
    """Verify no PVCs remain in the telemetry namespace.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str),
                        count (int).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    count = _get_resource_count(host, "pvc", ns)
    if count == 0:
        return {
            "success": True,
            "details": f"No PVCs in namespace '{ns}'",
            "error": "",
            "count": 0,
        }
    return {
        "success": False,
        "details": f"{count} PVC(s) still present in namespace '{ns}'",
        "error": f"{count} PVC(s) remain after full cleanup",
        "count": count,
    }


def verify_source_pvcs_deleted(host, namespace=None) -> Dict[str, Any]:
    """Verify source PVCs are deleted after cleanup (always expected).

    Source PVCs (currently iDRAC and PowerScale) should always be
    deleted regardless of the delete_volume flag. This function
    verifies that no source PVCs remain.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str),
                        count (int).
    """
    ns = namespace or TELEMETRY_NAMESPACE

    # Check for source PVCs (should always be deleted)
    source_pvc_count = 0
    source_pvc_details = []
    for prefix in ["mysqldb", "powerscale"]:
        cmd = CMDS["kubectl_get_pvc_count"].format(namespace=ns, prefix=prefix)
        result = run_on_kube_vip(host, cmd)
        if result.rc == 0:
            count = int(result.stdout.strip())
            if count > 0:
                source_pvc_count += count
                source_pvc_details.append(f"{prefix} ({count})")

    if source_pvc_count == 0:
        return {
            "success": True,
            "details": (
                f"No source PVCs found in namespace '{ns}' "
                f"(all source PVCs deleted as expected)"
            ),
            "error": "",
            "count": 0,
        }
    return {
        "success": False,
        "details": (
            f"{source_pvc_count} source PVC(s) still present in namespace '{ns}': "
            f"{', '.join(source_pvc_details)}"
        ),
        "error": (
            f"Source PVCs were not deleted; found {source_pvc_count} source PVC(s) "
            f"that should have been deleted: {', '.join(source_pvc_details)}"
        ),
        "count": source_pvc_count,
    }


def verify_sink_pvcs_deleted(host, namespace=None) -> Dict[str, Any]:
    """Verify Kafka and Victoria PVCs are deleted after cleanup (delete_volume=true).

    When delete_volume=true, Kafka and VictoriaMetrics/VictoriaLogs PVCs should be deleted.
    This function verifies that no sink PVCs remain.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str),
                        count (int).
    """
    ns = namespace or TELEMETRY_NAMESPACE

    # Check for sink PVCs (should be deleted when delete_volume=true)
    sink_pvc_count = 0
    sink_pvc_details = []
    for prefix in ["kafka", "vmstorage", "vminsert", "vmselect", "vlstorage", "vlinsert", "vlselect"]:
        cmd = CMDS["kubectl_get_pvc_count"].format(namespace=ns, prefix=prefix)
        result = run_on_kube_vip(host, cmd)
        if result.rc == 0:
            count = int(result.stdout.strip())
            if count > 0:
                sink_pvc_count += count
                sink_pvc_details.append(f"{prefix} ({count})")

    if sink_pvc_count == 0:
        return {
            "success": True,
            "details": (
                f"No sink PVCs found in namespace '{ns}' "
                f"(all sink PVCs deleted as expected)"
            ),
            "error": "",
            "count": 0,
        }
    return {
        "success": False,
        "details": (
            f"{sink_pvc_count} sink PVC(s) still present in namespace '{ns}': "
            f"{', '.join(sink_pvc_details)}"
        ),
        "error": (
            f"Sink PVCs were not deleted; found {sink_pvc_count} sink PVC(s) "
            f"that should have been deleted: {', '.join(sink_pvc_details)}"
        ),
        "count": sink_pvc_count,
    }


def verify_pvcs_preserved(host, namespace=None) -> Dict[str, Any]:
    """Verify Kafka and VictoriaMetrics/VictoriaLogs PVCs are preserved after cleanup (delete_volume=false).

    When cleanup runs without ``delete_volume=true``, Kafka and VictoriaMetrics/VictoriaLogs
    persistent volume claims must be retained so that data survives a redeploy.
    Other source volumes (currently iDRAC and PowerScale) are always deleted.

    This function succeeds when:
      - Kafka and VictoriaMetrics/VictoriaLogs PVCs exist (preserved)
      - Other source PVCs do NOT exist (deleted)

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str),
                        count (int).
    """
    ns = namespace or TELEMETRY_NAMESPACE

    # Check for Kafka and VictoriaMetrics/VictoriaLogs PVCs (should be preserved)
    sink_pvc_count = 0
    for prefix in ["kafka", "vmstorage", "vminsert", "vmselect", "vlstorage", "vlinsert", "vlselect"]:
        cmd = CMDS["kubectl_get_pvc_count"].format(namespace=ns, prefix=prefix)
        result = run_on_kube_vip(host, cmd)
        if result.rc == 0:
            sink_pvc_count += int(result.stdout.strip())

    # Check for source PVCs (should be deleted)
    source_pvc_count = 0
    for prefix in ["mysqldb", "powerscale"]:
        cmd = CMDS["kubectl_get_pvc_count"].format(namespace=ns, prefix=prefix)
        result = run_on_kube_vip(host, cmd)
        if result.rc == 0:
            source_pvc_count += int(result.stdout.strip())

    if sink_pvc_count > 0 and source_pvc_count == 0:
        return {
            "success": True,
            "details": (
                f"{sink_pvc_count} Kafka/VictoriaMetrics/VictoriaLogs PVC(s) preserved, "
                f"{source_pvc_count} source PVC(s) deleted in namespace '{ns}' "
                f"(delete_volume=false)"
            ),
            "error": "",
            "count": sink_pvc_count,
        }
    elif sink_pvc_count == 0:
        return {
            "success": False,
            "details": (
                f"No Kafka/VictoriaMetrics/VictoriaLogs PVCs found in namespace '{ns}' — "
                f"expected them to be preserved (delete_volume=false)"
            ),
            "error": (
                "Kafka/VictoriaMetrics/VictoriaLogs PVCs were deleted despite delete_volume=false; "
                "these volumes should have been preserved"
            ),
            "count": 0,
        }
    else:
        return {
            "success": False,
            "details": (
                f"{source_pvc_count} source PVC(s) still present in namespace '{ns}' — "
                f"expected them to be deleted (delete_volume=false)"
            ),
            "error": (
                f"Source PVCs were not deleted despite delete_volume=false; "
                f"found {source_pvc_count} source PVC(s) that should have been deleted"
            ),
            "count": sink_pvc_count,
        }


# =============================================================================
# CREDENTIAL AND LOG PRESERVATION VERIFICATION
# =============================================================================

def verify_credentials_preserved(host) -> Dict[str, Any]:
    """Verify credential files are preserved after cleanup with cleanup_credentials=false.

    Checks for:
      - telemetry_credentials.yml
      - .telemetry_credentials_key

    Args:
        host: testinfra host fixture.

    Returns:
        dict: {
            "success": bool,
            "details": str,
            "error": str or None,
            "files": {
                "credentials": bool,
                "vault_key": bool
            }
        }
    """
    # Read environment variables from the host (sources /etc/omnia/omnia.env)
    omnia_data_path = (
        read_remote_env(host, ENV_OMNIA_DATA_PATH, required=False) or "/opt/omnia"
    )
    omnia_project_name = (
        read_remote_env(host, ENV_OMNIA_PROJECT_NAME, required=False) or "project_default"
    )

    input_dir = f"{omnia_data_path}/telemetry/input/{omnia_project_name}"
    cred_file = f"{input_dir}/telemetry_credentials.yml"
    vault_key_file = f"{input_dir}/.telemetry_credentials_key"

    result = {
        "success": False,
        "details": "",
        "error": None,
        "files": {
            "credentials": False,
            "vault_key": False,
        },
    }

    try:
        # Check credentials file
        cred_exists = host.file(cred_file).exists
        result["files"]["credentials"] = cred_exists

        # Check vault key file
        key_exists = host.file(vault_key_file).exists
        result["files"]["vault_key"] = key_exists

        if cred_exists and key_exists:
            result["success"] = True
            result["details"] = (
                f"Credential files preserved:\n"
                f"  - {cred_file}: exists\n"
                f"  - {vault_key_file}: exists"
            )
        else:
            missing = []
            if not cred_exists:
                missing.append(cred_file)
            if not key_exists:
                missing.append(vault_key_file)
            result["error"] = f"Credential files not preserved: {', '.join(missing)}"
            result["details"] = (
                f"Expected credential files to be preserved (cleanup_credentials=false):\n"
                f"  - {cred_file}: {'exists' if cred_exists else 'MISSING'}\n"
                f"  - {vault_key_file}: {'exists' if key_exists else 'MISSING'}"
            )

    except Exception as e:
        result["error"] = str(e)
        result["details"] = f"Error checking credential files: {str(e)}"

    return result


def verify_credentials_deleted(host) -> Dict[str, Any]:
    """Verify credential files are deleted after cleanup with cleanup_credentials=true (default).

    Checks that both credential files are removed:
      - telemetry_credentials.yml
      - .telemetry_credentials_key

    Args:
        host: testinfra host fixture.

    Returns:
        dict: {
            "success": bool,
            "details": str,
            "error": str or None,
            "files": {
                "credentials": bool,
                "vault_key": bool
            }
        }
    """
    # Read environment variables from the host (sources /etc/omnia/omnia.env)
    omnia_data_path = (
        read_remote_env(host, ENV_OMNIA_DATA_PATH, required=False) or "/opt/omnia"
    )
    omnia_project_name = (
        read_remote_env(host, ENV_OMNIA_PROJECT_NAME, required=False) or "project_default"
    )

    input_dir = f"{omnia_data_path}/telemetry/input/{omnia_project_name}"
    cred_file = f"{input_dir}/telemetry_credentials.yml"
    vault_key_file = f"{input_dir}/.telemetry_credentials_key"

    result = {
        "success": False,
        "details": "",
        "error": None,
        "files": {
            "credentials": False,
            "vault_key": False,
        },
    }

    try:
        # Check credentials file
        cred_exists = host.file(cred_file).exists
        result["files"]["credentials"] = cred_exists

        # Check vault key file
        key_exists = host.file(vault_key_file).exists
        result["files"]["vault_key"] = key_exists

        if not cred_exists and not key_exists:
            result["success"] = True
            result["details"] = (
                f"Credential files deleted:\n"
                f"  - {cred_file}: deleted\n"
                f"  - {vault_key_file}: deleted"
            )
        else:
            remaining = []
            if cred_exists:
                remaining.append(cred_file)
            if key_exists:
                remaining.append(vault_key_file)
            result["error"] = f"Credential files not deleted: {', '.join(remaining)}"
            result["details"] = (
                f"Expected credential files to be deleted (cleanup_credentials=true):\n"
                f"  - {cred_file}: {'exists' if cred_exists else 'deleted'}\n"
                f"  - {vault_key_file}: {'exists' if key_exists else 'deleted'}"
            )

    except Exception as e:
        result["error"] = str(e)
        result["details"] = f"Error checking credential files: {str(e)}"

    return result


def verify_logs_preserved(host) -> Dict[str, Any]:
    """Verify log directory is preserved after cleanup with cleanup_logs=false.

    Checks for:
      - <OMNIA_DATA_PATH>/telemetry/log/<OMNIA_PROJECT_NAME>/

    Args:
        host: testinfra host fixture.

    Returns:
        dict: {
            "success": bool,
            "details": str,
            "error": str or None,
            "log_dir_exists": bool
        }
    """
    # Read environment variables from the host (sources /etc/omnia/omnia.env)
    omnia_data_path = (
        read_remote_env(host, ENV_OMNIA_DATA_PATH, required=False) or "/opt/omnia"
    )
    omnia_project_name = (
        read_remote_env(host, ENV_OMNIA_PROJECT_NAME, required=False) or "project_default"
    )

    log_dir = f"{omnia_data_path}/telemetry/log/{omnia_project_name}"

    result = {
        "success": False,
        "details": "",
        "error": None,
        "log_dir_exists": False,
    }

    try:
        log_dir_exists = host.file(log_dir).is_directory
        result["log_dir_exists"] = log_dir_exists

        if log_dir_exists:
            result["success"] = True
            result["details"] = (
                f"Log directory preserved:\n"
                f"  - {log_dir}: exists"
            )
        else:
            result["error"] = f"Log directory not preserved: {log_dir}"
            result["details"] = (
                f"Expected log directory to be preserved (cleanup_logs=false):\n"
                f"  - {log_dir}: MISSING"
            )

    except Exception as e:
        result["error"] = str(e)
        result["details"] = f"Error checking log directory: {str(e)}"

    return result


def verify_logs_deleted(host) -> Dict[str, Any]:
    """Verify log directory is deleted after cleanup with cleanup_logs=true (default).

    Checks that the log directory is removed:
      - <OMNIA_DATA_PATH>/telemetry/log/<OMNIA_PROJECT_NAME>/

    Args:
        host: testinfra host fixture.

    Returns:
        dict: {
            "success": bool,
            "details": str,
            "error": str or None,
            "log_dir_exists": bool
        }
    """
    # Read environment variables from the host (sources /etc/omnia/omnia.env)
    omnia_data_path = (
        read_remote_env(host, ENV_OMNIA_DATA_PATH, required=False) or "/opt/omnia"
    )
    omnia_project_name = (
        read_remote_env(host, ENV_OMNIA_PROJECT_NAME, required=False) or "project_default"
    )

    log_dir = f"{omnia_data_path}/telemetry/log/{omnia_project_name}"

    result = {
        "success": False,
        "details": "",
        "error": None,
        "log_dir_exists": False,
    }

    try:
        log_dir_exists = host.file(log_dir).is_directory
        result["log_dir_exists"] = log_dir_exists

        if not log_dir_exists:
            result["success"] = True
            result["details"] = (
                f"Log directory deleted:\n"
                f"  - {log_dir}: deleted"
            )
        else:
            result["error"] = f"Log directory not deleted: {log_dir}"
            result["details"] = (
                f"Expected log directory to be deleted (cleanup_logs=true):\n"
                f"  - {log_dir}: still exists"
            )

    except Exception as e:
        result["error"] = str(e)
        result["details"] = f"Error checking log directory: {str(e)}"

    return result
