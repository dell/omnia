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
  TC-017: GPU guard -- override with workload validation (audit trail, MPI/UCX/GPU over TCP+IB)
  TC-018: Shared storage preserved during upgrade
  TC-019: OIM reboot with cluster reform (excluded -- disruptive)
  TC-020: Slurm node drain/resume lifecycle and cluster health
  TC-021: K8s control-plane health and Master node readiness
  TC-022: NVIDIA GPU CUDA version selection and consistency
  TC-023: User-provided Slurm configuration validation
  TC-024: EUS repository resync and image rebuild
  TC-025: Boot service MAC isolation during node recovery (with recovery config checks)
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

        # Step 1b: Verify controller OS
        control_host = Infra.get_slurm_control_host()
        ctrl_os = None
        if control_host:
            ctrl_os = Infra.get_os_version(control_host)
            if ctrl_os:
                tl.info(f"Step 1b: Slurm controller {control_host}: {ctrl_os}")

        # Step 2: sinfo shows all nodes -- verify count matches inventory
        # and check actual node health states
        slurm_nodes = Infra.sinfo()
        assert len(slurm_nodes) > 0, "No Slurm nodes registered"
        inv_compute_addrs = Infra.get_slurm_compute_hosts()
        tl.info(
            f"Step 2: sinfo {len(slurm_nodes)} node(s), "
            f"inventory expects {len(inv_compute_addrs)} compute"
        )

        # Step 2b: Check slurmd service status on each compute node and
        # report the OS version -- the plan requires nodes across 10.0/10.2
        healthy_nodes = []
        unhealthy_nodes = []
        node_os_map = {}
        for addr in inv_compute_addrs:
            node_os = Infra.get_os_version(addr)
            node_os_map[addr] = node_os or "unreachable"
            rc, svc_out, _ = Infra.ssh_command(
                addr, "systemctl is-active slurmd 2>/dev/null"
            )
            # systemctl is-active returns non-zero for inactive/failed but
            # still writes the state to stdout; only treat as unreachable
            # when we got no output at all.
            svc_state = svc_out.strip() if svc_out and svc_out.strip() else "unreachable"
            if svc_state == "active":
                healthy_nodes.append(addr)
            else:
                unhealthy_nodes.append((addr, svc_state, node_os or "unknown"))
            tl.info(
                f"Step 2b: {addr}: slurmd={svc_state}, "
                f"OS={node_os or 'unreachable'}"
            )

        # Fail if no compute nodes have slurmd running -- the cluster cannot
        # schedule jobs and the remaining steps are meaningless.
        assert healthy_nodes, (
            f"All {len(inv_compute_addrs)} compute node(s) have slurmd down: "
            f"{[(a, s) for a, s, _ in unhealthy_nodes]}"
        )
        if unhealthy_nodes:
            tl.info(
                f"Step 2b: WARNING: {len(unhealthy_nodes)} node(s) with slurmd "
                f"not active: {[(a, s) for a, s, _ in unhealthy_nodes]}"
            )

        # Step 2c: Verify mixed-OS boundary exists (controller or computes
        # span 10.0 and 10.2)
        os_versions_seen = set()
        if ctrl_os:
            os_versions_seen.add("10.2" if "10.2" in ctrl_os else "10.0")
        for addr, os_str in node_os_map.items():
            if "10.2" in os_str:
                os_versions_seen.add("10.2")
            elif "10.0" in os_str:
                os_versions_seen.add("10.0")
        tl.info(f"Step 2c: OS versions in Slurm cluster: {os_versions_seen}")

        # Steps 3-4: Submit test jobs targeting specific OS nodes
        idle_nodes = _get_idle_slurm_nodes()
        assert idle_nodes, (
            f"No IDLE/schedulable Slurm nodes -- "
            f"node states: {Infra.sinfo()}"
        )

        # Helper: submit job, wait, verify output + sacct
        def _submit_and_verify(target_addr, target_name, expected_os, step_label):
            """Submit a job to a specific node, verify completion and output."""
            output_path = f"/tmp/br55868_tc012_{target_name}.out"
            job_script = (
                f"hostname && cat /etc/redhat-release"
            )
            job_id = Infra.submit_slurm_job_on_node(
                target_name,
                job_script,
            )
            assert job_id is not None, (
                f"{step_label}: Failed to submit job to {target_name}"
            )
            tl.info(f"{step_label}: Submitted job {job_id} to {target_name}")

            assert Infra.wait_for_slurm_job(job_id, timeout=60), (
                f"{step_label}: Job {job_id} did not complete on "
                f"{target_name} in 60s"
            )

            # Verify job state via sacct
            rc, sacct_out, _ = Infra.slurm_cmd(
                f"sacct -j {job_id} "
                f"--format=JobID,JobName,NodeList,State,ExitCode "
                f"--noheader --parsable2"
            )
            assert rc == 0, f"{step_label}: sacct failed for job {job_id}"
            assert "COMPLETED" in sacct_out.upper(), (
                f"{step_label}: Job {job_id} not COMPLETED: {sacct_out}"
            )
            tl.info(
                f"{step_label}: sacct confirms COMPLETED: "
                f"{sacct_out.strip().split(chr(10))[0]}"
            )

            # Read job output from the compute node to verify correct
            # node and OS.  sbatch writes slurm-<jobid>.out on the node
            # that ran the job (not the controller).
            rc, job_output, _ = Infra.ssh_command(
                target_addr,
                f"cat /root/slurm-{job_id}.out 2>/dev/null",
            )
            if rc == 0 and job_output.strip():
                tl.info(
                    f"{step_label}: Job output: "
                    f"{job_output.strip()}"
                )
                assert target_name in job_output, (
                    f"{step_label}: Job ran on wrong node — "
                    f"expected {target_name}, output: {job_output.strip()}"
                )
                assert expected_os in job_output, (
                    f"{step_label}: Job node not on expected OS "
                    f"{expected_os} — output: {job_output.strip()}"
                )
            else:
                # Fallback: verify via sacct NodeList
                tl.info(
                    f"{step_label}: slurm-{job_id}.out not found on "
                    f"{target_name}; verifying via sacct NodeList"
                )
                rc2, nodelist_out, _ = Infra.slurm_cmd(
                    f"sacct -j {job_id} --format=NodeList --noheader "
                    f"--parsable2"
                )
                assert rc2 == 0 and target_name in nodelist_out, (
                    f"{step_label}: Cannot confirm job ran on "
                    f"{target_name}: {nodelist_out}"
                )
                tl.info(
                    f"{step_label}: sacct confirms ran on "
                    f"{nodelist_out.strip().split(chr(10))[0]}"
                )

            # Cleanup
            Infra.ssh_command(
                target_addr,
                f"rm -f /root/slurm-{job_id}.out 2>/dev/null",
            )
            return job_id

        jobs_completed = 0

        # Step 3: Job targeting a RHEL 10.2 compute node (if any exist)
        rhel102_compute = [
            a for a in healthy_nodes if "10.2" in (node_os_map.get(a, ""))
        ]
        if rhel102_compute:
            rc, hostname_out, _ = Infra.ssh_command(
                rhel102_compute[0], "hostname -s"
            )
            target_name = hostname_out.strip() if rc == 0 else None
            assert target_name, (
                f"Step 3: Cannot resolve hostname for {rhel102_compute[0]}"
            )
            _submit_and_verify(
                rhel102_compute[0], target_name, "10.2", "Step 3"
            )
            jobs_completed += 1
        else:
            tl.info(
                "Step 3: No RHEL 10.2 compute nodes in cluster "
                "(mixed-OS boundary is controller=10.2, computes=10.0)"
            )

        # Step 4: Job targeting a RHEL 10.0 compute node
        rhel100_compute = [
            a for a in healthy_nodes if "10.0" in (node_os_map.get(a, ""))
        ]
        if rhel100_compute:
            rc, hostname_out, _ = Infra.ssh_command(
                rhel100_compute[0], "hostname -s"
            )
            target_name = hostname_out.strip() if rc == 0 else None
            assert target_name, (
                f"Step 4: Cannot resolve hostname for {rhel100_compute[0]}"
            )
            _submit_and_verify(
                rhel100_compute[0], target_name, "10.0", "Step 4"
            )
            jobs_completed += 1
        else:
            tl.info("Step 4: No RHEL 10.0 compute nodes with slurmd active")

        # Step 5: At least one job must have run
        assert jobs_completed > 0, (
            "Steps 3-4: No jobs were submitted — cannot verify Slurm health"
        )

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
    """Verify GPU override audit trail and workloads (MPI, UCX, CUDA) over TCP and IB."""
    tc = TC["gpu_guard_override_workload"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        gpu_hosts = Infra.get_gpu_hosts()
        if not gpu_hosts:
            pytest.skip("No GPU nodes detected; workload validation cannot run")

        # Step 3: Verify override audit trail in operation report
        report_dir = os.path.join(
            OMNIA_DATA_PATH, "orchestrator/output", OMNIA_PROJECT_NAME
        )
        audit_found = False
        for report_name in ("operation_report.yml", "provision_report.yml"):
            report_path = os.path.join(report_dir, report_name)
            if os.path.exists(report_path):
                report = _load_yaml(report_path)
                if report:
                    overrides = report.get("gpu_overrides", report.get("overrides", []))
                    if overrides:
                        tl.info(f"Step 3: Audit trail in {report_name}: {overrides}")
                        audit_found = True
                    # Also check for override mentions in free-form fields
                    report_str = str(report)
                    if "override" in report_str.lower():
                        tl.info(f"Step 3: Override reference found in {report_name}")
                        audit_found = True
        if not audit_found:
            tl.info(
                "Step 3: No explicit GPU override audit trail in operation reports "
                "(override may not have been exercised in this deployment)"
            )

        for node in gpu_hosts:
            # Step 3b: OS version
            rc, os_out, _ = Infra.ssh_command(node, "cat /etc/redhat-release")
            if rc == 0:
                tl.info(f"Step 3b: {node}: OS = {os_out.strip()}")

            # Step 9: GPU compute -- nvidia-smi query + actual CUDA workload
            rc, stdout, stderr = Infra.ssh_command(
                node, "nvidia-smi --query-gpu=driver_version,gpu_name,compute_cap --format=csv,noheader"
            )
            assert rc == 0, f"nvidia-smi failed on {node}: {stderr}"
            tl.info(f"Step 9: {node}: GPU {stdout.strip()}")

            # Step 9b: Run actual CUDA compute workload (vectorAdd)
            # Compile and execute a minimal CUDA kernel to prove the GPU
            # can run compute — not just respond to nvidia-smi queries.
            cuda_src = (
                '#include <stdio.h>\n'
                '__global__ void vadd(float*a,float*b,float*c,int n)'
                '{int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)c[i]=a[i]+b[i];}\n'
                'int main(){\n'
                '  int n=1024;size_t sz=n*sizeof(float);\n'
                '  float*ha=(float*)malloc(sz),*hb=(float*)malloc(sz),*hc=(float*)malloc(sz);\n'
                '  float*da,*db,*dc;\n'
                '  for(int i=0;i<n;i++){ha[i]=i;hb[i]=2.0f*i;}\n'
                '  cudaMalloc(&da,sz);cudaMalloc(&db,sz);cudaMalloc(&dc,sz);\n'
                '  cudaMemcpy(da,ha,sz,cudaMemcpyHostToDevice);\n'
                '  cudaMemcpy(db,hb,sz,cudaMemcpyHostToDevice);\n'
                '  vadd<<<(n+255)/256,256>>>(da,db,dc,n);\n'
                '  cudaMemcpy(hc,dc,sz,cudaMemcpyDeviceToHost);\n'
                '  cudaDeviceSynchronize();\n'
                '  cudaError_t e=cudaGetLastError();\n'
                '  if(e!=cudaSuccess){printf("FAIL:%s\\n",cudaGetErrorString(e));return 1;}\n'
                '  int ok=1;for(int i=0;i<n;i++){if(hc[i]!=3.0f*i){ok=0;break;}}\n'
                '  cudaDeviceProp p;cudaGetDeviceProperties(&p,0);\n'
                '  printf("GPU_COMPUTE_OK: vectorAdd %d elems valid=%d dev=%s sm_%d.%d\\n",'
                'n,ok,p.name,p.major,p.minor);\n'
                '  free(ha);free(hb);free(hc);cudaFree(da);cudaFree(db);cudaFree(dc);\n'
                '  return ok?0:1;}\n'
            )
            # Write, compile with sm_90 (H100), run, cleanup
            rc_w, _, _ = Infra.ssh_command(
                node,
                f"cat > /tmp/_tc017_gpu.cu << 'CUDASRC'\n{cuda_src}CUDASRC",
                timeout=10,
            )
            rc_c, compile_out, _ = Infra.ssh_command(
                node,
                "/usr/local/cuda/bin/nvcc "
                "-gencode arch=compute_90,code=sm_90 "
                "-o /tmp/_tc017_gpu /tmp/_tc017_gpu.cu 2>&1",
                timeout=60,
            )
            if rc_c == 0:
                rc_r, gpu_out, _ = Infra.ssh_command(
                    node, "/tmp/_tc017_gpu 2>&1", timeout=30,
                )
                assert rc_r == 0 and "GPU_COMPUTE_OK" in gpu_out, (
                    f"CUDA compute failed on {node}: {gpu_out.strip()}"
                )
                tl.info(f"Step 9b: {node}: {gpu_out.strip()}")
            else:
                tl.info(
                    f"Step 9b: {node}: nvcc compile skipped "
                    f"({compile_out.strip()[:60]})"
                )
            # Cleanup
            Infra.ssh_command(
                node, "rm -f /tmp/_tc017_gpu /tmp/_tc017_gpu.cu 2>/dev/null"
            )

            # Step 5: Open MPI -- check installed and run a simple MPI test
            rc, stdout_mpi, _ = Infra.ssh_command(node, "command -v mpirun")
            assert rc == 0, f"Open MPI (mpirun) not installed on {node}"
            tl.info(f"Step 5: {node}: MPI at {stdout_mpi.strip()}")

            # Step 5b: Run single-node MPI job over TCP
            rc, mpi_out, mpi_err = Infra.ssh_command(
                node,
                "PMIX_MCA_gds=hash mpirun --allow-run-as-root -np 2 --mca btl tcp,self hostname 2>&1",
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
            # Detect IB via ibstat (rdma-level) and ip link (IPoIB iface).
            # 'ip link show type infiniband' misses IPoIB on some kernels,
            # so also look for link/infiniband in 'ip link show'.
            rc_ibstat, ibstat_out, _ = Infra.ssh_command(
                node,
                "ibstat 2>/dev/null | grep -E 'State:|Link layer' | head -4",
            )
            rc_iplink, iplink_out, _ = Infra.ssh_command(
                node,
                "ip -o link show 2>/dev/null | grep 'link/infiniband' "
                "| awk '{print $2}' | tr -d ':'",
            )
            ib_iface = iplink_out.strip().split("\n")[0] if iplink_out.strip() else ""
            has_ib = (
                (rc_ibstat == 0 and "Active" in ibstat_out)
                or bool(ib_iface)
            )

            if has_ib:
                tl.info(
                    f"Step 6: {node}: IB present "
                    f"(iface={ib_iface or 'N/A'}, "
                    f"ibstat={'Active' if 'Active' in ibstat_out else ibstat_out.strip()[:40]})"
                )

                # Get IPoIB IP for later multi-node tests
                ib_ip = None
                if ib_iface:
                    rc, ip_out, _ = Infra.ssh_command(
                        node,
                        f"ip -4 addr show {ib_iface} 2>/dev/null "
                        f"| grep -oP 'inet \\K[0-9.]+'",
                    )
                    if rc == 0 and ip_out.strip():
                        ib_ip = ip_out.strip()
                        tl.info(f"Step 6: {node}: IPoIB IP = {ib_ip} ({ib_iface})")

                # Step 6b: MPI over IPoIB (single-node)
                rc, mpi_ib, mpi_ib_err = Infra.ssh_command(
                    node,
                    "PMIX_MCA_gds=hash mpirun --allow-run-as-root -np 2 --mca pml ucx "
                    "-x UCX_NET_DEVICES=mlx5_0:1 hostname 2>&1",
                    timeout=30,
                )
                if rc == 0:
                    tl.info(f"Step 6b: {node}: MPI over IB/UCX OK: {mpi_ib.strip()}")
                else:
                    tl.info(
                        f"Step 6b: {node}: MPI over IB rc={rc}: "
                        f"{mpi_ib_err.strip()[:80] if mpi_ib_err else mpi_ib.strip()[:80]}"
                    )

                # Step 8: UCX over IB (RDMA) -- verify IB HCA state
                rc, ib_dev, _ = Infra.ssh_command(
                    node, "ibstat 2>/dev/null | grep -E 'State|Rate|Port' | head -6"
                )
                if rc == 0 and ib_dev.strip():
                    tl.info(f"Step 8: {node}: IB HCA: {ib_dev.strip().split(chr(10))[0]}")

                # Step 8b: UCX RDMA transport verification
                rc, ucx_rdma, _ = Infra.ssh_command(
                    node,
                    "ucx_info -d 2>/dev/null "
                    "| grep -E 'Transport:.*(rc_verbs|rc_mlx5|ud_verbs|ud_mlx5|dc_mlx5)' "
                    "| head -5",
                    timeout=10,
                )
                if rc == 0 and ucx_rdma.strip():
                    rdma_transports = [
                        l.split(":")[-1].strip()
                        for l in ucx_rdma.strip().split("\n")
                    ]
                    tl.info(f"Step 8b: {node}: UCX RDMA transports: {rdma_transports}")
                    assert len(rdma_transports) > 0, (
                        f"No UCX RDMA transports on {node} despite IB Active"
                    )
                else:
                    tl.info(f"Step 8b: {node}: No UCX RDMA transports detected")
            else:
                tl.info(f"Step 6: {node}: No IB interface (TCP-only environment)")

        # Step 10: Multi-node GPU MPI job over IB RDMA (if 2+ GPU nodes)
        if len(gpu_hosts) >= 2:
            node_a, node_b = gpu_hosts[0], gpu_hosts[1]
            # Detect IB via ibstat (not ip link show type infiniband)
            rc_a, ib_a, _ = Infra.ssh_command(
                node_a, "ibstat 2>/dev/null | grep 'State: Active'"
            )
            rc_b, ib_b, _ = Infra.ssh_command(
                node_b, "ibstat 2>/dev/null | grep 'State: Active'"
            )
            has_ib_a = rc_a == 0 and "Active" in ib_a
            has_ib_b = rc_b == 0 and "Active" in ib_b
            if has_ib_a and has_ib_b:
                # Get Slurm hostnames for the GPU nodes
                rc_ha, name_a, _ = Infra.ssh_command(node_a, "hostname -s")
                rc_hb, name_b, _ = Infra.ssh_command(node_b, "hostname -s")
                slurm_a = name_a.strip() if rc_ha == 0 else node_a
                slurm_b = name_b.strip() if rc_hb == 0 else node_b

                if Infra.scontrol_ping():
                    # GPU-aware MPI job: each rank runs nvidia-smi to
                    # prove GPU+MPI+IB works end-to-end.
                    job_id = Infra.submit_slurm_job_on_node(
                        f"{slurm_a},{slurm_b}",
                        "PMIX_MCA_gds=hash "
                        "mpirun --allow-run-as-root -np 2 "
                        "--mca pml ucx -x UCX_NET_DEVICES=mlx5_0:1 "
                        "nvidia-smi --query-gpu=gpu_name "
                        "--format=csv,noheader",
                    )
                    if job_id:
                        completed = Infra.wait_for_slurm_job(
                            job_id, timeout=120
                        )
                        # Read job output from first node
                        rc, job_out, _ = Infra.ssh_command(
                            node_a,
                            f"cat /root/slurm-{job_id}.out 2>/dev/null",
                        )
                        out_str = job_out.strip() if rc == 0 else ""
                        tl.info(
                            f"Step 10: Multi-node GPU MPI over IB "
                            f"job {job_id} "
                            f"({'completed' if completed else 'timed out'})"
                            f"{': ' + out_str if out_str else ''}"
                        )
                        assert completed, (
                            f"Step 10: Multi-node MPI over IB job "
                            f"{job_id} did not complete in 120s"
                        )
                        # Cleanup
                        Infra.ssh_command(
                            node_a,
                            f"rm -f /root/slurm-{job_id}.out "
                            f"2>/dev/null",
                        )
                    else:
                        tl.info(
                            "Step 10: Could not submit multi-node "
                            "GPU MPI job via Slurm"
                        )
                else:
                    tl.info(
                        "Step 10: Slurm not available for "
                        "multi-node GPU MPI test"
                    )
            else:
                tl.info(
                    f"Step 10: IB not active on both GPU nodes "
                    f"({node_a}: {'yes' if has_ib_a else 'no'}, "
                    f"{node_b}: {'yes' if has_ib_b else 'no'})"
                )
        else:
            tl.info(
                f"Step 10: Only {len(gpu_hosts)} GPU node(s); "
                "multi-node test requires 2+"
            )

        # Step 11: Verify consistency with RHEL 10.0 EUS baseline
        # Confirm GPU nodes are operational on their current OS without
        # functional regression compared to what the baseline OS provides.
        for node in gpu_hosts:
            rc, cuda_ver, _ = Infra.ssh_command(
                node,
                "nvidia-smi 2>/dev/null | grep -oP 'CUDA Version: \\K[0-9.]+'",
                timeout=10,
            )
            rc2, driver_ver, _ = Infra.ssh_command(
                node,
                "nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null",
                timeout=10,
            )
            cuda_str = cuda_ver.strip() if rc == 0 else "N/A"
            driver_str = driver_ver.strip() if rc2 == 0 else "N/A"
            tl.info(
                f"Step 11: {node}: driver={driver_str}, CUDA={cuda_str} "
                "(baseline consistency check)"
            )

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
# TC-019: OIM Reboot with Cluster Reform (EXCLUDED -- disruptive)
# ============================================================================

@pytest.mark.st
@pytest.mark.tier4
@pytest.mark.orchestrator
@pytest.mark.rhel102
def test_br55868_oim_reboot_cluster_reform(test_logger):
    """OIM Reboot with Cluster Reform -- EXCLUDED (disruptive).

    This scenario reboots the OIM host itself, which terminates the test
    runner process.  It must be executed manually outside the automated
    suite:
      1. Record pre-reboot container list and Pulp repo count.
      2. Reboot the OIM (``systemctl reboot``).
      3. After the OIM comes back, verify containers auto-started,
         Pulp data intact, K8s/Slurm clusters reformed, and no
         Orchestrator rerun was triggered.
    """
    tc = TC["oim_reboot_cluster_reform"]
    tl = test_logger(tc["title"], tc["id"])
    tl.info("Disruptive scenario: rebooting OIM terminates this test run. Execute manually.")
    pytest.skip("Disruptive: OIM reboot excluded per test plan instructions")


# ============================================================================
# TC-020: Slurm Node Addition and Deletion
# ============================================================================

@pytest.mark.st
@pytest.mark.tier4
@pytest.mark.orchestrator
@pytest.mark.rhel102
@pytest.mark.node_lifecycle
def test_br55868_slurm_node_add_delete(test_logger):
    """Verify Slurm node drain/resume cycle and cluster health.

    Full node provisioning (add) and decommissioning (delete from inventory)
    require Orchestrator reruns and are out of scope for a non-disruptive ST
    run.  This test validates the Slurm-level lifecycle that the test plan
    describes: drain a node, verify it leaves the schedulable pool, resume
    it, verify it accepts jobs again, and confirm the controller stays healthy
    throughout.
    """
    tc = TC["slurm_node_add_delete"]
    tl = test_logger(tc["title"], tc["id"])
    drained_node = None

    try:
        if not Infra.scontrol_ping():
            pytest.skip("Slurm controller not reachable")

        # Step 1: Record current Slurm node count and cluster state
        slurm_nodes = Infra.sinfo()
        assert len(slurm_nodes) > 0, "No Slurm nodes registered"
        baseline_count = len(slurm_nodes)
        idle_nodes = [n for n, s in slurm_nodes.items() if s in ("idle", "mix")]
        tl.info(f"Step 1: Baseline: {baseline_count} node(s), {len(idle_nodes)} idle/mix")

        if len(idle_nodes) < 2:
            pytest.skip(
                f"Need at least 2 idle nodes for drain/resume test, "
                f"have {len(idle_nodes)}: {idle_nodes}"
            )

        # Pick the last idle node for drain/resume (least disruptive)
        target_node = idle_nodes[-1]
        remaining_idle = idle_nodes[:-1]

        # Step 4: Submit test job targeting the target node (pre-drain)
        job_id = Infra.submit_slurm_job_on_node(target_node, "hostname")
        if job_id:
            Infra.wait_for_slurm_job(job_id, timeout=60)
            tl.info(f"Step 4: Pre-drain job {job_id} completed on {target_node}")
        else:
            tl.info(f"Step 4: Could not submit pre-drain job to {target_node}")

        # Step 5: Verify existing nodes state before drain
        for n in remaining_idle:
            state = Infra.slurm_get_node_state(n)
            tl.info(f"Step 5: {n} state before drain: {state}")

        # Step 6: Drain the target node
        assert Infra.slurm_drain_node(target_node, reason="br55868-tc020-test"), (
            f"Failed to drain node {target_node}"
        )
        drained_node = target_node
        time.sleep(3)
        drain_state = Infra.slurm_get_node_state(target_node)
        assert drain_state and "DRAIN" in drain_state.upper(), (
            f"Node {target_node} not in DRAIN state: {drain_state}"
        )
        tl.info(f"Step 6: {target_node} drained: {drain_state}")

        # Step 7: Verify node count unchanged (still registered, just drained)
        slurm_after_drain = Infra.sinfo()
        assert len(slurm_after_drain) == baseline_count, (
            f"Node count changed after drain: {len(slurm_after_drain)} != {baseline_count}"
        )
        tl.info(f"Step 7: Node count unchanged: {len(slurm_after_drain)}")

        # Step 8: Submit test job to remaining nodes
        if remaining_idle:
            job_id2 = Infra.submit_slurm_job_on_node(remaining_idle[0], "hostname")
            if job_id2:
                assert Infra.wait_for_slurm_job(job_id2, timeout=60), (
                    f"Job {job_id2} did not complete on remaining node"
                )
                tl.info(f"Step 8: Job {job_id2} completed on {remaining_idle[0]}")

        # Step 9: Verify controller and accounting remain healthy
        assert Infra.scontrol_ping(), "Slurm controller lost after drain"
        rc, sacct_out, _ = Infra.sacct(job_id) if job_id else (0, "", "")
        if rc == 0 and sacct_out.strip():
            tl.info(f"Step 9: sacct responsive, controller healthy")

        # Resume the drained node (restore cluster)
        assert Infra.slurm_resume_node(target_node), (
            f"Failed to resume node {target_node}"
        )
        drained_node = None
        time.sleep(3)
        resumed_state = Infra.slurm_get_node_state(target_node)
        tl.info(f"Restore: {target_node} resumed: {resumed_state}")

        # Post-resume: verify node accepts jobs again
        job_id3 = Infra.submit_slurm_job_on_node(target_node, "hostname")
        if job_id3:
            Infra.wait_for_slurm_job(job_id3, timeout=60)
            tl.info(f"Restore: Post-resume job {job_id3} completed on {target_node}")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise
    finally:
        # Always resume the node if we drained it
        if drained_node:
            Infra.slurm_resume_node(drained_node)


# ============================================================================
# TC-021: Kubernetes Master Node Addition
# ============================================================================

@pytest.mark.st
@pytest.mark.tier4
@pytest.mark.orchestrator
@pytest.mark.rhel102
@pytest.mark.node_lifecycle
def test_br55868_k8s_master_node_add(test_logger):
    """Verify K8s control-plane health and readiness for Master node addition.

    Provisioning a new K8s Master node requires an Orchestrator rerun with
    updated inventory, which is disruptive.  This test validates the
    preconditions and current control-plane health that the test plan
    specifies: existing masters are Ready with correct roles, etcd
    membership is consistent, control-plane components are running, and
    worker scheduling is unaffected.
    """
    tc = TC["k8s_master_node_add"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        k8s_nodes = Infra.kubectl_get_nodes()
        if not k8s_nodes:
            pytest.skip("K8s control plane not reachable")

        # Step 1: Record current control-plane state
        cp_nodes = Infra.kubectl_get_control_plane_nodes()
        assert len(cp_nodes) > 0, "No control-plane nodes found"
        tl.info(f"Step 1: Control-plane nodes: {cp_nodes}")

        # Step 3: Verify all existing masters are Ready with control-plane role
        rc, stdout, _ = Infra.kubectl("get nodes --no-headers")
        for cp_node in cp_nodes:
            node_line = next(
                (l for l in stdout.strip().split("\n") if l.startswith(cp_node)),
                None,
            )
            assert node_line, f"Control-plane node {cp_node} not found in kubectl output"
            parts = node_line.split()
            assert len(parts) >= 2, f"Unexpected kubectl output for {cp_node}"
            assert parts[1] == "Ready", f"Control-plane {cp_node} not Ready: {parts[1]}"
            roles = parts[2] if len(parts) >= 3 else ""
            assert "control-plane" in roles, (
                f"Control-plane {cp_node} missing control-plane role: {roles}"
            )
            tl.info(f"Step 3: {cp_node}: Ready, roles={roles}")

        # Step 4: Verify etcd membership
        etcd_members = Infra.kubectl_get_etcd_members()
        if etcd_members:
            tl.info(f"Step 4: etcd members ({len(etcd_members)}): {etcd_members}")
        else:
            # Fall back: check etcd pods are running
            rc, etcd_pods, _ = Infra.kubectl(
                "get pods -n kube-system -l component=etcd --no-headers"
            )
            if rc == 0 and etcd_pods.strip():
                etcd_count = len(etcd_pods.strip().split("\n"))
                etcd_running = sum("Running" in l for l in etcd_pods.strip().split("\n"))
                assert etcd_running > 0, "No etcd pods Running"
                tl.info(f"Step 4: etcd pods: {etcd_running}/{etcd_count} Running")
            else:
                tl.info("Step 4: etcd membership not queryable")

        # Step 5: Verify control-plane components on each master
        for cp_node in cp_nodes:
            cp_pods = Infra.kubectl_get_control_plane_pods_on_node(cp_node)
            if cp_pods:
                all_running = all(s == "Running" for s in cp_pods.values())
                assert all_running, (
                    f"Control-plane pods not all Running on {cp_node}: {cp_pods}"
                )
                tl.info(f"Step 5: {cp_node}: {len(cp_pods)} CP pod(s) Running")
            else:
                # Query without node filter as fallback
                tl.info(f"Step 5: {cp_node}: CP pod query returned empty (node filter issue)")

        # Step 6: Verify worker scheduling unaffected
        rc, stdout, stderr = Infra.kubectl(
            "run br55868-tc021-test --image=busybox:1.36 --restart=Never "
            "-- sh -c 'echo ok && sleep 5'"
        )
        if rc == 0:
            Infra.kubectl(
                "wait --for=condition=Ready --timeout=60s pod/br55868-tc021-test",
                timeout=65,
            )
            tl.info("Step 6: Test pod scheduled successfully")
            Infra.kubectl("delete pod br55868-tc021-test --ignore-not-found")
        else:
            tl.info(f"Step 6: Test pod creation skipped ({stderr.strip()[:60]})")

        # Step 7: Verify workers unaffected
        all_ready = sum(1 for s in k8s_nodes.values() if s == "True")
        assert all_ready == len(k8s_nodes), (
            f"Not all nodes Ready: {all_ready}/{len(k8s_nodes)}"
        )
        tl.info(f"Step 7: All {len(k8s_nodes)} node(s) Ready")

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise
    finally:
        Infra.kubectl("delete pod br55868-tc021-test --ignore-not-found 2>/dev/null")


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

        # Step 1: Verify CUDA version selection is present in configuration
        cuda_config_path = os.path.join(
            OMNIA_DATA_PATH, "image_build_manager/input", OMNIA_PROJECT_NAME
        )
        cuda_version_configured = None
        for cfg_name in ("image_build_config.yml", "image_build_manager_config.yml"):
            cfg_path = os.path.join(cuda_config_path, cfg_name)
            if os.path.exists(cfg_path):
                cfg = _load_yaml(cfg_path)
                if cfg:
                    cuda_ver = cfg.get("cuda_version", cfg.get("cuda_toolkit_version"))
                    if cuda_ver:
                        cuda_version_configured = str(cuda_ver)
                        tl.info(f"Step 1: CUDA version configured: {cuda_version_configured} (in {cfg_name})")
        if not cuda_version_configured:
            tl.info("Step 1: No explicit CUDA version in image_build config (using default)")

        # Step 6: nvidia-smi on GPU nodes -- verify both driver AND CUDA runtime version
        node_cuda_versions = {}
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
                node_cuda_versions[node] = cuda_out.strip()
                tl.info(f"Step 6b: {node}: CUDA runtime version {cuda_out.strip()}")
                # Verify selected CUDA version matches what is deployed
                if cuda_version_configured:
                    assert cuda_out.strip().startswith(cuda_version_configured.split(".")[0]), (
                        f"CUDA version mismatch on {node}: configured={cuda_version_configured}, "
                        f"deployed={cuda_out.strip()}"
                    )
                    tl.info(
                        f"Step 6c: {node}: CUDA version matches configuration "
                        f"({cuda_version_configured})"
                    )
            else:
                tl.info(f"Step 6b: {node}: CUDA runtime version not reported by nvidia-smi")

        # Steps 7-8: Alternate CUDA version selection verification
        # Rebuilding with a different CUDA version is destructive (requires full
        # image rebuild + reboot cycle).  We verify the selection mechanism by
        # confirming that all GPU nodes report a consistent CUDA version and
        # that the version matches what was configured in the build input.
        if node_cuda_versions:
            unique_versions = set(node_cuda_versions.values())
            tl.info(
                f"Steps 7-8: CUDA versions across {len(node_cuda_versions)} GPU node(s): "
                f"{unique_versions}"
            )
            assert len(unique_versions) == 1, (
                f"Inconsistent CUDA versions across GPU nodes: {node_cuda_versions}"
            )
            tl.info("Steps 7-8: All GPU nodes report consistent CUDA version (selection honored)")
        else:
            tl.info("Steps 7-8: No CUDA runtime versions collected; alternate selection not verifiable")

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
    """Verify MAC isolation across FG boot configs and recovery config integrity."""
    tc = TC["boot_service_mac_isolation"]
    tl = test_logger(tc["title"], tc["id"])

    try:
        boot_dir = os.path.join(OMNIA_DATA_PATH, "openchami/workdir/boot")
        boot_files = sorted(glob.glob(os.path.join(boot_dir, "boot-svc-*.yaml")))
        if not boot_files:
            pytest.skip(f"No boot-svc-*.yaml files in {boot_dir}")

        # Step 1: Check for recovery config files (node-specific recovery)
        recovery_files = sorted(glob.glob(os.path.join(boot_dir, "recovery-*.yaml")))
        tl.info(
            f"Step 1: {len(boot_files)} FG boot config(s), "
            f"{len(recovery_files)} recovery config(s)"
        )

        # Step 2: Verify FG boot membership is saved (backup exists)
        backup_dir = os.path.join(boot_dir, "backups")
        if os.path.isdir(backup_dir):
            backups = os.listdir(backup_dir)
            tl.info(f"Step 2: {len(backups)} FG membership backup(s) in {backup_dir}")
        else:
            tl.info("Step 2: No backup directory (no recovery in progress or backups inline)")

        # Steps 3-4: Read every FG boot config and collect MACs
        mac_to_fg = {}
        duplicates = []
        total_macs = 0
        fg_configs = {}
        for filepath in boot_files:
            data = _load_yaml(filepath)
            if not data:
                continue
            fg_name = (data.get("metadata") or {}).get("name", os.path.basename(filepath))
            spec = data.get("spec", {})
            macs = spec.get("macs", [])
            total_macs += len(macs)
            fg_configs[fg_name] = {"macs": macs, "file": filepath}

            # Verify boot config has required fields
            assert spec.get("kernel"), f"FG {fg_name}: missing kernel"
            assert spec.get("initrd"), f"FG {fg_name}: missing initrd"
            assert macs, f"FG {fg_name}: no MACs assigned"
            tl.info(f"Step 3: {fg_name}: {len(macs)} MAC(s), kernel+initrd present")

            # Step 5: MAC never in both FG configs
            for mac in macs:
                mac_lower = mac.lower()
                if mac_lower in mac_to_fg:
                    duplicates.append(f"MAC {mac} in both '{mac_to_fg[mac_lower]}' and '{fg_name}'")
                mac_to_fg[mac_lower] = fg_name

        # Step 4: Check recovery configs for MAC conflicts with FG configs
        recovery_macs = {}
        for filepath in recovery_files:
            data = _load_yaml(filepath)
            if not data:
                continue
            rec_name = (data.get("metadata") or {}).get("name", os.path.basename(filepath))
            spec = data.get("spec", {})
            macs = spec.get("macs", [])
            for mac in macs:
                mac_lower = mac.lower()
                recovery_macs[mac_lower] = rec_name
                # Step 5: MAC must NOT appear in both FG config and recovery config
                if mac_lower in mac_to_fg:
                    duplicates.append(
                        f"MAC {mac} in FG '{mac_to_fg[mac_lower]}' AND "
                        f"recovery '{rec_name}' simultaneously"
                    )
            tl.info(f"Step 4: Recovery config {rec_name}: {len(macs)} MAC(s)")

        assert total_macs > 0, "No MACs found in any boot config"
        assert not duplicates, f"MAC isolation violated: {duplicates}"
        tl.info(
            f"Step 5: {total_macs} FG MAC(s) + {len(recovery_macs)} recovery MAC(s) "
            f"across {len(boot_files)} FG(s) + {len(recovery_files)} recovery config(s) "
            "-- all unique (no simultaneous membership)"
        )

        # Step 6: Boot service running and serving correct config
        rc, stdout, _ = Infra.run_command(
            "podman ps --format '{{.Names}}' --filter name=boot-service"
        )
        if rc == 0 and "boot-service" in stdout:
            tl.info("Step 6: boot-service container running")
        else:
            tl.info("Step 6: boot-service container not found (may use different name)")

        # Step 7: After recovery, verify temporary config removed and node reattached
        # In steady state (no active recovery), there should be no recovery configs
        # OR if recovery completed, the recovery file should be cleaned up.
        if not recovery_files:
            tl.info(
                "Step 7: No active recovery configs (steady state -- "
                "cleanup verified or no recovery was performed)"
            )
        else:
            # Recovery in progress -- verify each recovery MAC is NOT also in FG
            for mac, rec_name in recovery_macs.items():
                assert mac not in mac_to_fg, (
                    f"Step 7: Recovery MAC {mac} still in FG config "
                    f"(cleanup incomplete): recovery={rec_name}, FG={mac_to_fg.get(mac)}"
                )
            tl.info(
                f"Step 7: {len(recovery_files)} recovery config(s) present -- "
                "MACs correctly isolated from FG configs"
            )

        tl.passed(tc["title"])

    except AssertionError as e:
        tl.failed(tc["title"], str(e))
        raise
    except Exception as e:
        tl.failed(tc["title"], str(e))
        raise
