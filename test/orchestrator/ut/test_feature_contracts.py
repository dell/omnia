# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Source contracts for additional cloud-init and HPC features."""

import json

import pytest
import yaml

from ut.source_loader import ORCHESTRATOR_ROOT


pytestmark = pytest.mark.unit
CONFIGURE_ROLE = ORCHESTRATOR_ROOT / "roles" / "configure_ochami"
SLURM_ROLE = ORCHESTRATOR_ROOT / "roles" / "slurm_config"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_additional_cloud_init_key_flows_from_schema_to_role():
    """ORCH_UT_013: One public key enables additional cloud-init end to end."""
    public_key = "additional_cloud_init_config_file"
    schema = json.loads(
        _read(
            ORCHESTRATOR_ROOT
            / "plugins/module_utils/orchestrator_validation/schema/orchestrator_config.json"
        )
    )
    assert schema["properties"][public_key]["type"] == "string"
    assert f"['{public_key}']" in _read(
        CONFIGURE_ROLE / "tasks/validate_additional_metadata_svc.yml"
    )


def test_additional_cloud_init_example_uses_only_supported_stages():
    """ORCH_UT_014: Shipped cloud-init input cannot override platform stages."""
    example = yaml.safe_load(
        _read(ORCHESTRATOR_ROOT / "input/additional_cloud_init.yml")
    )
    assert set(example) == {"common", "groups"}
    assert set(example["common"]) <= {"write_files", "runcmd"}
    for section in example["groups"].values():
        assert set(section) <= {"write_files", "runcmd"}


def test_additional_cloud_init_template_preserves_platform_precedence():
    """ORCH_UT_015: User lists append while platform dictionaries win."""
    template = _read(
        CONFIGURE_ROLE
        / "templates/metadata_svc/ms-group-additional_metadata_svc.yaml.j2"
    )
    assert "settings: [append]" in template
    assert "settings: [no_replace, recurse_list]" in template
    assert "bootcmd" not in template
    assert "packages:" not in template
    assert "network:" not in template


def test_additional_cloud_init_group_names_are_namespaced():
    """ORCH_UT_016: User metadata groups cannot collide with platform groups."""
    variables = yaml.safe_load(_read(CONFIGURE_ROLE / "vars/main.yml"))
    assert variables["additional_metadata_svc_common_group_name"] == (
        "additional_metadata_svc"
    )
    assert variables["additional_metadata_svc_fg_group_prefix"] == (
        "additional_metadata_svc_"
    )


def test_hpc_assets_are_deployed_with_safe_modes():
    """ORCH_UT_017: HPC scripts are executable and lists are read-only data."""
    tasks = _read(SLURM_ROLE / "tasks/hpc_tools.yml")
    for asset in ("download_container_image.sh", "pull_benchmarks.sh"):
        assert asset in tasks
    for asset in ("container_image.list", "benchmark_tools.list"):
        assert asset in tasks
    assert tasks.count('mode: "0755"') >= 2
    assert tasks.count('mode: "0644"') >= 2


def test_hpc_benchmark_allowlist_is_complete():
    """ORCH_UT_018: Required benchmark families stay in the staging list."""
    configured = {
        line.strip()
        for line in _read(SLURM_ROLE / "templates/benchmark_tools.list.j2").splitlines()
        if line.strip() and not line.startswith("#")
    }
    expected = {
        "osu-micro-benchmarks",
        "imb",
        "likwid",
        "papi",
        "geopm",
        "sionlib",
        "msr-safe",
    }
    assert configured == expected


def test_benchmark_downloader_is_offline_and_architecture_aware():
    """ORCH_UT_019: Benchmarks use Pulp only and handle x86/Arm differences."""
    script = _read(SLURM_ROLE / "templates/pull_benchmarks.sh.j2")
    assert "PULP_CONTENT_BASE" in script
    assert "uname -m" in script
    assert '"x86_64"' in script and '"aarch64"' in script
    assert '"msr-safe"' in script
    assert "PULP_CONTENT_BASE=\"https://${PULP_SERVER}/pulp/content/" in script
    assert "FAILED_COUNT" in script and "exit ${EXIT_CODE:-0}" in script


def test_apptainer_downloader_is_bounded_and_pulp_only():
    """ORCH_UT_020: SIF downloads use the mirror and a finite timeout."""
    script = _read(SLURM_ROLE / "templates/download_container_image.sh.j2")
    assert "command -v apptainer" in script
    assert "PULP_SERVER" in script
    assert "timeout 1800 apptainer pull" in script
    assert "--disable-cache" in script
    assert 'PULP_IMAGE="docker://${PULP_SERVER}/' in script


@pytest.mark.parametrize(
    "template_name",
    [
        "ms-group-login_node_x86_64.yaml.j2",
        "ms-group-login_node_aarch64.yaml.j2",
        "ms-group-login_compiler_node_x86_64.yaml.j2",
        "ms-group-login_compiler_node_aarch64.yaml.j2",
        "ms-group-slurm_control_node_x86_64.yaml.j2",
        "ms-group-slurm_node_x86_64.yaml.j2",
        "ms-group-slurm_node_aarch64.yaml.j2",
    ],
)
def test_apptainer_mirror_reaches_every_slurm_node_type(template_name):
    """ORCH_UT_021: Every supported Slurm node type installs mirror config."""
    template = _read(
        CONFIGURE_ROLE / "templates" / "metadata_svc" / template_name
    )
    assert "apptainer_mirror.conf.j2" in template
    assert "/etc/containers/registries.conf.d/apptainer_mirror.conf" in template


@pytest.mark.parametrize(
    "architecture",
    ["x86_64", "aarch64"],
)
def test_gpu_node_templates_install_complete_cuda_stack(architecture):
    """ORCH_UT_022: GPU nodes receive driver, CUDA, GRES and DCGM tooling."""
    template = _read(
        CONFIGURE_ROLE
        / f"templates/metadata_svc/ms-group-slurm_node_{architecture}.yaml.j2"
    )
    for script in (
        "slurm_cuda_coordinator.sh",
        "install_cuda_driver.sh",
        "install_cuda_toolkit.sh",
        "install_dcgm.sh",
    ):
        assert script in template
    coordinator = _read(
        CONFIGURE_ROLE / "templates/hpc_tools/slurm_cuda_coordinator.sh.j2"
    )
    assert "lspci" in coordinator and "NVIDIA" in coordinator


def test_slurm_defaults_enable_gpu_gres_autodetection():
    """ORCH_UT_023: Slurm defaults expose GPU GRES through NVML."""
    defaults = _read(SLURM_ROLE / "defaults/main.yml")
    assert "GresTypes: gpu" in defaults
    assert "AutoDetect: nvml" in defaults


def test_dcgm_flag_is_boolean_and_defaults_enabled():
    """ORCH_UT_024: DCGM feature configuration has a stable boolean contract."""
    schema = json.loads(
        _read(
            ORCHESTRATOR_ROOT
            / "plugins/module_utils/orchestrator_validation/schema/orchestrator_config.json"
        )
    )
    dcgm = schema["properties"]["dcgm_enabled"]
    assert dcgm["type"] == "boolean"
    assert dcgm["default"] is True


def test_cleanup_protects_inputs_and_system_roots():
    """ORCH_UT_025: Cleanup cannot erase inputs or expand to a system root."""
    artifacts = _read(
        ORCHESTRATOR_ROOT / "roles/cleanup/components/artifacts/vars/component_spec.yml"
    )
    k8s = yaml.safe_load(
        _read(ORCHESTRATOR_ROOT / "roles/cleanup/components/k8s/vars/component_spec.yml")
    )
    assert "orchestrator_output_dir" in artifacts
    assert "input_project_dir" not in artifacts
    protected = set(k8s["k8s_config"]["protected_cleanup_paths"])
    assert {"/", "/root", "/opt", "/var", "/tmp"} <= protected


def test_openldap_is_catalog_driven_and_lifecycle_gated():
    """ORCH_UT_026: Catalog state consistently gates every OpenLDAP phase."""
    setup = _read(ORCHESTRATOR_ROOT / "roles/orchestrator_setup/tasks/main.yml")
    assert "openldap_support:" in setup
    assert "_catalog_group_names | select('match', '.*openldap.*')" in setup
    for relative_path in (
        "playbooks/precheck/precheck_openldap.yml",
        "playbooks/prepare/prepare_openldap.yml",
        "roles/deploy_openldap/tasks/main.yml",
        "playbooks/validate/validate_openldap.yml",
    ):
        assert "openldap_support" in _read(ORCHESTRATOR_ROOT / relative_path)


def test_openldap_credentials_tls_and_health_are_fail_closed():
    """ORCH_UT_027: OpenLDAP protects secrets and proves LDAP readiness."""
    deploy = _read(ORCHESTRATOR_ROOT / "roles/deploy_openldap/tasks/main.yml")
    certs = _read(
        ORCHESTRATOR_ROOT / "roles/deploy_openldap/tasks/generate_tls_certs.yml"
    )
    quadlet = _read(
        ORCHESTRATOR_ROOT / "roles/deploy_openldap/templates/omnia_auth.container.j2"
    )
    validation = _read(
        ORCHESTRATOR_ROOT
        / "roles/orchestrator_validations/tasks/validate_openldap_container.yml"
    )
    assert "decrypt_include_encrypt.yml" in deploy
    assert "no_log: true" in deploy
    assert 'mode: "0600"' in deploy
    assert '{ name: "{{ tls_key_file }}", mode: "0600" }' in certs
    assert "HealthCmd=ldapwhoami" in quadlet
    assert "PublishPort={{ ldap_port }}:389" in quadlet
    assert "PublishPort={{ ldaps_port }}:636" in quadlet
    assert "ldapwhoami" in validation and "failed_when: false" in validation
    assert "Fail if OpenLDAP does not accept LDAP requests" in validation


def test_functional_group_classification_has_ordered_custom_fallback():
    """ORCH_UT_028: Known node profiles are classified before custom fallback."""
    rules = yaml.safe_load(
        _read(ORCHESTRATOR_ROOT / "vars/functional_group_classification.yml")
    )["functional_group_categories"]
    assert list(rules) == ["kubernetes", "slurm", "login", "os_only", "custom"]
    assert rules["custom"]["patterns"] == [".*"]
    provisioning = yaml.safe_load(
        _read(ORCHESTRATOR_ROOT / "vars/functional_group_classification.yml")
    )["category_provisioning_map"]
    assert set(provisioning) == set(rules)
    assert provisioning["os_only"] == "provision_os"
    assert provisioning["custom"] == "provision_custom"


@pytest.mark.parametrize(
    ("playbook", "selector"),
    [
        ("provision_os.yml", "selectattr('name', 'match', '^os_')"),
        ("provision_custom.yml", "rejectattr('name', 'match', '^os_')"),
    ],
)
def test_os_and_custom_profiles_use_common_provisioning(playbook, selector):
    """ORCH_UT_029: OS-only and custom nodes share registration/metadata flow."""
    source = _read(ORCHESTRATOR_ROOT / "playbooks/provision" / playbook)
    assert selector in source
    assert "role: provision_common" in source
    assert "target_functional_groups | length > 0" in source


def test_storage_supports_group_node_oim_and_swap_paths():
    """ORCH_UT_030: Storage wiring covers group, node, OIM and swap use cases."""
    role = ORCHESTRATOR_ROOT / "roles/mount_config/tasks"
    main = _read(role / "main.yml")
    cloud_init = _read(role / "cloud_init.yml")
    oim = _read(role / "oim_mount.yml")
    swap = _read(role / "swap_config.yml")
    assert "cloud-init" in main and "oim-mount" in main
    assert "build_host_mount_map.yml" in cloud_init
    assert "process_single_mount.yml" in cloud_init
    assert "process_single_powervault.yml" in cloud_init
    assert "mount_on_oim" in oim and "unique(attribute='name')" in oim
    assert "Process each swap entry" in swap


def test_execute_persists_provisioning_and_aggregate_status():
    """ORCH_UT_031: Both execute and provision tags persist status artifacts."""
    validation = _read(
        ORCHESTRATOR_ROOT / "roles/validate_provisioning/tasks/main.yml"
    )
    condition = "intersect(['execute', 'provision'])"
    assert validation.count(condition) == 2
    assert "provisioning_report.yml" in validation
    assert "orchestrator_status.yml" in validation
    assert "missing_admin_interfaces" in validation


def test_upgrade_has_lock_backup_and_post_migration_verification():
    """ORCH_UT_032: Upgrades apply target versions and verify before success."""
    openchami = _read(
        ORCHESTRATOR_ROOT / "playbooks/upgrade/upgrade_openchami.yml"
    )
    openldap = _read(
        ORCHESTRATOR_ROOT / "playbooks/upgrade/upgrade_openldap.yml"
    )
    assert "upgrade_in_progress.lock" in openchami
    assert "backup" in openchami.lower()
    assert "Verify" in openchami
    assert "Update OpenLDAP Quadlet to the target image" in openldap
    assert "backup: true" in openldap
    assert "auth_target_tag in" in openldap
    assert "Fail when upgraded LDAP endpoint is not ready" in openldap


@pytest.mark.recovery
def test_upgrade_lock_blocks_normal_runs_and_is_removed_on_success():
    """ORCH_UT_033: Upgrade lock handling is fail-closed and self-clearing."""
    setup = _read(ORCHESTRATOR_ROOT / "roles/orchestrator_setup/tasks/main.yml")
    upgrade = _read(
        ORCHESTRATOR_ROOT / "playbooks/upgrade/upgrade_openchami.yml"
    )
    assert "Block playbook while upgrade is in progress" in setup
    assert "upgrade_lock.stat.exists" in setup
    assert "Remove upgrade lock file" in upgrade
    assert "state: absent" in upgrade
    assert "upgrade_in_progress.lock" in upgrade


@pytest.mark.recovery
def test_openchami_retry_resets_failure_and_recreates_networks():
    """ORCH_UT_034: OpenCHAMI retry repairs failed services and networks."""
    retry = _read(
        ORCHESTRATOR_ROOT / "roles/deploy_openchami/tasks/configs/verify.yml"
    )
    assert "Reset failed services before retry" in retry
    assert "systemctl reset-failed" in retry
    assert "Ensure OpenCHAMI Podman networks are recreated on retry" in retry
    assert "state: restarted" in retry
    assert "name: openchami.target" in retry


@pytest.mark.recovery
def test_smd_retry_refreshes_token_before_rediscovery():
    """ORCH_UT_035: SMD retry refreshes credentials before rediscovery."""
    registration = _read(
        ORCHESTRATOR_ROOT / "roles/provision_common/tasks/register_nodes.yml"
    )
    assert "Refresh access token before retry" in registration
    assert "retry_token_result.stdout" in registration
    assert "Retry SMD node discovery" in registration
    assert "retries: 2" in registration


@pytest.mark.recovery
def test_pxeboot_retry_supports_filtered_inventory_and_status_artifacts():
    """ORCH_UT_036: PXE retry can select failed nodes and persist status."""
    pxeboot = _read(ORCHESTRATOR_ROOT / "playbooks/pxeboot/pxeboot.yml")
    assert "Compute effective inventory for BuildStream retry" in pxeboot
    assert "generate_effective_csv.yml" in pxeboot
    assert "failed_nodes.json" in pxeboot
    assert "pxeboot_inventory" in pxeboot
    assert "inventory_source" in pxeboot
