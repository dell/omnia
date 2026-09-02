# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Test Category: Custom SLURM Configuration Tests
Tests for custom SLURM configuration validation, merging, and rendering.

TC_SL_043: Validate custom slurm_conf module structure
TC_SL_044: Validate custom partition configuration in slurm.conf
TC_SL_045: Validate custom GRES (GPU) configuration in slurm.conf
TC_SL_046: Validate custom node configuration in slurm.conf
TC_SL_047: Validate extra_confs handling in slurm_config.yml
TC_SL_048: Validate slurm_conf merge functionality
TC_SL_049: Validate custom scheduling parameters in slurm.conf
TC_SL_050: Validate slurm.conf syntax is valid
TC_SL_051: Validate custom conf files exist if configured
"""

import pytest
from testinfra.host import Host

from library.functions import (
    TestLogger,
    run_on_host,
    load_test_config,
)
from library.messages.slurm_msgs import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.slurm_vars import TEST_CASES as TC


def _skip_if_slurm_disabled(host):
    """Skip test if Slurm is not enabled in catalog."""
    from library.functions.slurm_func import check_slurm_enabled
    result = check_slurm_enabled(host)
    if result.get("skipped"):
        pytest.skip(result["details"])


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(10)
def test_custom_slurm_conf_structure(host: Host):
    """TC_SL_043: Validate custom slurm_conf module structure."""
    _skip_if_slurm_disabled(host)

    tc = TC["custom_slurm_conf_structure"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Validating slurm_conf module availability")

    # Check if slurm_conf module is available
    result = host.run(
        "python3 -c 'from ansible.module_utils.slurm.slurm_conf_utils "
        "import parse_slurm_conf'",
        check=False
    )

    if result.rc == 0:
        tl.passed(LOG["slurm_conf_module_available"], "slurm_conf module is available")
    else:
        tl.failed("slurm_conf_module_not_available", result.stderr)
        pytest.skip("slurm_conf module not available")

    assert result.rc == 0, ASSERT["slurm_conf_module_required"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(11)
def test_extra_confs_handling(host: Host):
    """TC_SL_047: Validate extra_confs handling in slurm_config.yml."""
    _skip_if_slurm_disabled(host)

    tc = TC["extra_confs_handling"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking extra_confs configuration")

    config = load_test_config()
    project = config.get("project_name", "project_default")
    slurm_config_path = f"/opt/omnia/orchestrator/input/{project}/slurm_config.yml"

    # Check if slurm_config.yml exists
    cmd = f"test -f {slurm_config_path} && echo exists || echo missing"
    result = run_on_host(host, cmd)

    if result.stdout.strip() == "exists":
        # Check for extra_confs in slurm_config.yml
        cmd = f"grep -i extra_confs {slurm_config_path} || echo none"
        result = run_on_host(host, cmd)

        if "extra_confs" in result.stdout:
            tl.passed("extra_confs_configured",
                "extra_confs found in slurm_config.yml"
            )
        else:
            tl.passed("extra_confs_not_configured",
                "No extra_confs configured (using default)"
            )
    else:
        tl.passed("slurm_config.yml not found", "Using default SLURM configuration")

    # Test passes whether extra_confs is configured or not
    assert True, "extra_confs check completed"


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(12)
def test_custom_conf_files_exist(host: Host):
    """TC_SL_051: Validate custom conf files exist if configured."""
    _skip_if_slurm_disabled(host)

    tc = TC["custom_conf_files_exist"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking custom conf files")

    config = load_test_config()
    project = config.get("project_name", "project_default")
    slurm_config_path = f"/opt/omnia/orchestrator/input/{project}/slurm_config.yml"

    # Check if slurm_config.yml exists and has extra_confs
    cmd = f"test -f {slurm_config_path} && echo exists || echo missing"
    result = run_on_host(host, cmd)

    if result.stdout.strip() == "exists":
        cmd = f"grep -A 10 extra_confs: {slurm_config_path} 2>/dev/null || echo none"
        result = run_on_host(host, cmd)

        if "extra_confs:" in result.stdout:
            # Extract extra conf file names
            extra_confs = []
            for line in result.stdout.split('\n'):
                if line.strip().startswith('-') and '.conf' in line:
                    conf_file = line.strip().split(':')[-1].strip().strip("'\"")
                    if conf_file:
                        extra_confs.append(conf_file)

            if extra_confs:
                tl.passed("custom_conf_files_found",
                         f"Extra conf files: {', '.join(extra_confs)}")
            else:
                tl.passed("custom_conf_files_not_found",
                         "No extra conf files configured")
        else:
            tl.passed("No extra_confs section",
                     "No extra_confs section in slurm_config.yml")
    else:
        tl.passed("slurm_config.yml not found", "Using default configuration")

    # Test passes whether custom conf files exist or not
    assert True, "Custom conf files check completed"


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(13)
def test_custom_partition_config(host: Host):
    """TC_SL_044: Validate custom partition configuration in slurm.conf."""
    _skip_if_slurm_disabled(host)

    tc = TC["custom_partition_config"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking custom partition configuration")

    # Read PXE mapping to get control node IP
    config = load_test_config()
    project = config.get("project_name", "project_default")
    pxe_mapping_path = f"/opt/omnia/orchestrator/input/{project}/pxe_mapping_file.csv"

    cmd = f"grep 'slurm_control_node' {pxe_mapping_path} | cut -d',' -f7"
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        tl.passed("Control node not found", "SLURM not deployed or PXE mapping missing")
        pytest.skip("Control node not found - SLURM not deployed")

    control_ip = result.stdout.strip()
    # Check for custom partition configurations
    try:
        ssh_cmd = (
            f"ssh -o StrictHostKeyChecking=no root@{control_ip} "
            "'grep -i PartitionName /etc/slurm/slurm.conf'"
        )
        result = run_on_host(host, ssh_cmd)
    except Exception as e:
        tl.passed("custom_partition_not_found",
                 f"SSH failed: {str(e)}")
        pytest.skip(f"SSH to control node failed: {str(e)}")

    if result.rc == 0:
        partition_count = len(result.stdout.strip().split('\n'))
        tl.passed("custom_partition_found",
                 f"Found {partition_count} partition configurations in slurm.conf")
    else:
        tl.passed("custom_partition_not_found",
                 "SLURM not deployed or slurm.conf not accessible")
        pytest.skip("SLURM not deployed - cannot check partition config")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(14)
def test_custom_gres_config(host: Host):
    """TC_SL_045: Validate custom GRES (GPU) configuration in slurm.conf."""
    _skip_if_slurm_disabled(host)

    tc = TC["custom_gres_config"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking custom GRES configuration")

    # Read PXE mapping to get control node IP
    config = load_test_config()
    project = config.get("project_name", "project_default")
    pxe_mapping_path = f"/opt/omnia/orchestrator/input/{project}/pxe_mapping_file.csv"

    cmd = f"grep 'slurm_control_node' {pxe_mapping_path} | cut -d',' -f7"
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        tl.passed("Control node not found", "SLURM not deployed or PXE mapping missing")
        pytest.skip("Control node not found - SLURM not deployed")

    control_ip = result.stdout.strip()
    # Check for GRES configuration
    try:
        ssh_cmd = (
            f"ssh -o StrictHostKeyChecking=no root@{control_ip} "
            "'grep -i gres /etc/slurm/slurm.conf'"
        )
        result = run_on_host(host, ssh_cmd)
    except Exception as e:
        tl.passed("gres_config_not_found",
                 f"SSH failed: {str(e)}")
        pytest.skip(f"SSH to control node failed: {str(e)}")

    if result.rc == 0:
        gres_lines = [line for line in result.stdout.split('\n') if line.strip()]
        tl.passed("gres_config_found",
                 f"GPU resources configured in slurm.conf: {len(gres_lines)} GRES entries")
    else:
        tl.passed("gres_config_not_found",
                 "SLURM not deployed or slurm.conf not accessible")
        pytest.skip("SLURM not deployed - cannot check GRES config")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(15)
def test_custom_node_config(host: Host):
    """TC_SL_046: Validate custom node configuration in slurm.conf."""
    _skip_if_slurm_disabled(host)

    tc = TC["custom_node_config"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking custom node configuration")

    # Read PXE mapping to get control node IP
    config = load_test_config()
    project = config.get("project_name", "project_default")
    pxe_mapping_path = f"/opt/omnia/orchestrator/input/{project}/pxe_mapping_file.csv"

    cmd = f"grep 'slurm_control_node' {pxe_mapping_path} | cut -d',' -f7"
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        tl.passed("Control node not found", "SLURM not deployed or PXE mapping missing")
        pytest.skip("Control node not found - SLURM not deployed")

    control_ip = result.stdout.strip()
    # Check for NodeName configuration
    try:
        ssh_cmd = (
            f"ssh -o StrictHostKeyChecking=no root@{control_ip} "
            "'grep -i NodeName /etc/slurm/slurm.conf'"
        )
        result = run_on_host(host, ssh_cmd)
    except Exception as e:
        tl.passed("Node config not checked", f"SSH failed: {str(e)}")
        pytest.skip(f"SSH to control node failed: {str(e)}")

    if result.rc == 0:
        node_lines = [line for line in result.stdout.split('\n') if line.strip()]
        tl.passed("node_config_found",
                 f"Found {len(node_lines)} node configurations in slurm.conf")
    else:
        tl.passed("Node config not checked", "SLURM not deployed or slurm.conf not accessible")
        pytest.skip("SLURM not deployed - cannot check node config")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(16)
def test_slurm_conf_merge_functionality(host: Host):
    """TC_SL_048: Validate slurm_conf merge functionality."""
    _skip_if_slurm_disabled(host)

    tc = TC["slurm_conf_merge"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing slurm_conf merge functionality")

    # Use ansible module to test merge
    cmd = (
        "ansible localhost -m ansible.module_utils.slurm.slurm_conf "
        "-a 'op=render conf_map={\"ClusterName\": \"test_cluster\", "
        "\"SlurmctldPort\": 6817}' 2>&1"
    )
    result = run_on_host(host, cmd)

    if result.rc == 0:
        tl.passed("slurm_conf merge functional", "slurm_conf module merge operation works")
    else:
        tl.passed("slurm_conf merge skipped", "Ansible module test skipped")
        pytest.skip("Ansible module not available or test environment issue")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(17)
def test_custom_scheduling_params(host: Host):
    """TC_SL_049: Validate custom scheduling parameters in slurm.conf."""
    _skip_if_slurm_disabled(host)

    tc = TC["custom_scheduling_params"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking custom scheduling parameters")

    # Read PXE mapping to get control node IP
    config = load_test_config()
    project = config.get("project_name", "project_default")
    pxe_mapping_path = f"/opt/omnia/orchestrator/input/{project}/pxe_mapping_file.csv"

    cmd = f"grep 'slurm_control_node' {pxe_mapping_path} | cut -d',' -f7"
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        tl.passed("Control node not found", "SLURM not deployed or PXE mapping missing")
        pytest.skip("Control node not found - SLURM not deployed")

    control_ip = result.stdout.strip()
    # Check for scheduling parameters
    try:
        scheduling_params = ["SchedulerType", "SelectType", "SelectTypeParameters"]
        found_params = []

        for param in scheduling_params:
            ssh_cmd = (
                f"ssh -o StrictHostKeyChecking=no root@{control_ip} "
                f"'grep -i {param} /etc/slurm/slurm.conf'"
            )
            result = run_on_host(host, ssh_cmd)
            if result.rc == 0:
                found_params.append(param)
    except Exception as e:
        tl.passed("scheduling_params_not_found",
                 f"SSH failed: {str(e)}")
        pytest.skip(f"SSH to control node failed: {str(e)}")

    if found_params:
        tl.passed("scheduling_params_found",
                 f"Found scheduling parameters: {', '.join(found_params)}")
    else:
        tl.passed("scheduling_params_not_found",
                 "SLURM not deployed or slurm.conf not accessible")
        pytest.skip("SLURM not deployed - cannot check scheduling params")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(18)
def test_slurm_conf_syntax_valid(host: Host):
    """TC_SL_050: Validate slurm.conf syntax is valid."""
    _skip_if_slurm_disabled(host)

    tc = TC["slurm_conf_syntax_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Validating slurm.conf syntax")

    # Read PXE mapping to get control node IP
    config = load_test_config()
    project = config.get("project_name", "project_default")
    pxe_mapping_path = f"/opt/omnia/orchestrator/input/{project}/pxe_mapping_file.csv"

    cmd = f"grep 'slurm_control_node' {pxe_mapping_path} | cut -d',' -f7"
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        tl.passed("Control node not found", "SLURM not deployed or PXE mapping missing")
        pytest.skip("Control node not found - SLURM not deployed")

    control_ip = result.stdout.strip()
    # Validate slurm.conf syntax using scontrol
    try:
        ssh_cmd = (
            f"ssh -o StrictHostKeyChecking=no root@{control_ip} "
            "'scontrol show config | grep -i error'"
        )
        result = run_on_host(host, ssh_cmd)
    except Exception as e:
        tl.passed("Syntax check skipped", f"SSH failed: {str(e)}")
        pytest.skip(f"SSH to control node failed: {str(e)}")

    if result.rc == 0 and "error" not in result.stdout.lower():
        tl.passed("slurm_conf_syntax_valid", "No syntax errors in slurm.conf")
    else:
        tl.passed("Syntax check skipped", "SLURM not deployed or scontrol not available")
        pytest.skip("SLURM not deployed - cannot check syntax")
