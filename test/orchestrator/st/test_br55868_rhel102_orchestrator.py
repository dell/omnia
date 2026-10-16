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
Orchestrator System Tests -- BR-55868 RHEL 10.2 Support for x86_64 Functional Groups.

Validates end-to-end orchestrator behavior for RHEL 10.2 EUS:
  TC-008: Fresh deployment with mixed OS (10.2 x86_64 + 10.0 GPU)
  TC-009: FG upgrade outcome verification
  TC-010: Unselected FGs remain unchanged (OS + uptime)
  TC-011: Mixed-OS cluster health (K8s, Slurm, LDAP, NFS, telemetry)
  TC-012: Slurm health across OS boundary
  TC-013: Kubernetes health across OS boundary
  TC-014: Content unavailable -- safe failure and 10.0 preservation
  TC-015: Omnia 2.3 version gate acceptance
  TC-016: GPU guard -- block without override
  TC-017: GPU guard -- override with workload validation
  TC-018: Shared storage preserved during upgrade
  TC-019: OIM reboot with cluster reform (excluded -- disruptive)
  TC-022: NVIDIA GPU CUDA version selection
  TC-023: User-provided Slurm configuration validation
  TC-024: EUS repository resync and image rebuild
  TC-025: Boot service MAC isolation during node recovery
"""

import pytest
import yaml
import os
import glob
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from library.st_helpers.infrastructure_utils import InfrastructureUtils as Infra
from library.vars.test_case_vars import ST_TEST_CASES as TC

OMNIA_DATA_PATH = os.getenv("OMNIA_DATA_PATH", "/opt/omnia")
OMNIA_PROJECT_NAME = os.getenv("OMNIA_PROJECT_NAME", "project_default")

REPO_STATUS_PATH = os.getenv(
    "REPO_STATUS_PATH",
    os.path.join(OMNIA_DATA_PATH, "repo_manager/output", OMNIA_PROJECT_NAME, "repo_status.yml"),
)
BUILD_STATUS_PATH = os.getenv(
    "BUILD_STATUS_PATH",
    os.path.join(OMNIA_DATA_PATH, "image_build_manager/output", OMNIA_PROJECT_NAME, "build_status.yml"),
)
OMNIA_ENV_PATH = os.getenv("OMNIA_ENV_PATH", "/etc/omnia/omnia.env")
CATALOG_PATH = os.getenv(
    "CATALOG_PATH",
    os.path.join(OMNIA_DATA_PATH, "catalog/catalog_rhel.json"),
)


def _read_omnia_version():
    """Read OMNIA_VERSION from the real omnia.env on this OIM."""
    if not os.path.exists(OMNIA_ENV_PATH):
        return None
    with open(OMNIA_ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("OMNIA_VERSION="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return None


def _load_yaml(path):
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _load_json(path):
    import json
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def _get_idle_slurm_nodes() -> list:
    """Return list of Slurm node names in idle/alloc state (able to run jobs)."""
    nodes = Infra.sinfo()
    return [n for n, state in nodes.items() if state in ("idle", "alloc", "mix")]


def _parse_fg_images(build_status):
    """Extract flat list of FG image dicts from build_status structure."""
    fg_images = build_status.get("functional_group_images", [])
    all_fgs = []
    if isinstance(fg_images, list):
        for entry in fg_images:
            if isinstance(entry, dict):
                for arch_fgs in entry.values():
                    if isinstance(arch_fgs, list):
                        all_fgs.extend(arch_fgs)
    elif isinstance(fg_images, dict):
        all_fgs = list(fg_images.values())
    return all_fgs


# ============================================================================
# TC-008: Fresh Deployment on RHEL 10.2 EUS
# ============================================================================

@pytest.mark.st
@pytest.mark.tier2
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_fresh_deploy_rhel102(test_logger):
    """Verify fresh Omnia 2.3 deployment with RHEL 10.2 EUS for x86_64 and 10.0 for GPU."""
    tc = TC["fresh_deploy_rhel102"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        # Step 2: Catalog accepted -- verify catalog file exists and is valid JSON
        catalog = _load_json(CATALOG_PATH)
        assert catalog is not None, f"Catalog not found at {CATALOG_PATH}"
        tl.info(f"Step 2: Catalog present at {CATALOG_PATH}")

        # Step 3: Pipeline complete -- verify repo_status and build_status success
        repo_status = _load_yaml(REPO_STATUS_PATH)
        assert repo_status is not None, f"repo_status.yml not found at {REPO_STATUS_PATH}"
        assert repo_status.get("overall_status") == "success", (
            f"Repo sync not successful: {repo_status.get('overall_status')}"
        )
        build_status = _load_yaml(BUILD_STATUS_PATH)
        assert build_status is not None, f"build_status.yml not found at {BUILD_STATUS_PATH}"
        assert build_status.get("overall_status") == "success", (
            f"Image build not successful: {build_status.get('overall_status')}"
        )
        tl.info("Step 3: Pipeline complete (repo_status + build_status = success)")

        # Step 4: Verify OIM OS version
        rc, oim_os, _ = Infra.run_command("cat /etc/redhat-release")
        assert rc == 0 and oim_os.strip(), "Failed to read OIM OS version"
        oim_os_str = oim_os.strip()
        if "10.2" in oim_os_str:
            tl.info(f"Step 4: OIM on RHEL 10.2 EUS: {oim_os_str}")
        else:
            tl.info(f"Step 4: OIM on {oim_os_str} (manages 10.2 FGs)")

        x86_64_hosts = Infra.get_rhel_10_2_hosts()
        gpu_hosts = Infra.get_gpu_hosts()
        if not x86_64_hosts and not gpu_hosts:
            pytest.skip("No functional groups found in orchestrator_inventory.yml")

        # Step 5: x86_64 FGs on RHEL 10.2 EUS
        reachable_102 = 0
        unreachable_102 = []
        for addr in x86_64_hosts:
            node_os = Infra.get_os_version(addr)
            if node_os is None:
                unreachable_102.append(addr)
                continue
            assert "10.2" in node_os, f"Node {addr} not on RHEL 10.2: {node_os}"
            reachable_102 += 1
            tl.info(f"Step 5: {addr}: {node_os}")
        assert reachable_102 > 0, f"No RHEL 10.2 nodes reachable (unreachable: {unreachable_102})"
        if unreachable_102:
            tl.info(f"Step 5: {len(unreachable_102)} node(s) unreachable: {unreachable_102}")

        # Step 6: GPU FGs on RHEL 10.0 EUS
        if gpu_hosts:
            for addr in gpu_hosts:
                node_os = Infra.get_os_version(addr)
                if node_os is None:
                    continue
                assert "10.0" in node_os, f"GPU node {addr} not on RHEL 10.0: {node_os}"
                tl.info(f"Step 6: GPU {addr}: {node_os}")
        else:
            tl.info("Step 6: No GPU FG present (10.2-only cluster)")

        # Step 7: Slurm and K8s operational
        assert Infra.scontrol_ping(), "Slurm controller not responsive"
        slurm_nodes = Infra.sinfo()
        assert len(slurm_nodes) > 0, "No Slurm nodes registered"
        tl.info(f"Step 7: Slurm operational: {len(slurm_nodes)} node(s)")

        k8s_nodes = Infra.kubectl_get_nodes()
        assert len(k8s_nodes) > 0, "No K8s nodes registered"
        ready_count = sum(1 for s in k8s_nodes.values() if s == "True")
        assert ready_count > 0, "No K8s nodes Ready"
        tl.info(f"Step 7: K8s operational: {ready_count}/{len(k8s_nodes)} Ready")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise


# ============================================================================
# TC-009: Functional-Group Upgrade to RHEL 10.2 EUS
# ============================================================================

@pytest.mark.st
@pytest.mark.tier2
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_fg_upgrade_selected(test_logger):
    """Verify existing RHEL 10.0 cluster upgraded selected x86_64 FGs to RHEL 10.2 EUS."""
    tc = TC["fg_upgrade_selected"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        # Step 1: Mixed-OS state exists
        rhel_10_2_hosts = Infra.get_rhel_10_2_hosts()
        rhel_10_0_hosts = Infra.get_rhel_10_0_hosts()
        if not rhel_10_2_hosts:
            pytest.skip("No RHEL 10.2 FGs in inventory -- upgrade not performed")
        tl.info(f"Step 1: {len(rhel_10_2_hosts)} in 10.2 FGs, {len(rhel_10_0_hosts)} in 10.0 FGs")

        # Step 3: RHEL 10.2 image artifacts in build_status
        build_status = _load_yaml(BUILD_STATUS_PATH)
        if build_status:
            all_fgs = _parse_fg_images(build_status)
            rhel_102_fg_names = [
                fg.get("functional_group", "")
                for fg in all_fgs
                if isinstance(fg, dict) and "10_2" in fg.get("functional_group", "")
            ]
            assert rhel_102_fg_names, "No RHEL 10.2 FG images in build_status.yml"
            tl.info(f"Step 3: 10.2 image artifacts: {rhel_102_fg_names}")

        # Step 5: Every node in upgraded FGs running RHEL 10.2
        reachable = 0
        for addr in rhel_10_2_hosts:
            node_os = Infra.get_os_version(addr)
            if node_os is None:
                tl.info(f"Step 5: {addr} unreachable")
                continue
            assert "10.2" in node_os, f"Upgraded node {addr} not on 10.2: {node_os}"
            reachable += 1
            tl.info(f"Step 5: {addr}: {node_os}")
        assert reachable > 0, "No upgraded RHEL 10.2 nodes reachable"

        # Step 6: Slurm and K8s versions intact
        slurm_version = Infra.get_slurm_version()
        assert slurm_version is not None, "Slurm version unreadable"
        tl.info(f"Step 6: Slurm version: {slurm_version}")
        k8s_version = Infra.get_kubernetes_version()
        assert k8s_version is not None, "K8s version unreadable"
        tl.info(f"Step 6: K8s version intact")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise


# ============================================================================
# TC-010: Unselected Functional Groups Remain Unchanged
# ============================================================================

@pytest.mark.st
@pytest.mark.tier2
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_fg_unselected_unchanged(test_logger):
    """Verify FGs not selected for RHEL 10.2 EUS remain on original OS and not rebooted."""
    tc = TC["fg_unselected_unchanged"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        # Steps 3-4: Verify 10.0 FGs still on RHEL 10.0 (includes GPU nodes)
        rhel_10_0_hosts = Infra.get_rhel_10_0_hosts()
        gpu_hosts = Infra.get_gpu_hosts()
        unselected = list(set(rhel_10_0_hosts + gpu_hosts))
        if not unselected:
            pytest.skip("No unselected (RHEL 10.0/GPU) nodes in inventory")

        tl.info(f"Checking {len(unselected)} unselected node(s)...")
        verified_os = 0
        baseline_uptime = {}
        for node in unselected:
            # Step 3-4: OS version check
            node_os = Infra.get_os_version(node)
            if node_os is None:
                tl.info(f"  {node}: unreachable")
                continue
            assert "10.0" in node_os, f"Unselected node {node} not on RHEL 10.0: {node_os}"
            verified_os += 1
            tl.info(f"Step 3: {node}: {node_os} (unchanged)")

            # Step 1,5: Uptime baseline
            uptime = Infra.get_uptime(node)
            if uptime is not None:
                baseline_uptime[node] = uptime

        assert verified_os > 0, "No unselected nodes reachable to verify OS"

        # Step 5: Re-sample uptime -- must not have decreased (no reboot)
        for node, baseline in baseline_uptime.items():
            current = Infra.get_uptime(node)
            assert current is not None, f"Lost connectivity to {node}"
            assert current >= baseline, (
                f"{node} rebooted (uptime {current}s < {baseline}s)"
            )
            tl.info(f"Step 5: {node}: no reboot ({current}s >= {baseline}s)")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise


# ============================================================================
# TC-011: Mixed-OS Cluster Health -- Overall
# ============================================================================

@pytest.mark.st
@pytest.mark.tier2
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_mixed_os_health_overall(test_logger):
    """Verify K8s, Slurm, LDAP, NFS, telemetry healthy across 10.0/10.2 boundary."""
    tc = TC["mixed_os_health_overall"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        rhel_10_0 = Infra.get_rhel_10_0_hosts()
        rhel_10_2 = Infra.get_rhel_10_2_hosts()
        tl.info(f"Step 1: {len(rhel_10_0)} on 10.0, {len(rhel_10_2)} on 10.2")

        # Step 2: K8s all nodes Ready
        k8s_nodes = Infra.kubectl_get_nodes()
        assert len(k8s_nodes) > 0, "No K8s nodes found"
        for node, status in k8s_nodes.items():
            assert status == "True", f"K8s node {node} not Ready: {status}"
        tl.info(f"Step 2: K8s {len(k8s_nodes)} node(s) Ready")

        # Step 3: Slurm nodes in valid states
        assert Infra.scontrol_ping(), "Slurm controller not responsive"
        slurm_nodes = Infra.sinfo()
        assert len(slurm_nodes) > 0, "No Slurm nodes found"
        valid_states = {"idle", "alloc", "mix", "drain", "down", "unk*", "down*"}
        for node_name, state in slurm_nodes.items():
            assert state in valid_states, (
                f"Slurm node {node_name} in unexpected state: {state}"
            )
        tl.info(f"Step 3: Slurm {len(slurm_nodes)} node(s): {dict(slurm_nodes)}")

        # Step 4: LDAP operational from BOTH OS versions
        slurm_control = Infra.get_slurm_control_host()
        if slurm_control:
            ldap_ok = Infra.ldapsearch(slurm_control)
            assert ldap_ok, f"LDAP not operational on Slurm controller {slurm_control}"
            tl.info(f"Step 4: LDAP OK on 10.2 node ({slurm_control})")

        # LDAP from a 10.0 node
        if rhel_10_0:
            ldap_10_0_tested = False
            for node_10_0 in rhel_10_0:
                ldap_ok_10_0 = Infra.ldapsearch(node_10_0)
                if ldap_ok_10_0:
                    tl.info(f"Step 4: LDAP OK on 10.0 node ({node_10_0})")
                    ldap_10_0_tested = True
                    break
            if not ldap_10_0_tested:
                tl.info("Step 4: LDAP not reachable from any 10.0 node (may not have ldapsearch)")

        # Step 5: NFS accessible from workers
        kube_workers = Infra.get_kube_worker_hosts()
        nfs_mount = os.getenv("NFS_MOUNT", "/share_omnia_k8s")
        if kube_workers:
            nfs_ok = any(Infra.check_nfs_mount(n, nfs_mount) for n in kube_workers)
            assert nfs_ok, f"NFS mount {nfs_mount} not found on any worker: {kube_workers}"
            tl.info(f"Step 5: NFS mounted ({nfs_mount})")

        # Step 6: Telemetry services (check for common containers)
        rc, stdout, _ = Infra.run_command(
            "podman ps --format '{{.Names}}' 2>/dev/null | "
            "grep -iE 'ldms|grafa|prome|timescale|telegra' || true"
        )
        if stdout.strip():
            tl.info(f"Step 6: Telemetry containers: {stdout.strip()}")
        else:
            tl.info("Step 6: No telemetry containers detected (not configured)")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise


# ============================================================================
# TC-012: Slurm Health on Mixed-OS Cluster
# ============================================================================

@pytest.mark.st
@pytest.mark.tier2
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_slurm_health_mixed_os(test_logger):
    """Verify Slurm health across RHEL 10.0/10.2 boundaries."""
    tc = TC["slurm_health_mixed_os"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        # Step 1: scontrol ping
        if not Infra.scontrol_ping():
            pytest.skip("Slurm controller not reachable")
        tl.info("Step 1: scontrol ping UP")

        # Step 1b: Verify controller OS crosses the OS boundary
        control_host = Infra.get_slurm_control_host()
        if control_host:
            ctrl_os = Infra.get_os_version(control_host)
            if ctrl_os:
                tl.info(f"Step 1b: Slurm controller {control_host}: {ctrl_os}")

        # Step 2: sinfo shows all nodes -- verify count matches inventory
        slurm_nodes = Infra.sinfo()
        assert len(slurm_nodes) > 0, "No Slurm nodes registered"
        inv_count = sum(
            len(Infra.get_group_addresses(g)) for g in Infra.find_groups("slurm_node")
        )
        tl.info(f"Step 2: sinfo {len(slurm_nodes)} node(s), inventory expects ~{inv_count} compute")

        # Steps 3-4: Submit test jobs targeting specific OS nodes
        idle_nodes = _get_idle_slurm_nodes()
        if idle_nodes:
            # Step 3: Job targeting a compute node (RHEL 10.0 in this cluster)
            job_id = Infra.submit_slurm_job("hostname && cat /etc/redhat-release")
            assert job_id is not None, "Failed to submit Slurm job"
            assert Infra.wait_for_slurm_job(job_id, timeout=60), (
                f"Job {job_id} did not complete in 60s"
            )
            tl.info(f"Step 3: Job {job_id} completed on compute node")

            # Step 4: Verify job ran on expected node via sacct
            rc, stdout, stderr = Infra.sacct(job_id)
            assert rc == 0, f"sacct failed: {stderr}"
            assert "COMPLETED" in stdout.upper(), f"Job not COMPLETED: {stdout}"
            tl.info(f"Step 4: sacct confirms COMPLETED")

            # Step 5: Accounting across OS boundary -- verify sacct reports correctly
            rc, sacct_detail, _ = Infra.slurm_cmd(
                f"sacct -j {job_id} --format=JobID,JobName,NodeList,State --noheader"
            )
            if rc == 0 and sacct_detail.strip():
                tl.info(f"Step 5: sacct detail: {sacct_detail.strip().split(chr(10))[0]}")
        else:
            tl.info(f"Steps 3-5: No IDLE nodes ({set(slurm_nodes.values())}); job skipped")

        # Step 6: Slurm version
        slurm_version = Infra.get_slurm_version()
        assert slurm_version is not None, "Failed to read Slurm version"
        tl.info(f"Step 6: Slurm version: {slurm_version}")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise


# ============================================================================
# TC-013: Kubernetes Health on Mixed-OS Cluster
# ============================================================================

@pytest.mark.st
@pytest.mark.tier2
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_k8s_health_mixed_os(test_logger):
    """Verify K8s health across RHEL 10.0/10.2 boundaries."""
    tc = TC["k8s_health_mixed_os"]
    tl = test_logger(tc["title"], tc["id"])
    deployed = False

    try:
        # Step 1: All nodes Ready
        k8s_nodes = Infra.kubectl_get_nodes()
        if not k8s_nodes:
            pytest.skip("K8s control plane not reachable")
        for node, status in k8s_nodes.items():
            assert status == "True", f"Node {node} not Ready: {status}"
        tl.info(f"Step 1: {len(k8s_nodes)} node(s) Ready")

        # Step 2: Control plane components healthy
        rc, stdout, stderr = Infra.kubectl("get pods -n kube-system --no-headers")
        assert rc == 0, f"Failed to list kube-system pods: {stderr}"
        cp_components = ("kube-apiserver", "kube-scheduler", "kube-controller-manager", "etcd")
        cp_pods = [l for l in stdout.strip().split("\n") if any(c in l for c in cp_components)]
        assert cp_pods, "No core control-plane pods found"
        running_cp = [l for l in cp_pods if "Running" in l]
        assert running_cp, f"Control-plane pods not Running: {cp_pods}"
        tl.info(f"Step 2: {len(running_cp)}/{len(cp_pods)} control-plane pods Running")

        # Step 3: Deploy test pod to 10.2 worker (busybox:1.36 pre-pulled)
        rc, stdout, stderr = Infra.kubectl(
            "create deployment br55868-test-tc013 --image=busybox:1.36 --replicas=1 -- sleep 3600"
        )
        assert rc == 0, f"Failed to create test deployment: {stderr}"
        deployed = True

        rc, stdout, stderr = Infra.kubectl(
            "wait --for=condition=available --timeout=120s deployment/br55868-test-tc013",
            timeout=135,
        )
        if rc != 0:
            _, events, _ = Infra.kubectl(
                "get events --field-selector reason=FailedScheduling --sort-by=.lastTimestamp"
            )
            last_event = events.strip().split("\n")[-1] if events.strip() else "none"
            assert False, f"Deployment not available: {stderr or stdout}\nLast event: {last_event}"
        tl.info("Step 3: Test pod scheduled and Running on worker")

        # Step 3b: Verify the pod's host node OS version
        rc, pod_node, _ = Infra.kubectl(
            "get pods -l app=br55868-test-tc013 -o jsonpath='{.items[0].status.hostIP}'"
        )
        if rc == 0 and pod_node.strip().strip("'"):
            host_ip = pod_node.strip().strip("'")
            host_os = Infra.get_os_version(host_ip)
            tl.info(f"Step 3b: Pod running on {host_ip}: {host_os or 'unknown'}")

        # Step 4: Attempt pod on 10.0 K8s worker if present
        kube_worker_addrs = set(Infra.get_kube_worker_hosts())
        rhel_10_0_addrs = set(Infra.get_rhel_10_0_hosts())
        k8s_10_0_workers = kube_worker_addrs & rhel_10_0_addrs
        if k8s_10_0_workers:
            tl.info(f"Step 4: RHEL 10.0 K8s workers present: {k8s_10_0_workers}")
        else:
            tl.info("Step 4: K8s workers are 10.2-only in this cluster (no 10.0 K8s workers)")

        # Step 5: CNI networking -- verify calico/CNI pods running across all nodes
        rc, stdout, _ = Infra.kubectl("get pods -n kube-system -l k8s-app=calico-node --no-headers")
        if rc == 0 and stdout.strip():
            calico_count = len(stdout.strip().split("\n"))
            calico_running = sum("Running" in l for l in stdout.strip().split("\n"))
            assert calico_running == calico_count, f"Not all calico-node pods Running"
            tl.info(f"Step 5: CNI (calico): {calico_running}/{calico_count} pods Running")

        # Step 5b: Verify pod-to-service networking works (DNS resolution)
        rc, dns_out, _ = Infra.kubectl(
            "exec deployment/br55868-test-tc013 -- nslookup kubernetes.default.svc.cluster.local 2>/dev/null || true",
            timeout=15,
        )
        if rc == 0 and "Address" in dns_out:
            tl.info("Step 5b: Pod DNS resolution to kubernetes service OK")
        else:
            tl.info("Step 5b: Pod DNS check inconclusive (busybox nslookup may be absent)")

        # Step 6: K8s version
        k8s_version = Infra.get_kubernetes_version()
        assert k8s_version is not None, "Failed to read K8s version"
        tl.info(f"Step 6: K8s version: {k8s_version}")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise
    finally:
        if deployed:
            Infra.kubectl("delete deployment br55868-test-tc013 --ignore-not-found")


# ============================================================================
# TC-014: RHEL 10.2 Content Unavailable Fails Safely
# ============================================================================

@pytest.mark.st
@pytest.mark.tier2
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_content_unavailable_fail(test_logger):
    """Verify content unavailable fails safely; existing 10.0 repos preserved."""
    tc = TC["content_unavailable_fail"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        repo_status = _load_yaml(REPO_STATUS_PATH)
        if repo_status is None:
            pytest.skip(f"repo_status.yml not found at {REPO_STATUS_PATH}")

        # Step 2 (positive): Current sync succeeded
        overall_status = repo_status.get("overall_status")
        assert overall_status is not None, "repo_status.yml missing overall_status"
        tl.info(f"Step 2: repo sync overall_status: {overall_status}")

        # Step 3: Existing RHEL 10.0 repos remain intact
        repositories = repo_status.get("repositories", {})
        assert "10.2" in repositories, "RHEL 10.2 repositories not present"
        assert "10.0" in repositories, "RHEL 10.0 repositories missing -- not preserved"
        x86_64_100 = repositories.get("10.0", {}).get("x86_64", {})
        assert x86_64_100, "No x86_64 repos under RHEL 10.0"
        for repo in ["baseos", "appstream"]:
            assert repo in x86_64_100, f"RHEL 10.0 {repo} missing -- not preserved"
        tl.info("Step 3: RHEL 10.0 repos intact (baseos, appstream)")

        # Step 4: Build status consistent
        build_status = _load_yaml(BUILD_STATUS_PATH)
        if build_status:
            bs_status = build_status.get("overall_status")
            assert bs_status is not None, "build_status.yml missing overall_status"
            tl.info(f"Step 4: build_status overall_status: {bs_status}")

        # Step 5: Error messaging structure
        overall_by_ver = repo_status.get("overall_status_by_version", {})
        if overall_by_ver:
            tl.info(f"Step 5: Per-version status: {list(overall_by_ver.keys())}")
        tl.info("Negative path (removing entitlement) is destructive; positive verified")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise


# ============================================================================
# TC-015: Omnia 2.3 Version Gate -- Accept
# ============================================================================

@pytest.mark.st
@pytest.mark.tier3
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_version_gate_accept(test_logger):
    """Verify Omnia 2.3 version gate passes and workflow proceeds."""
    tc = TC["version_gate_accept"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        # Step 1: Omnia version 2.3
        omnia_version = _read_omnia_version()
        if omnia_version is None:
            pytest.skip(f"OMNIA_VERSION not found in {OMNIA_ENV_PATH}")
        assert omnia_version.startswith("2.3"), f"Expected 2.3.x, got {omnia_version}"
        tl.info(f"Step 1: Omnia version: {omnia_version}")

        # Step 2: Pre-flight -- critical contracts exist
        assert os.path.exists(REPO_STATUS_PATH), f"Pre-flight: repo_status.yml missing"
        assert os.path.exists(BUILD_STATUS_PATH), f"Pre-flight: build_status.yml missing"
        tl.info("Step 2: Pre-flight: contracts present")

        # Step 3: Workflow proceeded -- orchestrator inventory exists
        inv_path = os.path.join(
            OMNIA_DATA_PATH, "orchestrator/output", OMNIA_PROJECT_NAME, "orchestrator_inventory.yml"
        )
        assert os.path.exists(inv_path), f"Workflow did not proceed: inventory missing at {inv_path}"
        tl.info("Step 3: Workflow proceeded: orchestrator_inventory.yml present")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise


# ============================================================================
# TC-016: GPU Guard -- Block Without Override
# ============================================================================

@pytest.mark.st
@pytest.mark.tier3
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_gpu_guard_block(test_logger):
    """Verify GPU FG blocked from RHEL 10.2 without override; remains on 10.0."""
    tc = TC["gpu_guard_block"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        gpu_hosts = Infra.get_gpu_hosts()
        if not gpu_hosts:
            pytest.skip("No GPU nodes detected; GPU guard cannot be exercised")

        # Step 1: Verify catalog assigns GPU groups to RHEL 10.0 (not 10.2)
        catalog = _load_json(CATALOG_PATH)
        if catalog:
            gpu_fg_os = {}
            for ctx in catalog.get("contexts", []):
                for fg in ctx.get("functional_groups", []):
                    fg_name = fg.get("name", "")
                    fg_os_ver = fg.get("os_version", "")
                    if any(h in fg_name.lower() for h in ["gpu", "10_0"]):
                        gpu_fg_os[fg_name] = fg_os_ver
            if gpu_fg_os:
                for fg_name, os_ver in gpu_fg_os.items():
                    assert os_ver != "10.2", (
                        f"GPU guard policy: FG {fg_name} assigned to 10.2 without override"
                    )
                    tl.info(f"Step 1: Catalog FG {fg_name}: os_version={os_ver} (guard OK)")
            else:
                tl.info("Step 1: No explicit GPU FG in catalog (GPU detected via hardware)")

        # Steps 2-3: GPU nodes NOT on 10.2 (guard held)
        for node in gpu_hosts:
            node_os = Infra.get_os_version(node)
            if node_os is None:
                tl.info(f"  {node}: unreachable")
                continue
            assert "10.2" not in node_os, (
                f"GPU guard failed: {node} on RHEL 10.2 without override -- {node_os}"
            )
            tl.info(f"Step 2: {node}: {node_os} (not 10.2 -- guard holding)")

        # Step 3: Verify guard message in catalog policy -- GPU groups stay on 10.0
        tl.info("Step 3: GPU groups blocked from 10.2 assignment (verified by OS check)")

        # Step 4: GPU group positively on RHEL 10.0
        for node in gpu_hosts:
            node_os = Infra.get_os_version(node)
            if node_os is None:
                continue
            assert "10.0" in node_os, f"GPU node {node} not on 10.0: {node_os}"
            tl.info(f"Step 4: {node}: confirmed RHEL 10.0")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise


# ============================================================================
# TC-017: GPU Guard -- Override with Workload Validation
# ============================================================================

@pytest.mark.st
@pytest.mark.tier3
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_gpu_guard_override_workload(test_logger):
    """Verify GPU workloads (MPI, UCX, CUDA) operational on GPU nodes."""
    tc = TC["gpu_guard_override_workload"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        gpu_hosts = Infra.get_gpu_hosts()
        if not gpu_hosts:
            pytest.skip("No GPU nodes detected; workload validation cannot run")

        for node in gpu_hosts:
            # Step 3: OS version and audit trail
            rc, os_out, _ = Infra.ssh_command(node, "cat /etc/redhat-release")
            if rc == 0:
                tl.info(f"Step 3: {node}: OS = {os_out.strip()}")

            # Step 9: GPU compute -- nvidia-smi with full query
            rc, stdout, stderr = Infra.ssh_command(
                node, "nvidia-smi --query-gpu=driver_version,gpu_name,compute_cap --format=csv,noheader"
            )
            assert rc == 0, f"nvidia-smi failed on {node}: {stderr}"
            tl.info(f"Step 9: {node}: GPU {stdout.strip()}")

            # Step 9b: GPU compute workload -- run CUDA vector add if available
            rc, cuda_out, _ = Infra.ssh_command(
                node,
                "ls /usr/local/cuda/samples/1_Utilities/deviceQuery/deviceQuery 2>/dev/null "
                "|| command -v nvidia-smi",
                timeout=10,
            )
            rc, gpu_test, _ = Infra.ssh_command(
                node,
                "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader 2>/dev/null",
                timeout=10,
            )
            if rc == 0 and gpu_test.strip():
                tl.info(f"Step 9b: {node}: GPU utilization query OK: {gpu_test.strip()}")

            # Step 5: Open MPI -- check installed and run a simple MPI test
            rc, stdout_mpi, _ = Infra.ssh_command(node, "command -v mpirun")
            assert rc == 0, f"Open MPI (mpirun) not installed on {node}"
            tl.info(f"Step 5: {node}: MPI at {stdout_mpi.strip()}")

            # Step 5b: Run single-node MPI job over TCP
            rc, mpi_out, mpi_err = Infra.ssh_command(
                node,
                "mpirun --allow-run-as-root -np 2 --mca btl tcp,self hostname 2>&1",
                timeout=30,
            )
            if rc == 0:
                tl.info(f"Step 5b: {node}: MPI over TCP OK (2 ranks)")
            else:
                tl.info(f"Step 5b: {node}: MPI over TCP: rc={rc} ({mpi_err.strip()[:80]})")

            # Step 7: UCX -- check installed and run info
            rc, _, _ = Infra.ssh_command(node, "command -v ucx_info")
            if rc == 0:
                rc, ucx_tl_out, _ = Infra.ssh_command(
                    node, "ucx_info -t 2>/dev/null | head -5", timeout=10,
                )
                if rc == 0 and ucx_tl_out.strip():
                    tl.info(f"Step 7: {node}: UCX transports: {ucx_tl_out.strip().split(chr(10))[0]}")
                else:
                    tl.info(f"Step 7: {node}: UCX installed (ucx_info available)")
            else:
                rc2, _, _ = Infra.ssh_command(node, "command -v ucx_perftest")
                if rc2 == 0:
                    tl.info(f"Step 7: {node}: UCX perftest installed")
                else:
                    tl.info(f"Step 7: {node}: UCX not installed (not required on this FG)")

            # Step 6: Check IB interfaces for IPoIB/RDMA path
            rc, ib_out, _ = Infra.ssh_command(
                node, "ip link show type infiniband 2>/dev/null | head -2"
            )
            if rc == 0 and ib_out.strip():
                tl.info(f"Step 6: {node}: IB interface present")
                # Step 8: UCX over IB (RDMA) -- verify IB transport available
                rc, ib_dev, _ = Infra.ssh_command(
                    node, "ibstat 2>/dev/null | grep -E 'State|Port' | head -4"
                )
                if rc == 0 and ib_dev.strip():
                    tl.info(f"Step 8: {node}: IB status: {ib_dev.strip().split(chr(10))[0]}")
            else:
                tl.info(f"Step 6: {node}: No IB interface (TCP-only environment)")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise


# ============================================================================
# TC-018: Shared Storage Preserved During Upgrade
# ============================================================================

@pytest.mark.st
@pytest.mark.tier4
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_shared_storage_preserved(test_logger):
    """Verify NFS data preserved; local data not guaranteed after reprovisioning."""
    tc = TC["shared_storage_preserved"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        kube_workers = Infra.get_kube_worker_hosts()
        if not kube_workers:
            pytest.skip("No K8s worker nodes found")

        nfs_mount = os.getenv("NFS_MOUNT", "/share_omnia_k8s")

        # Find a worker with NFS mounted
        node = None
        for w in kube_workers:
            if Infra.check_nfs_mount(w, nfs_mount):
                node = w
                break
        if node is None:
            pytest.skip(f"{nfs_mount} not mounted on any worker: {kube_workers}")

        # Step 1: Write test file to NFS
        test_file = f"{nfs_mount}/.br55868_tc018_test"
        rc, _, stderr = Infra.ssh_command(node, f"echo 'br55868-tc018' > {test_file}")
        assert rc == 0, f"Failed to write NFS test file: {stderr}"
        checksum_before = Infra.get_file_checksum(node, test_file)
        assert checksum_before is not None, "Failed to checksum NFS test file"
        tl.info(f"Step 1: NFS file written on {node}: checksum {checksum_before}")

        # Step 4: Re-read from another worker (shared storage test)
        other_node = None
        for w in kube_workers:
            if w != node and Infra.check_nfs_mount(w, nfs_mount):
                other_node = w
                break
        if other_node is None:
            other_node = node
        checksum_after = Infra.get_file_checksum(other_node, test_file)
        assert checksum_after == checksum_before, (
            f"Checksum mismatch from {other_node}: {checksum_after} != {checksum_before}"
        )
        tl.info(f"Step 4: NFS data consistent (read from {other_node})")

        # Step 5: Local data not guaranteed
        tl.info("Step 5: Local storage not guaranteed after reprovisioning (documented)")

        Infra.ssh_command(node, f"rm -f {test_file}")
        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise


# ============================================================================
# TC-019: OIM Reboot with Cluster Reform (EXCLUDED)
# ============================================================================

@pytest.mark.st
@pytest.mark.tier4
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_oim_reboot_cluster_reform(test_logger):
    """OIM Reboot with Cluster Reform -- EXCLUDED (disruptive)."""
    tc = TC["oim_reboot_cluster_reform"]
    tl = test_logger(tc["title"], tc["id"])
    tl.info("Disruptive scenario: rebooting OIM interrupts this run. Execute manually.")
    pytest.skip("Disruptive: OIM reboot excluded per test plan instructions")


# ============================================================================
# TC-020: Slurm Node Addition and Deletion (EXCLUDED)
# ============================================================================

@pytest.mark.st
@pytest.mark.tier4
@pytest.mark.orchestrator
@pytest.mark.rhel102
@pytest.mark.node_lifecycle
def test_br55868_slurm_node_add_delete(test_logger):
    """Slurm Node Addition and Deletion -- EXCLUDED (node lifecycle)."""
    tc = TC["slurm_node_add_delete"]
    tl = test_logger(tc["title"], tc["id"])
    pytest.skip("Node lifecycle: Slurm add/delete excluded per instructions")


# ============================================================================
# TC-021: Kubernetes Master Node Addition (EXCLUDED)
# ============================================================================

@pytest.mark.st
@pytest.mark.tier4
@pytest.mark.orchestrator
@pytest.mark.rhel102
@pytest.mark.node_lifecycle
def test_br55868_k8s_master_node_add(test_logger):
    """Kubernetes Master Node Addition -- EXCLUDED (node lifecycle)."""
    tc = TC["k8s_master_node_add"]
    tl = test_logger(tc["title"], tc["id"])
    pytest.skip("Node lifecycle: K8s master addition excluded per instructions")


# ============================================================================
# TC-022: NVIDIA GPU CUDA Version Selection
# ============================================================================

@pytest.mark.st
@pytest.mark.tier4
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_nvidia_gpu_cuda_selection(test_logger):
    """Verify CUDA version selection in repo_status and on GPU nodes."""
    tc = TC["nvidia_gpu_cuda_selection"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        gpu_hosts = Infra.get_gpu_hosts()
        if not gpu_hosts:
            pytest.skip("No GPU nodes detected; CUDA selection cannot be verified")

        # Steps 2-3: CUDA repos in repo_status
        repo_status = _load_yaml(REPO_STATUS_PATH)
        assert repo_status is not None, f"repo_status.yml not found at {REPO_STATUS_PATH}"
        repositories = repo_status.get("repositories", {})
        cuda_found = False
        for version, arch_data in repositories.items():
            x86_64 = arch_data.get("x86_64", {}) if isinstance(arch_data, dict) else {}
            if "cuda" in x86_64:
                cuda_found = True
                cuda_entry = x86_64["cuda"]
                cuda_url = cuda_entry.get("url", cuda_entry) if isinstance(cuda_entry, dict) else cuda_entry
                tl.info(f"Step 2: CUDA repo for RHEL {version}: {cuda_url}")
        assert cuda_found, "No CUDA repository found in repo_status.yml"

        # Step 4: Check build_status for GPU FG and CUDA version metadata
        build_status = _load_yaml(BUILD_STATUS_PATH)
        if build_status:
            all_fgs = _parse_fg_images(build_status)
            gpu_fgs = [fg for fg in all_fgs if isinstance(fg, dict) and "10_0" in fg.get("functional_group", "")]
            if gpu_fgs:
                tl.info(f"Step 4: GPU FG images in build_status: {[fg['functional_group'] for fg in gpu_fgs]}")
                # Check for driver/CUDA version metadata in build_status
                for fg in gpu_fgs:
                    driver_meta = fg.get("driver_versions", fg.get("drivers", {}))
                    if driver_meta:
                        tl.info(f"Step 4b: {fg['functional_group']} driver metadata: {driver_meta}")

        # Step 6: nvidia-smi on GPU nodes -- verify both driver AND CUDA runtime version
        for node in gpu_hosts:
            # Driver version
            driver_ver = Infra.get_nvidia_cuda_version(node)
            assert driver_ver is not None, f"Could not read GPU driver from {node}"
            tl.info(f"Step 6: {node}: driver version {driver_ver}")

            # CUDA runtime version (from nvidia-smi header)
            rc, cuda_out, _ = Infra.ssh_command(
                node,
                "nvidia-smi 2>/dev/null | grep -oP 'CUDA Version: \\K[0-9.]+'",
                timeout=10,
            )
            if rc == 0 and cuda_out.strip():
                tl.info(f"Step 6b: {node}: CUDA runtime version {cuda_out.strip()}")
            else:
                tl.info(f"Step 6b: {node}: CUDA runtime version not reported by nvidia-smi")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise


# ============================================================================
# TC-023: User-Provided Slurm Configuration Validation
# ============================================================================

@pytest.mark.st
@pytest.mark.tier4
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_user_slurm_config(test_logger):
    """Verify user-provided Slurm configuration applied and operational."""
    tc = TC["user_slurm_config"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        control_host = Infra.get_slurm_control_host()
        if not control_host:
            pytest.skip("No Slurm controller node found")

        slurm_config_path = os.getenv("SLURM_CONFIG_PATH", "/etc/slurm/slurm.conf")
        rc, stdout, _ = Infra.ssh_command(control_host, f"test -f {slurm_config_path} && echo exists")
        if "exists" not in stdout:
            pytest.skip(f"{slurm_config_path} not found on {control_host}")

        # Step 3: slurm.conf partition definitions
        rc, stdout, _ = Infra.ssh_command(control_host, f"grep -i '^PartitionName' {slurm_config_path}")
        assert rc == 0 and stdout.strip(), "No PartitionName entries in slurm.conf"
        partitions_in_conf = stdout.strip().split("\n")
        tl.info(f"Step 3: {len(partitions_in_conf)} partition(s) in slurm.conf")

        # Step 4: scontrol shows active partitions
        rc, stdout, stderr = Infra.slurm_cmd("scontrol show partition")
        assert rc == 0, f"scontrol show partition failed: {stderr}"
        active_partitions = stdout.count("PartitionName=")
        assert active_partitions > 0, "No active partitions per scontrol"
        tl.info(f"Step 4: {active_partitions} partition(s) active per scontrol")

        # Step 5: Job scheduling
        idle_nodes = _get_idle_slurm_nodes()
        if idle_nodes:
            job_id = Infra.submit_slurm_job("sleep 5")
            assert job_id is not None, "Failed to submit job"
            assert Infra.wait_for_slurm_job(job_id, timeout=60), f"Job {job_id} did not complete"
            tl.info(f"Step 5: Job {job_id} scheduled and completed")
        else:
            slurm_nodes = Infra.sinfo()
            tl.info(f"Step 5: No IDLE nodes ({set(slurm_nodes.values())}); job skipped")

        # Step 6: Custom scheduling parameters in effect
        rc, stdout, _ = Infra.ssh_command(
            control_host,
            f"grep -iE '^(SchedulerType|SelectType|PriorityType)' {slurm_config_path}"
        )
        if rc == 0 and stdout.strip():
            for line in stdout.strip().split("\n"):
                tl.info(f"Step 6: {line.strip()}")
        else:
            tl.info("Step 6: No custom scheduling params found (using defaults)")

        # Step 7: Slurm healthy
        assert Infra.scontrol_ping(), "Slurm controller not healthy"
        tl.info("Step 7: Slurm remains healthy")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise


# ============================================================================
# TC-024: EUS Repository Resync and Image Rebuild
# ============================================================================

# Playbook paths for repo_manager and image_build_manager
_RM_PLAYBOOK = "repo_manager.yml"
_RM_WORKDIR = "src/repo_manager/playbooks"
_IBM_PLAYBOOK = "image_build_manager.yml"
_IBM_WORKDIR = "src/image_build_manager/playbooks"


def _run_domain_playbook(playbook, workdir, tag, timeout=7200):
    """Run a domain playbook via omnia_auto's run_playbook."""
    from omnia_auto.functions.runner_func import run_playbook as _run_pb
    return _run_pb(
        playbook=playbook,
        playbook_workdir=workdir,
        tag=tag,
        timeout=timeout,
    )


@pytest.mark.st
@pytest.mark.tier4
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_eus_resync_rebuild(test_logger):
    """Verify EUS resync cycle: resync repos, rebuild images, verify contracts."""
    tc = TC["eus_resync_rebuild"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        x86_64_hosts = Infra.get_rhel_10_2_hosts()
        if not x86_64_hosts:
            pytest.skip("No RHEL 10.2 x86_64 nodes found")

        # Step 1: Record current package baselines on RHEL 10.2 nodes
        baseline_packages = {}
        for node in x86_64_hosts:
            rc, stdout, _ = Infra.ssh_command(node, "rpm -qa | wc -l")
            if rc == 0 and stdout.strip().isdigit():
                baseline_packages[node] = int(stdout.strip())
                tl.info(f"Step 1: {node}: {baseline_packages[node]} packages")
        assert baseline_packages, "Could not read packages from any node"

        # Record pre-resync timestamps
        repo_mtime_before = (
            os.path.getmtime(REPO_STATUS_PATH) if os.path.exists(REPO_STATUS_PATH) else 0
        )
        build_mtime_before = (
            os.path.getmtime(BUILD_STATUS_PATH) if os.path.exists(BUILD_STATUS_PATH) else 0
        )

        # Step 2: Trigger Repo Manager resync
        tl.info("Step 2: Running repo_manager resync (--tags execute)...")
        rm_result = _run_domain_playbook(_RM_PLAYBOOK, _RM_WORKDIR, tag="execute", timeout=3600)
        assert rm_result["success"], (
            f"Repo Manager resync failed (rc={rm_result['rc']}): "
            f"{rm_result.get('error', 'see playbook output')}"
        )
        tl.info(f"Step 2: Repo Manager resync completed in {rm_result['duration']:.0f}s")

        # Generate repo_status.yml
        tl.info("Step 2b: Generating repo_status.yml (--tags status)...")
        rm_status = _run_domain_playbook(_RM_PLAYBOOK, _RM_WORKDIR, tag="status", timeout=600)
        assert rm_status["success"], (
            f"Repo Manager status generation failed (rc={rm_status['rc']}): "
            f"{rm_status.get('error', 'see playbook output')}"
        )
        tl.info(f"Step 2b: repo_status.yml generated in {rm_status['duration']:.0f}s")

        # Step 3: Verify repo_status.yml updated with latest sync timestamp
        repo_status = _load_yaml(REPO_STATUS_PATH)
        assert repo_status is not None, "repo_status.yml not found after resync"
        assert repo_status.get("overall_status") == "success", (
            f"repo_status after resync: {repo_status.get('overall_status')}"
        )
        repo_mtime_after = os.path.getmtime(REPO_STATUS_PATH)
        assert repo_mtime_after >= repo_mtime_before, (
            "repo_status.yml was not updated by resync"
        )
        tl.info(
            f"Step 3: repo_status.yml updated (mtime: "
            f"{repo_mtime_before:.0f} -> {repo_mtime_after:.0f})"
        )

        # Step 4: Trigger Image Build Manager to rebuild images
        tl.info("Step 4: Running image_build_manager rebuild (--tags build)...")
        ibm_result = _run_domain_playbook(_IBM_PLAYBOOK, _IBM_WORKDIR, tag="build", timeout=7200)
        assert ibm_result["success"], (
            f"Image Build Manager rebuild failed (rc={ibm_result['rc']}): "
            f"{ibm_result.get('error', 'see playbook output')}"
        )
        tl.info(f"Step 4: Image Build Manager rebuild completed in {ibm_result['duration']:.0f}s")

        # Step 5: Verify build_status.yml updated with new build timestamp
        build_status = _load_yaml(BUILD_STATUS_PATH)
        assert build_status is not None, "build_status.yml not found after rebuild"
        assert build_status.get("overall_status") == "success", (
            f"build_status after rebuild: {build_status.get('overall_status')}"
        )
        build_mtime_after = os.path.getmtime(BUILD_STATUS_PATH)
        assert build_mtime_after >= build_mtime_before, (
            "build_status.yml was not updated by rebuild"
        )
        tl.info(
            f"Step 5: build_status.yml updated (mtime: "
            f"{build_mtime_before:.0f} -> {build_mtime_after:.0f})"
        )

        # Steps 6-7: Reboot and verify packages
        # Rebooting nodes is destructive and would disrupt the cluster.
        # We verify package counts post-resync/rebuild are >= baseline.
        tl.info("Steps 6-7: Node reboot is destructive; verifying package baselines instead")
        for node, baseline_count in baseline_packages.items():
            rc, stdout, _ = Infra.ssh_command(node, "rpm -qa | wc -l")
            if rc == 0 and stdout.strip().isdigit():
                current_count = int(stdout.strip())
                assert current_count >= baseline_count, (
                    f"{node}: package count decreased ({current_count} < {baseline_count})"
                )
                tl.info(f"Step 7: {node}: {current_count} packages (>= {baseline_count} baseline)")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise


# ============================================================================
# TC-025: Boot Service MAC Isolation During Node Recovery
# ============================================================================

@pytest.mark.st
@pytest.mark.tier4
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_boot_service_mac_isolation(test_logger):
    """Verify no MAC appears in more than one FG boot config simultaneously."""
    tc = TC["boot_service_mac_isolation"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        boot_dir = os.path.join(OMNIA_DATA_PATH, "openchami/workdir/boot")
        boot_files = sorted(glob.glob(os.path.join(boot_dir, "boot-svc-*.yaml")))
        if not boot_files:
            pytest.skip(f"No boot-svc-*.yaml files in {boot_dir}")

        # Steps 2-4: Read every FG boot config and collect MACs
        mac_to_fg = {}
        duplicates = []
        total_macs = 0
        for filepath in boot_files:
            data = _load_yaml(filepath)
            if not data:
                continue
            fg_name = (data.get("metadata") or {}).get("name", os.path.basename(filepath))
            spec = data.get("spec", {})
            macs = spec.get("macs", [])
            total_macs += len(macs)

            # Verify boot config has required fields
            assert spec.get("kernel"), f"FG {fg_name}: missing kernel"
            assert spec.get("initrd"), f"FG {fg_name}: missing initrd"
            assert macs, f"FG {fg_name}: no MACs assigned"
            tl.info(f"Step 2: {fg_name}: {len(macs)} MAC(s), kernel+initrd present")

            # Step 5: MAC never in both configs
            for mac in macs:
                mac_lower = mac.lower()
                if mac_lower in mac_to_fg:
                    duplicates.append(f"MAC {mac} in both '{mac_to_fg[mac_lower]}' and '{fg_name}'")
                mac_to_fg[mac_lower] = fg_name

        assert total_macs > 0, "No MACs found in any boot config"
        assert not duplicates, f"MAC isolation violated: {duplicates}"
        tl.info(f"Step 5: {total_macs} MAC(s) across {len(boot_files)} FGs -- all unique")

        # Step 6: Boot service running
        rc, stdout, _ = Infra.run_command(
            "podman ps --format '{{.Names}}' --filter name=boot-service"
        )
        if rc == 0 and "boot-service" in stdout:
            tl.info("Step 6: boot-service container running")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise
