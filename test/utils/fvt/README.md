# Utils Domain — FVT Test Case Registry

Complete registry of all Functional Verification Tests for the utils domain.

## Test Scenarios

| Scenario | Directory | Description |
|----------|-----------|-------------|
| precheck | `fvt/precheck/` | Environment and connectivity checks |
| collect | `fvt/collect/` | Log collector tests |
| set_pxe_boot | `fvt/set_pxe_boot/` | PXE boot tests |
| install_os | `fvt/install_os/` | OS installation tests |

## Test Case Index

### Precheck Scenario

| TC ID | Test Function | File | Markers |
|-------|---------------|------|---------|
| TC_PC_001 | test_target_connectivity | connectivity/test_connectivity.py | sanity |
| TC_PC_002 | test_env_vars_present | connectivity/test_connectivity.py | sanity |
| TC_PC_003 | test_hostname_domain | connectivity/test_connectivity.py | sanity |
| TC_PC_004 | test_admin_ip_assigned | connectivity/test_connectivity.py | sanity |
| TC_PC_005 | test_omnia_setup | connectivity/test_connectivity.py | sanity |

### Collect Scenario

#### Deploy Tests

| TC ID | Test Function | File | Markers |
|-------|---------------|------|---------|
| TC_CL_001 | test_deploy_collect_setup | test_playbook.py | deploy, sanity, collect |
| TC_CL_002 | test_deploy_collect_prepare | test_playbook.py | deploy, sanity, collect |
| TC_CL_003 | test_deploy_collect_bundle | test_playbook.py | deploy, sanity, collect |
| TC_CL_004 | test_deploy_collect_full | test_playbook.py | deploy, functional, collect |

#### Verification Tests

| TC ID | Test Function | File | Markers |
|-------|---------------|------|---------|
| TC_CL_010 | test_collect_input_file_exists | log_collector/test_log_collector.py | sanity, collect |
| TC_CL_011 | test_collect_input_file_valid | log_collector/test_log_collector.py | sanity, collect |
| TC_CL_012 | test_collect_functional_groups_valid | log_collector/test_log_collector.py | sanity, collect |
| TC_CL_020 | test_collect_output_dir_exists | log_collector/test_log_collector.py | sanity, collect |
| TC_CL_021 | test_collect_bundle_created | log_collector/test_log_collector.py | functional, collect |
| TC_CL_022 | test_collect_metadata_exists | log_collector/test_log_collector.py | functional, collect |
| TC_CL_023 | test_collect_metadata_valid | log_collector/test_log_collector.py | functional, collect |
| TC_CL_024 | test_collect_metadata_sha256 | log_collector/test_log_collector.py | functional, collect |
| TC_CL_025 | test_collect_bundle_contents | log_collector/test_log_collector.py | functional, collect |
| TC_CL_030 | test_collect_env_vars_loaded | log_collector/test_log_collector.py | sanity, collect |
| TC_CL_031 | test_collect_project_name_loaded | log_collector/test_log_collector.py | sanity, collect |

### Set PXE Boot Scenario

#### Deploy Tests

| TC ID | Test Function | File | Markers |
|-------|---------------|------|---------|
| TC_PX_001 | test_deploy_pxe_credentials | test_playbook.py | deploy, sanity, pxe |
| TC_PX_002 | test_deploy_pxe_boot | test_playbook.py | deploy, functional, pxe |
| TC_PX_003 | test_deploy_pxe_full | test_playbook.py | deploy, functional, pxe |

#### Verification Tests

| TC ID | Test Function | File | Markers |
|-------|---------------|------|---------|
| TC_PX_010 | test_pxe_config_file_exists | pxe/test_pxe_boot.py | sanity, pxe |
| TC_PX_011 | test_pxe_config_valid | pxe/test_pxe_boot.py | sanity, pxe |
| TC_PX_012 | test_pxe_inventory_file_exists | pxe/test_pxe_boot.py | sanity, pxe |
| TC_PX_013 | test_pxe_inventory_valid | pxe/test_pxe_boot.py | sanity, pxe |
| TC_PX_014 | test_pxe_credentials_file_exists | pxe/test_pxe_boot.py | sanity, pxe |
| TC_PX_020 | test_pxe_output_dir_exists | pxe/test_pxe_boot.py | functional, pxe |
| TC_PX_021 | test_pxe_failed_nodes_file | pxe/test_pxe_boot.py | functional, pxe |
| TC_PX_022 | test_pxe_failed_nodes_valid | pxe/test_pxe_boot.py | functional, pxe |
| TC_PX_030 | test_pxe_phone_home_enabled | pxe/test_pxe_boot.py | sanity, pxe |
| TC_PX_031 | test_pxe_phone_home_config | pxe/test_pxe_boot.py | sanity, pxe |

### Install OS Scenario

#### Deploy Tests

| TC ID | Test Function | File | Markers |
|-------|---------------|------|---------|
| TC_IO_001 | test_deploy_install_os_credentials | test_playbook.py | deploy, sanity |
| TC_IO_002 | test_deploy_install_os_build_iso | test_playbook.py | deploy, functional |
| TC_IO_003 | test_deploy_install_os_deploy | test_playbook.py | deploy, functional |
| TC_IO_004 | test_deploy_install_os_generate_ks | test_playbook.py | deploy, functional |
| TC_IO_005 | test_deploy_install_os_full | test_playbook.py | deploy, functional |

#### Verification Tests

| TC ID | Test Function | File | Markers |
|-------|---------------|------|---------|
| TC_IO_010 | test_install_os_config_file_exists | iso/test_iso.py | sanity |
| TC_IO_011 | test_install_os_config_valid | iso/test_iso.py | sanity |
| TC_IO_012 | test_install_os_credentials_file_exists | iso/test_iso.py | sanity |
| TC_IO_020 | test_install_os_output_dir_exists | iso/test_iso.py | functional |
| TC_IO_021 | test_install_os_status_file_exists | iso/test_iso.py | functional |
| TC_IO_022 | test_install_os_status_valid | iso/test_iso.py | functional |
| TC_IO_030 | test_install_os_custom_iso_created | iso/test_iso.py | functional |
| TC_IO_031 | test_install_os_kickstart_generated | iso/test_iso.py | functional |

## Markers

| Marker | Description |
|--------|-------------|
| `sanity` | Baseline verification tests (must-pass) |
| `functional` | Extended functional verification |
| `deploy` | Playbook deployment tests |
| `collect` | Log collector tests |
| `pxe` | PXE boot tests |
| `install_os` | OS installation tests |

## Running Tests

```bash
# Run all tests in a scenario
./run_validation.sh collect test

# Run only sanity tests
./run_validation.sh collect test --marker sanity

# Run only deploy tests
./run_validation.sh collect deploy

# Run specific suite
./run_validation.sh collect test --suite log_collector
```
