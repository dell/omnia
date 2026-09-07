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
Orchestrator — Kubernetes Test Messages

Message templates for Kubernetes testing.
"""

from typing import Dict

# =============================================================================
# KUBERNETES TEST LOG MESSAGES
# =============================================================================
TEST_LOG_MSGS: Dict[str, str] = {
    # Basic checks
    "k8s_enabled_ok": "Kubernetes is enabled in catalog",
    "k8s_enabled_failed": "Kubernetes is not enabled in catalog",

    # Node status
    "k8s_nodes_ready_ok": "All Kubernetes nodes are in Ready state",
    "k8s_nodes_ready_failed": "{count} node(s) not Ready: {nodes}",
    "k8s_cp_nodes_ok": "All control plane nodes are Ready",
    "k8s_cp_nodes_failed": "{count} control plane node(s) not Ready: {nodes}",
    "k8s_worker_nodes_ok": "All worker nodes are Ready",
    "k8s_worker_nodes_failed": "{count} worker node(s) not Ready: {nodes}",

    # Service checks
    "kubelet_check_ok": "kubelet service is active on all nodes",
    "kubelet_check_failed": "kubelet service failed on nodes: {nodes}",
    "containerd_check_ok": "containerd service is active on all nodes",
    "containerd_check_failed": "containerd service failed on nodes: {nodes}",

    # Pod checks
    "system_pods_ok": "All kube-system pods are Running",
    "system_pods_failed": "{count} kube-system pod(s) not Running: {pods}",
    "apiserver_ok": "Kubernetes API server is responding",
    "apiserver_failed": "Kubernetes API server not responding: {error}",
    "etcd_ok": "etcd cluster is healthy",
    "etcd_failed": "etcd cluster health check failed: {error}",
    "coredns_ok": "CoreDNS pods are Running",
    "coredns_failed": "CoreDNS pods not Running: {error}",
    "kube_proxy_ok": "kube-proxy pods are Running",
    "kube_proxy_failed": "kube-proxy pods not Running: {error}",

    # Static pods
    "static_pod_ok": "{component} static pod is Running",
    "static_pod_failed": "{component} static pod not Running: {error}",

    # Cluster info
    "cluster_info_ok": "kubectl cluster-info returned valid data",
    "cluster_info_failed": "kubectl cluster-info failed: {error}",

    # Directory/file checks
    "k8s_dirs_ok": "All Kubernetes directories exist",
    "k8s_dirs_failed": "Missing Kubernetes directories: {dirs}",
    "k8s_config_files_ok": "All Kubernetes configuration files exist",
    "k8s_config_files_failed": "Missing configuration files: {files}",
    "k8s_pki_ok": "Kubernetes PKI certificates exist",
    "k8s_pki_failed": "Kubernetes PKI certificates missing",
    "k8s_nfs_config_ok": "K8s NFS configuration directory exists",
    "k8s_nfs_config_failed": "K8s NFS configuration directory missing",

    # SSH checks
    "ssh_ok": "Passwordless SSH from {from_type} to {to_type} works",
    "ssh_failed": "Passwordless SSH from {from_type} to {to_type} failed: {pairs}",

    # Workload tests
    "pod_create_ok": "Pod creation and scheduling works",
    "pod_create_failed": "Pod creation or scheduling failed: {error}",
    "dns_resolution_ok": "DNS resolution works inside pods",
    "dns_resolution_failed": "DNS resolution failed inside pods: {error}",
    "service_create_ok": "Kubernetes service creation works",
    "service_create_failed": "Service creation failed: {error}",

    # Node metadata
    "node_labels_ok": "Node labels match functional group roles",
    "node_labels_failed": "Node labels not set correctly: {error}",
    "node_taints_ok": "Control plane node taints verified",
    "node_taints_failed": "Control plane node taints check failed: {error}",

    # SMD/Metadata
    "smd_groups_ok": "K8s functional groups registered in SMD",
    "smd_groups_failed": "K8s functional groups not found in SMD",
    "metadata_ok": "K8s metadata-service configuration exists",
    "metadata_failed": "K8s metadata-service configuration missing",

    # LDAP
    "ldap_ok": "OpenLDAP integration with Kubernetes verified",
    "ldap_failed": "OpenLDAP integration check failed: {error}",

    # CRI-O / Container Runtime
    "crio_check_ok": "CRI-O service is active on all nodes",
    "crio_check_failed": "CRI-O service failed on nodes: {nodes}",
    "chronyd_check_ok": "chronyd service is active on all control plane nodes",
    "chronyd_check_failed": "chronyd service failed on nodes: {nodes}",
    "kubectl_version_ok": "kubectl version matches expected ({version})",
    "kubectl_version_failed": "kubectl version mismatch: {error}",
    "kubeadm_crio_match_ok": "kubeadm version matches CRI-O version on all control planes",
    "kubeadm_crio_match_failed": "kubeadm/CRI-O version mismatch: {error}",
    "container_runtime_ok": "All nodes using expected container runtime: {runtime}",
    "container_runtime_failed": "Container runtime mismatch detected: {error}",
    "component_status_ok": "All K8s components are Healthy",
    "component_status_failed": "Unhealthy components found: {components}",

    # etcd Detailed
    "etcd_health_detailed_ok": "All etcd endpoints are healthy",
    "etcd_health_detailed_failed": "Some etcd endpoints unhealthy: {error}",
    "etcd_member_list_ok": "etcd member list verified ({count} members)",
    "etcd_member_list_failed": "etcd member count mismatch: {error}",
    "etcd_leader_ok": "etcd leader identified with consistent RAFT terms",
    "etcd_leader_failed": "etcd consistency issue: {error}",

    # HA / VIP
    "vip_ok": "VIP configured on exactly one control plane: {node}",
    "vip_failed": "VIP configuration issue: {error}",

    # Network Pods
    "kube_vip_pods_ok": "All kube-vip pods are Running",
    "kube_vip_pods_failed": "kube-vip pods not Running: {error}",
    "calico_pods_ok": "All Calico pods are Running",
    "calico_pods_failed": "Calico pods not Running: {error}",
    "metallb_pods_ok": "All MetalLB pods are Running",
    "metallb_pods_failed": "MetalLB pods not Running: {error}",

    # Storage
    "nfs_provisioner_ok": "NFS provisioner pod is Running",
    "nfs_provisioner_failed": "NFS provisioner pod not Running: {error}",
    "snapshot_controller_ok": "Snapshot controller pods are Running",
    "snapshot_controller_failed": "Snapshot controller pods not Running: {error}",
    "isilon_csi_ok": "Isilon CSI driver pods are Running",
    "isilon_csi_failed": "Isilon CSI driver pods not Running: {error}",
    "default_sc_ok": "Default storage class is set correctly: {sc}",
    "default_sc_failed": "Default storage class mismatch: {error}",
    "persistent_volumes_ok": "All Persistent Volumes are Bound",
    "persistent_volumes_failed": "PV issues found: {error}",
    "nfs_sc_ok": "NFS StorageClass is dynamic and properly configured",
    "nfs_sc_failed": "NFS StorageClass validation failed: {error}",
    "telemetry_pvcs_ok": "All telemetry PVCs are Bound",
    "telemetry_pvcs_failed": "Telemetry PVC issues: {error}",

    # Workload
    "busybox_pod_ok": "BusyBox pod deployed and reached Running state",
    "busybox_pod_failed": "BusyBox pod deployment failed: {error}",
}

# =============================================================================
# KUBERNETES TEST ASSERTION MESSAGES
# =============================================================================
_BORDER = "\u2550" * 74

TEST_ASSERT_MSGS: Dict[str, str] = {
    "k8s_enabled_required": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBERNETES NOT ENABLED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Kubernetes functional groups not found in orchestrator config.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Add service_kube_* groups to pxe_mapping_file.csv\n"
        "\u2551   2. Verify orchestrator_config.yml references K8s nodes\n"
        "\u2551   3. Re-run orchestrator with --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "k8s_nodes_not_ready": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBERNETES NODES NOT READY\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Some Kubernetes nodes are not in Ready state.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check node status: kubectl get nodes -o wide\n"
        "\u2551   2. Check kubelet logs: journalctl -u kubelet -f\n"
        "\u2551   3. Check containerd: systemctl status containerd\n"
        "\u2551   4. Verify network connectivity between nodes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "kubelet_not_running": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBELET SERVICE NOT RUNNING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 kubelet is not active on one or more nodes.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. SSH to the node and check: systemctl status kubelet\n"
        "\u2551   2. Check kubelet logs: journalctl -xeu kubelet\n"
        "\u2551   3. Verify /etc/kubernetes/kubelet.conf exists\n"
        "\u2551   4. Restart kubelet: systemctl restart kubelet\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "containerd_not_running": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 CONTAINERD SERVICE NOT RUNNING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 containerd is not active on one or more nodes.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. SSH to the node and check: systemctl status containerd\n"
        "\u2551   2. Check containerd logs: journalctl -xeu containerd\n"
        "\u2551   3. Restart containerd: systemctl restart containerd\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "system_pods_not_running": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBE-SYSTEM PODS NOT RUNNING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Some kube-system pods are not in Running state.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check pods: kubectl get pods -n kube-system\n"
        "\u2551   2. Describe failing pods: kubectl describe pod <name> -n kube-system\n"
        "\u2551   3. Check pod logs: kubectl logs <name> -n kube-system\n"
        "\u2551   4. Verify node resources: kubectl top nodes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "apiserver_not_responding": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBERNETES API SERVER NOT RESPONDING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 The Kubernetes API server is not responding.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check API server pod: kubectl get pods -n kube-system | grep apiserver\n"
        "\u2551   2. Check static pod manifest: /etc/kubernetes/manifests/kube-apiserver.yaml\n"
        "\u2551   3. Check API server logs: kubectl logs kube-apiserver-<node> -n kube-system\n"
        "\u2551   4. Verify etcd is running: kubectl get pods -n kube-system | grep etcd\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "etcd_not_healthy": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 ETCD CLUSTER NOT HEALTHY\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 The etcd cluster is not healthy.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check etcd pods: kubectl get pods -n kube-system | grep etcd\n"
        "\u2551   2. Check etcd logs: kubectl logs etcd-<node> -n kube-system\n"
        "\u2551   3. Verify etcd data dir: /var/lib/etcd\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "k8s_dirs_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBERNETES DIRECTORIES MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Required Kubernetes directories are missing on nodes.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Re-run K8s provisioning: --tags provision_kubernetes\n"
        "\u2551   2. Verify kubeadm init completed successfully\n"
        "\u2551   3. Check /etc/kubernetes/ directory permissions\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "k8s_config_files_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBERNETES CONFIG FILES MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Required Kubernetes configuration files are missing.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Re-run kubeadm init on control plane\n"
        "\u2551   2. Verify /etc/kubernetes/admin.conf exists\n"
        "\u2551   3. Re-run K8s provisioning: --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "k8s_pki_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBERNETES PKI CERTIFICATES MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Required PKI certificate files are missing.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check /etc/kubernetes/pki/ on control plane nodes\n"
        "\u2551   2. Re-run kubeadm init to regenerate certificates\n"
        "\u2551   3. Re-run K8s provisioning: --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "ssh_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 PASSWORDLESS SSH CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Passwordless SSH is not configured between K8s nodes.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Verify SSH keys are distributed to all nodes\n"
        "\u2551   2. Check provision_preamble.yml ran successfully\n"
        "\u2551   3. Re-run: --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "pod_create_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 POD CREATION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Could not create and schedule a test pod.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check available resources: kubectl top nodes\n"
        "\u2551   2. Check scheduler: kubectl get pods -n kube-system | grep scheduler\n"
        "\u2551   3. Check events: kubectl get events --sort-by=.metadata.creationTimestamp\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "smd_groups_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 K8S SMD GROUPS NOT REGISTERED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 K8s functional groups not found in SMD.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check SMD API: curl -sk https://localhost:8443/hsm/v2/groups\n"
        "\u2551   2. Re-run provisioning: --tags provision_kubernetes\n"
        "\u2551   3. Check orchestrator logs for SMD registration errors\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "static_pod_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 STATIC POD NOT RUNNING: {component}\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 The {component} static pod is not running on the control plane.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check static pod manifest: /etc/kubernetes/manifests/\n"
        "\u2551   2. Check kubelet logs: journalctl -xeu kubelet\n"
        "\u2551   3. Verify container runtime: crictl ps -a\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "k8s_nfs_config_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 K8S NFS CONFIGURATION MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 K8s NFS configuration directory is missing.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Verify NFS mount: mount | grep nfs\n"
        "\u2551   2. Check /opt/omnia/kubernetes directory exists\n"
        "\u2551   3. Re-run provisioning: --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "node_labels_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 NODE LABELS NOT SET CORRECTLY\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Node labels do not match functional group roles.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check labels: kubectl get nodes --show-labels\n"
        "\u2551   2. Re-run provisioning: --tags provision_kubernetes\n"
        "\u2551   3. Manually apply: kubectl label node <name> <key>=<value>\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "node_taints_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 NODE TAINTS NOT CORRECT\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Control plane node taints are not set correctly.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check taints: kubectl describe nodes | grep Taints\n"
        "\u2551   2. Re-run provisioning: --tags provision_kubernetes\n"
        "\u2551   3. Manually apply: kubectl taint nodes <name> <taint>\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "cluster_info_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBECTL CLUSTER-INFO FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 kubectl cluster-info did not return valid data.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check API server: kubectl get pods -n kube-system | grep apiserver\n"
        "\u2551   2. Verify kubeconfig: kubectl config view\n"
        "\u2551   3. Check network: curl -k https://localhost:6443/healthz\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "dns_resolution_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 DNS RESOLUTION FAILED INSIDE PODS\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 DNS resolution is not working inside Kubernetes pods.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check CoreDNS: kubectl get pods -n kube-system | grep coredns\n"
        "\u2551   2. Check DNS service: kubectl get svc -n kube-system kube-dns\n"
        "\u2551   3. Test from pod: kubectl exec -it <pod> -- nslookup kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "service_create_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 SERVICE CREATION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Could not create a Kubernetes service.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check kube-proxy: kubectl get pods -n kube-system | grep kube-proxy\n"
        "\u2551   2. Check events: kubectl get events --sort-by=.metadata.creationTimestamp\n"
        "\u2551   3. Verify network plugin: kubectl get pods -n kube-system\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "ldap_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 LDAP INTEGRATION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 OpenLDAP integration with Kubernetes is not working.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check LDAP pods: kubectl get pods -A | grep ldap\n"
        "\u2551   2. Verify LDAP config: kubectl get configmap -n kube-system\n"
        "\u2551   3. Re-run provisioning: --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "k8s_worker_nodes_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBERNETES WORKER NODES NOT READY\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Some Kubernetes worker nodes are not in Ready state.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check node status: kubectl get nodes -l '!node-role.kubernetes.io/control-plane'\n"
        "\u2551   2. Check kubelet logs: journalctl -u kubelet -f\n"
        "\u2551   3. Check containerd: systemctl status containerd\n"
        "\u2551   4. Verify network connectivity between nodes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "k8s_control_plane_nodes_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBERNETES CONTROL PLANE NODES NOT READY\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Some Kubernetes control plane nodes are not in Ready state.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check node status: kubectl get nodes -l node-role.kubernetes.io/control-plane\n"
        "\u2551   2. Check kubelet logs: journalctl -u kubelet -f\n"
        "\u2551   3. Check static pods: ls /etc/kubernetes/manifests/\n"
        "\u2551   4. Verify etcd: kubectl get pods -n kube-system | grep etcd\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "k8s_coredns_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 COREDNS NOT RUNNING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 CoreDNS pods are not running in the kube-system namespace.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check CoreDNS pods: kubectl get pods -n kube-system -l k8s-app=kube-dns\n"
        "\u2551   2. Check CoreDNS logs: kubectl logs -n kube-system -l k8s-app=kube-dns\n"
        "\u2551   3. Verify CoreDNS ConfigMap: kubectl get configmap coredns -n kube-system -o yaml\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "k8s_kube_proxy_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBE-PROXY NOT RUNNING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 kube-proxy pods are not running in the kube-system namespace.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check kube-proxy pods: kubectl get pods -n kube-system -l k8s-app=kube-proxy\n"
        "\u2551   2. Check kube-proxy logs: kubectl logs -n kube-system -l k8s-app=kube-proxy\n"
        "\u2551   3. Verify kube-proxy DaemonSet: kubectl get ds kube-proxy -n kube-system\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "k8s_metadata_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 K8S METADATA-SERVICE NOT CONFIGURED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 K8s metadata-service configuration is missing.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check metadata-service deployment\n"
        "\u2551   2. Re-run provisioning: --tags provision_kubernetes\n"
        "\u2551   3. Check orchestrator logs for metadata-service errors\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "crio_not_running": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 CRI-O SERVICE NOT RUNNING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 CRI-O (crio/cri-o) is not active on one or more nodes.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. SSH to the node and check: systemctl status crio\n"
        "\u2551   2. Check CRI-O logs: journalctl -xeu crio\n"
        "\u2551   3. Re-run provisioning: --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "chronyd_not_running": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 CHRONYD SERVICE NOT RUNNING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 chronyd is not active on one or more control plane nodes.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. SSH to the node and check: systemctl status chronyd\n"
        "\u2551   2. Install chrony: dnf install chrony\n"
        "\u2551   3. Enable and start: systemctl enable --now chronyd\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "kubectl_version_mismatch": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBECTL VERSION MISMATCH\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 kubectl version does not match software_config.json.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check software_config.json for expected version\n"
        "\u2551   2. Re-run provisioning: --tags provision_kubernetes\n"
        "\u2551   3. Manual install: dnf install kubectl-<version>\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "kubeadm_crio_mismatch": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBEADM/CRI-O VERSION MISMATCH\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 kubeadm and CRI-O versions do not match on control planes.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check versions: kubeadm version && crio --version\n"
        "\u2551   2. Re-run provisioning: --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "container_runtime_mismatch": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 CONTAINER RUNTIME MISMATCH\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Not all nodes are using the expected container runtime.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check: kubectl get nodes -o wide\n"
        "\u2551   2. Verify CRI-O on affected nodes\n"
        "\u2551   3. Re-run provisioning: --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "component_status_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 K8S COMPONENTS NOT HEALTHY\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Some K8s cluster components are not Healthy.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check: kubectl get componentstatus\n"
        "\u2551   2. Check etcd, scheduler, controller-manager pods\n"
        "\u2551   3. Review kubelet logs on control plane nodes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "etcd_health_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 ETCD ENDPOINTS NOT HEALTHY\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Some etcd endpoints are not healthy.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check etcd pods: kubectl get pods -n kube-system | grep etcd\n"
        "\u2551   2. Run etcdctl endpoint health inside etcd pod\n"
        "\u2551   3. Check etcd data dir and logs\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "etcd_member_list_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 ETCD MEMBER LIST MISMATCH\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 etcd member count does not match control plane count.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run etcdctl member list inside etcd pod\n"
        "\u2551   2. Verify all control plane nodes have joined etcd\n"
        "\u2551   3. Re-run provisioning: --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "etcd_leader_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 ETCD LEADER/CONSISTENCY ISSUE\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 etcd leader not found or RAFT terms inconsistent.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run etcdctl endpoint status -w json inside each etcd pod\n"
        "\u2551   2. Check etcd cluster logs for election issues\n"
        "\u2551   3. Verify network connectivity between control planes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "vip_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 VIRTUAL IP NOT CONFIGURED CORRECTLY\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 VIP should be on exactly one control plane node.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check VIP: ip -4 -o addr show on each control plane\n"
        "\u2551   2. Check kube-vip pods: kubectl get pods -A | grep kube-vip\n"
        "\u2551   3. Verify high_availability_config.yml\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "kube_vip_pods_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 KUBE-VIP PODS NOT RUNNING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 kube-vip pods are not running on control plane nodes.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check: kubectl get pods -A | grep kube-vip\n"
        "\u2551   2. Verify /etc/kubernetes/manifests/kube-vip.yaml exists\n"
        "\u2551   3. Re-run provisioning: --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "calico_pods_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 CALICO PODS NOT RUNNING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Calico network pods are not all running.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check: kubectl get pods -A | grep calico\n"
        "\u2551   2. Check calico-node logs: kubectl logs -n kube-system <calico-pod>\n"
        "\u2551   3. Verify network configuration\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "metallb_pods_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 METALLB PODS NOT RUNNING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 MetalLB system pods are not all running.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check: kubectl get pods -n metallb-system\n"
        "\u2551   2. Check MetalLB logs: kubectl logs -n metallb-system <pod>\n"
        "\u2551   3. Verify MetalLB installation\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "nfs_provisioner_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 NFS PROVISIONER NOT RUNNING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 NFS client provisioner pod is not running.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check: kubectl get pods -A | grep nfs\n"
        "\u2551   2. Verify NFS server connectivity\n"
        "\u2551   3. Re-run provisioning: --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "default_sc_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 DEFAULT STORAGE CLASS MISMATCH\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 The default StorageClass does not match expected.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check: kubectl get sc\n"
        "\u2551   2. Set default: kubectl patch sc <name> -p '{{\"metadata\":{{\"annotations\":{{\"storageclass.kubernetes.io/is-default-class\":\"true\"}}}}}}'\n"
        "\u2551   3. Re-run provisioning: --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "persistent_volumes_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 PERSISTENT VOLUMES NOT BOUND\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Some Persistent Volumes are not in Bound state.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check: kubectl get pv\n"
        "\u2551   2. Describe failing PVs: kubectl describe pv <name>\n"
        "\u2551   3. Verify storage backend connectivity\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "nfs_sc_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 NFS STORAGECLASS VALIDATION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 NFS StorageClass is not properly configured.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check: kubectl get sc nfs-client -o yaml\n"
        "\u2551   2. Verify NFS provisioner is running\n"
        "\u2551   3. Re-run provisioning: --tags provision_kubernetes\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "telemetry_pvcs_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 TELEMETRY PVCS NOT BOUND\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Some telemetry PVCs are not in Bound state.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check: kubectl get pvc -n telemetry\n"
        "\u2551   2. Verify storage provisioner is running\n"
        "\u2551   3. Describe failing PVCs: kubectl describe pvc -n telemetry <name>\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "busybox_pod_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 BUSYBOX POD DEPLOYMENT FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Could not deploy and run a basic BusyBox pod.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check available resources: kubectl top nodes\n"
        "\u2551   2. Check scheduler: kubectl get pods -n kube-system | grep scheduler\n"
        "\u2551   3. Check events: kubectl get events\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
}
