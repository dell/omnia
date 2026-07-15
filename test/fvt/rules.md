<!-- Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License. -->

# Omnia Automation Framework — Development Rules

Comprehensive development rules for the omnia-artifactory automation repository.
**All developers must follow these rules strictly.**

---

## 1. Automation Design Process

### 1.1 Understand the Omnia Code First

Before writing any automation or test case, **log into the `omnia_core` container and study the actual Omnia codebase**:

```bash
podman exec -it omnia_core bash
ls /omnia/                              # Top-level playbook directories
ls /opt/omnia/input/project_default/    # Deployed input files
cat /omnia/telemetry/telemetry.yml      # Example: read the telemetry playbook
```

Every Omnia playbook starts by importing `utils/include_input_dir.yml`, which sets `input_project_dir` to `/opt/omnia/input/project_default/`. From there, each role loads its config files (e.g., `telemetry_config.yml`, `software_config.json`).

### 1.2 Playbook Analysis Requirements (MANDATORY)

**Before writing automation for any new playbook, you MUST analyze the code first.**

**Option A — If user provides a specific branch/PR:**

```bash
git clone -b <branch_or_pr_ref> https://github.com/dell/omnia.git /tmp/omnia_playbooks
```

**Option B — If no branch is specified, analyze directly from the running container:**

```bash
podman exec -it omnia_core bash
cat /omnia/<playbook_dir>/<playbook>.yml   # Read the main playbook
ls /omnia/<playbook_dir>/roles/            # List all roles
```

**Analysis checklist:**

1. Read the main playbook YAML file
2. Identify all roles being called
3. Note which hosts the playbook targets
4. Understand configuration files it reads/writes
5. Identify what resources it creates (containers, files, pods, services)
6. Map each resource to a verification test

### 1.3 Backtrack from the Feature

When automating a new feature:

1. **Identify the playbook** — Find which playbook under `/omnia/` implements the feature.
2. **Trace the input files** — Check which files from `input_project_dir` the playbook roles load (look for `include_vars` tasks).
3. **Understand the deployment** — Read the roles to understand what containers, services, K8s resources, or files the playbook creates.
4. **Write tests that verify the deployment** — Based on what the playbook actually does, write test cases that check the end state (containers running, services healthy, configs correct, etc.).
5. **Update the dataset** — If the feature needs new input values, add them to the appropriate file in `datasets/project_default/`.

Never write tests based on assumptions. Always verify against the actual Omnia code inside the container.

### 1.4 Input File Flow

```
datasets/project_default/          (automation repo — your input files)
        │
        │  rsync via deploy step (when sync_dataset_to_core: true)
        ▼
/opt/omnia/input/project_default/  (inside omnia_core container)
        │
        │  include_input_dir.yml → sets input_project_dir
        ▼
Omnia playbook roles               (load config via include_vars)
```

---

## 2. Module Architecture Rules

### 2.1 Module Structure (MANDATORY)

Every new module MUST follow this exact directory structure:

```
automation_library/<module_name>/
├── __init__.py           # Module exports — import and re-export specific items
├── functions/
│   ├── __init__.py       # Function exports — re-export from sub-files
│   ├── common_func.py    # Common utilities, node retrieval, SSH helpers
│   ├── <component>_func.py  # Component-specific verification functions
│   └── ...
├── vars/
│   ├── __init__.py       # Variable exports — re-export from sub-files
│   ├── common_vars.py    # Shared constants (container name, SSH opts, paths)
│   └── <component>_vars.py  # Component-specific constants (service lists, etc.)
└── messages/
    ├── __init__.py       # Message exports — re-export from sub-files
    └── <module>_msgs.py  # Test names, log messages, assertion messages
```

**Reference:** See `automation_library/provision/` for the canonical implementation.

### 2.2 Strict Separation Rules

- **Messages MUST be in the `messages/` directory** — Never define test names, log messages, or assertion messages inline in test files or function files.
- **Variables/Constants MUST be in the `vars/` directory** — Never hardcode service lists, paths, retry counts, or container names in function or test files.
- **Functions MUST be in the `functions/` directory** — Never define verification logic in test files. Test files should only call functions and handle output/assertions.

### 2.3 Module `__init__.py` Requirements

Each module's `__init__.py` MUST:
1. Include Apache 2.0 license header (current year)
2. Provide a docstring explaining the module's purpose
3. Import and export specific items (avoid `import *`)
4. Group imports logically: functions first, then vars, then messages

**Reference:** `automation_library/provision/__init__.py`

```python
"""
Provision Module

This module provides functions for provision playbook verification.
Uses core module utilities for SSH, PXE mapping, and config reading.

Test Categories:
- Common: Node boot, passwordless SSH, hostname sync
- Slurm: Services, cross-node SSH, sinfo, OpenMPI/UCX
- K8s: Node ready status
- Minimal OS: Functional group validation, package verification
"""

from .functions import (
    get_all_slurm_nodes,
    get_k8s_nodes,
    verify_services_on_nodes,
    verify_cross_node_ssh,
    # ... specific function imports
)
from .vars import (
    SLURM_CONTROL_SERVICES,
    SLURM_NODE_SERVICES,
    PROVISION_REACHABILITY_RETRY,
    # ... specific variable imports
)
from .messages import (
    TEST_NAMES,
    TEST_LOG_MSGS,
    TEST_ASSERT_MSGS,
)
```

---

## 3. Core Module Usage Rules (CRITICAL — CHECK FIRST)

### 3.1 First Check: Does It Already Exist in Core?

**Before writing ANY new function, ALWAYS check if it already exists in `automation_library.core`.**

The core module provides reusable utilities used across all modules. **Never duplicate core functions.**

### 3.2 Core Function Catalog — Host & Connection (`host_func.py`)

| Function | Description |
|----------|-------------|
| `get_testinfra_host()` | Returns a testinfra `Host` object. Local mode if `oim_server_ip` is empty/localhost, otherwise SSH. |
| `load_omnia_test_config()` | Loads and returns the `omnia_test_config.yml` dict (non-sensitive settings). |
| `load_omnia_test_credentials()` | Loads and returns the `omnia_test_credentials.yml` dict (sensitive passwords). Auto-decrypts if vault-encrypted. |
| `get_dataset_path()` | Returns the local dataset directory path. |
| `is_local_execution()` | Returns `True` if running in local mode. |
| `run_on_oim(host, cmd)` | Runs a shell command on the OIM host. Returns `CompletedProcess`. |
| `run_in_container(host, cmd, container, workdir)` | Runs a command inside a Podman container. Default container: `omnia_core`. |
| `run_on_remote_node(host, target_ip, cmd, user, password, port)` | Runs a command on a remote cluster node via SSH from the OIM. |
| `get_node_info(host, identifier, by)` | Looks up a single node from `pxe_mapping_file.csv` by hostname, IP, service tag, or MAC. |
| `get_nodes_info(host, functional_group)` | Gets all nodes matching a functional group from `pxe_mapping_file.csv`. |
| `get_node_admin_ip(host, identifier)` | Shortcut: get admin IP of a node by identifier. |
| `get_functional_groups_from_pxe_mapping(host)` | Returns `set` of all functional groups in the PXE mapping. |
| `get_group_names_from_pxe_mapping(host)` | Returns `set` of group names (functional group minus arch suffix). |
| `check_container_running(host, container_name)` | Returns dict with `running` bool and container info. |
| `make_verification_result(name, passed, message, details)` | Helper to create a standardized verification result dict. |
| `get_project_root()` | Returns the absolute path to the project root directory. |

### 3.3 Core Function Catalog — Input Loader (`load_inputs_func.py`)

| Function | Description |
|----------|-------------|
| `load_container_file(host, filepath)` | Reads and parses a YAML/JSON file from inside the container. Caches results. |
| `load_input_file(host, filename)` | Loads a file from `/opt/omnia/input/project_default/<filename>`. Caches results. |
| `get_input_value(host, filename, key, default)` | Get a specific value using dot-notation key (e.g., `admin_network.nic_name`). |
| `get_input_bool(host, filename, key, default)` | Same as `get_input_value` but coerces to `bool`. |
| `clear_input_cache()` | Clears the input file cache. Call when files may have changed. |
| `is_software_enabled(host, software_name)` | Checks if a software name exists in `software_config.json` softwares list. |
| `get_config_list_item(host, filename, list_key, match_key, match_value)` | Find an item in a list inside a config file by matching a field value. |
| `get_nfs_client_mount_path(host, nfs_name)` | Get the NFS client mount path from `storage_config.yml`. |

### 3.4 Core Function Catalog — Secrets (`secrets_func.py`)

| Function | Description |
|----------|-------------|
| `view_credentials_file(host, file_path, key_file_path)` | Decrypts an ansible-vault file and returns the parsed dict. |
| `get_credential_value(host, file_path, key_file_path, key)` | Decrypts and extracts a single credential value. |
| `get_multiple_credentials(host, file_path, key_file_path, keys)` | Decrypts and extracts multiple credential values. |

### 3.5 Core Function Catalog — Database (`db_exec_func.py`)

| Function | Description |
|----------|-------------|
| `exec_psql_query(host, query, db, container)` | Executes a SQL query in a Postgres container and returns rows as list of dicts. |
| `query_db_row(host, table, conditions, db, container)` | Query a single row from a Postgres table with conditions dict. |

### 3.6 Core Function Catalog — Node Connectivity (`node_checks_func.py`)

| Function | Description |
|----------|-------------|
| `check_node_connectivity_once(host, admin_ip, hostname)` | Single ping + SSH check on a node. |
| `check_node_connectivity_with_retry(host, admin_ip, hostname, ping_retries, ssh_retries)` | Ping + SSH with configurable retries. |
| `verify_nodes_connectivity(host, nodes, use_cache)` | Full connectivity check for a list of nodes with retry. |
| `check_nodes_reachability(host, nodes, retry_limit, retry_interval)` | Quick reachability check returning `reachable` and `unreachable` lists. |
| `get_reachable_nodes(nodes)` | Filter to reachable nodes from cache. |
| `get_unreachable_nodes(nodes)` | Filter to unreachable nodes from cache. |
| `is_node_reachable(admin_ip)` | Check if a specific node is reachable (from cache). |
| `get_node_error(admin_ip)` | Get the error message for an unreachable node. |
| `clear_connectivity_cache()` | Clear the connectivity result cache. |
| `print_unreachable_nodes(unreachable)` | Log unreachable nodes with details. |
| `get_cloudinit_status(host, target_ip)` | Get cloud-init status on a provisioned node. |
| `wait_for_cloudinit(host, target_ip, timeout, interval)` | Wait for cloud-init to complete on a node. |
| `verify_cloudinit_status(host, nodes)` | Verify cloud-init status on a list of nodes. |

### 3.7 Core Function Catalog — Build Stream (`build_stream_func.py`)

| Function | Description |
|----------|-------------|
| `is_build_stream_enabled(host)` | Check if BuildStream CI/CD is enabled in config. |
| `get_build_stream_job_id(host, stage_name)` | Resolve the BuildStream job ID — from config or latest COMPLETED job in DB. |
| `check_build_stream_stage(host, job_id, stage_name, expected_state)` | Validate a specific pipeline stage matches expected state. |

Stage constants: `STAGE_BUILD_IMAGE_X86_64`, `STAGE_BUILD_IMAGE_AARCH64`, `STAGE_CREATE_LOCAL_REPO`, `STAGE_VALIDATE_IMAGE`, `STAGE_PARSE_CATALOG`, `STAGE_GENERATE_INPUT`

### 3.8 Core Function Catalog — Formatting (`formatting_func.py`)

| Item | Description |
|------|-------------|
| `Colors` | Terminal color codes (RED, GREEN, YELLOW, BLUE, CYAN, etc.) |
| `Symbols` | Unicode symbols (CHECK, CROSS, WARN, INFO, ARROW, BULLET, etc.) |
| `log(message, level)` | Print a formatted log message with color and symbol. |
| `set_debug_mode(enabled)` | Enable or disable debug-level output. |
| `TestLogger` | Structured test logger — `check()`, `passed()`, `failed()`, `skipped()`, `info()`, `debug()`, `section()`, `sub_check()`. |
| `get_test_output()` | Returns collected test output as a string. |

### 3.9 Core Function Catalog — Reports (`report_func.py`)

| Item | Description |
|------|-------------|
| `TestReport` | Report builder — adds server info, test results, generates HTML/JSON. |
| `get_current_report()` | Returns the active `TestReport` instance. |
| `set_current_report(report)` | Sets the active `TestReport` instance. |

The generated HTML report is scenario-centric and self-contained. In addition
to per-run donut and scenario bar charts, each server panel renders a
**Scenario Trends** panel (per-scenario pass-rate sparklines across historical
runs with up/down/flat deltas) and a **Slowest Scenarios** duration-bar chart.
KPI cards include Total, Passed, Failed, Skipped, Pass Rate, Runs, and Duration.
All report presentation helpers live in `report_func.py` — never inline HTML/CSS
in test files.

Server-setup module results (if any are recorded) are **excluded from test KPI
counts** and rendered as a separate graphical **Server Setup** panel with
per-check pass/fail indicators, so setup outcomes never distort the
deploy/verify totals. Note the `oim-prereq-test` prerequisite tool runs as a
standalone gate (top-level `oim_prereq_test` flag in `test_run_config.yml`),
not as a pytest scenario, and writes its own `oim_prereq_report.txt`.

### 3.10 Core Constants (`vars/`)

Key path constants (all strings):

| Constant | Value | Description |
|----------|-------|-------------|
| `OIM_SHARED_PATH` | `/opt/omnia` | OIM shared data directory |
| `INPUT_BASE_PATH` | `/opt/omnia/input/project_default` | Input file base path in container |
| `OMNIA_CORE_CONTAINER` | `omnia_core` | Container name |
| `SOFTWARE_CONFIG_PATH` | `<base>/software_config.json` | Full path to software config |
| `TELEMETRY_CONFIG_PATH` | `<base>/telemetry_config.yml` | Full path to telemetry config |
| `NETWORK_SPEC_PATH` | `<base>/network_spec.yml` | Full path to network spec |
| `PXE_MAPPING_FILE_PATH` | `<base>/pxe_mapping_file.csv` | Full path to PXE mapping |

Functional group constants: `K8S_CONTROL_PLANE_FUNCTIONAL_GROUP`, `K8S_WORKER_NODE_FUNCTIONAL_GROUP`, `SLURM_CONTROL_NODE_FUNCTIONAL_GROUP`, `SLURM_NODE_FUNCTIONAL_GROUP`, `SLURM_NODE_AARCH64_FUNCTIONAL_GROUP`, `LOGIN_NODE_FUNCTIONAL_GROUP`, `LOGIN_COMPILER_NODE_FUNCTIONAL_GROUP`, `MINIMAL_OS_X86_64_FUNCTIONAL_GROUP`, `MINIMAL_OS_AARCH64_FUNCTIONAL_GROUP`, etc.

### 3.11 Import from Core — Never Duplicate

```python
# CORRECT — Import from core (single source of truth)
from automation_library.core import (
    get_nodes_info,
    is_software_enabled,
    K8S_CONTROL_PLANE_FUNCTIONAL_GROUP,
    K8S_WORKER_NODE_FUNCTIONAL_GROUP,
    HA_CONFIG_PATH,
    SERVICE_CLUSTER_METADATA_PATH,
    PXE_MAPPING_FILE_PATH,
    TELEMETRY_CONFIG_PATH,
    INPUT_BASE_PATH,
)

# WRONG — Duplicating core constants or functions
K8S_CONTROL_PLANE_FUNCTIONAL_GROUP = "service_kube_control_plane_x86_64"
INPUT_BASE_PATH = "/opt/omnia/input/project_default"
HA_CONFIG_FILE = "/opt/omnia/input/project_default/high_availability_config.yml"
PXE_MAPPING_FILE_PATH = "/opt/omnia/input/project_default/pxe_mapping_file.csv"
```

If a module needs a core value under a local name, alias it — do not re-hardcode
the literal:

```python
# CORRECT — module keeps its own public name but sources the value from core
from automation_library.core import HA_CONFIG_PATH as _CORE_HA_CONFIG_PATH
HA_CONFIG_FILE = _CORE_HA_CONFIG_PATH
```

---

## 4. Functions Module Rules

### 4.1 File Organization

- **`common_func.py`**: Common utilities — node retrieval, SSH helpers, skip functions
- **`<component>_func.py`**: Component-specific verification functions (e.g., `slurm_func.py`, `ldap_func.py`, `k8s_func.py`)

**Reference:** `automation_library/provision/functions/` — has `common_func.py`, `slurm_func.py`, `ldap_func.py`, `provision_output_func.py`, `minimal_os_func.py`, `package_collector.py`

### 4.2 Return Dictionary Pattern (MANDATORY)

All verification functions MUST return a dictionary with consistent structure:

```python
def verify_something(host, nodes) -> Dict[str, Any]:
    """
    Verify something important.

    Args:
        host: Testinfra host object
        nodes: List of node dicts from PXE mapping

    Returns:
        Dict with success, details/error, and component-specific keys
    """
    # ... implementation

    return {
        "success": True,           # REQUIRED — bool
        "error": "",               # REQUIRED — empty string if success
        "details": "...",          # Human-readable details
        # Component-specific keys as needed:
        "results": [...],          # Per-node results
        "expected": [...],         # Expected items
        "found": [...],            # Found items
        "missing": [...],          # Missing items
    }
```

### 4.3 Skip Pattern for Optional Features

```python
def skip_if_openmpi_not_enabled(host, log: TestLogger = None):
    """Skip test if OpenMPI is not enabled in software_config.json."""
    if not is_software_enabled(host, "openmpi"):
        reason = "OpenMPI is not enabled in software_config.json"
        if log:
            log.skipped(reason, "Test skipped")
        pytest.skip(reason)
```

### 4.4 Dynamic Input Rules (CRITICAL)

**NEVER hardcode:**
- IP addresses or hostnames
- File paths that may vary by environment
- Credentials or secrets
- Port numbers (read from config)

**ALWAYS:**
- Read from `omnia_test_config.yml` via core utilities
- Read from component config files via `load_input_file()` / `get_input_value()`
- Use PXE mapping file for node information via `get_nodes_info()`
- Use `is_software_enabled()` to check software flags

```python
# WRONG — Hardcoded
admin_ip = "<HARDCODED_IP>"

# CORRECT — Dynamic from PXE mapping
from automation_library.core import get_nodes_info, K8S_CONTROL_PLANE_FUNCTIONAL_GROUP
nodes = get_nodes_info(host, K8S_CONTROL_PLANE_FUNCTIONAL_GROUP)
admin_ip = nodes[0]["admin_ip"] if nodes else None
```

### 4.5 Caching Pattern (RECOMMENDED)

For expensive operations (SSH, file reads, API calls), implement caching:

```python
_config_cache: Dict[str, Any] = {}

def clear_cache():
    """Clear all caches. Call at start of test run."""
    _config_cache.clear()

def get_config(host) -> Dict[str, Any]:
    """Get config with caching."""
    cache_key = "module_config"
    if cache_key in _config_cache:
        return _config_cache[cache_key]
    # ... read config
    _config_cache[cache_key] = config
    return config
```

---

## 5. Variables Module Rules

### 5.1 Variable Organization

```python
# common_vars.py structure

# =============================================================================
# Container and Connection Constants
# =============================================================================
CONTAINER_NAME = "omnia_core"
SSH_OPTS = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

# =============================================================================
# Retry Configuration
# =============================================================================
PROVISION_REACHABILITY_RETRY = 2
PROVISION_REACHABILITY_INTERVAL = 30

# =============================================================================
# Path Constants (inside container)
# =============================================================================
IMAGE_CONFIG_YAML_DIR = "/opt/omnia/.data/image_config_yaml_dir"
OPENCHAMI_WORKDIR = "/opt/omnia/openchami/workdir"
```

### 5.2 Service Lists (Component-Specific Vars)

```python
# slurm_vars.py — Service lists as tuples (immutable)

SLURM_CONTROL_SERVICES = ("slurmctld", "slurmdbd", "munge", "mariadb")
SLURM_NODE_SERVICES = ("slurmd", "munge")
LOGIN_NODE_SERVICES = ("slurmd", "munge")
LDMS_SAMPLER_SERVICE = "ldmsd.sampler"
```

### 5.3 Never Duplicate Core Constants

If a constant exists in `automation_library.core.vars`, import it from there:

```python
# CORRECT
from automation_library.core import OMNIA_CORE_CONTAINER, INPUT_BASE_PATH

# WRONG — duplicating core constants
CONTAINER_NAME = "omnia_core"
```

---

## 6. Messages Module Rules (MANDATORY)

### 6.1 Message Categories

Every messages file MUST define these dictionaries:

```python
from typing import Dict

# =============================================================================
# TEST NAMES — displayed in reports and TestLogger
# =============================================================================
TEST_NAMES: Dict[str, str] = {
    "build_stream_job_stage": "Verify build_stream pipeline stage '{stage}' completed successfully",
    "node_packages": "Verify all required packages installed on all nodes",
    "slurm_services": "Verify Slurm services running on all nodes",
}

# =============================================================================
# LOG MESSAGES — for TestLogger during test execution
# =============================================================================
TEST_LOG_MSGS: Dict[str, str] = {
    "packages_ok": "All required packages installed on all {count} nodes",
    "packages_fail": "{failed}/{total} nodes have missing packages",
    "services_ok": "All services running on {node_type} nodes",
}

# =============================================================================
# ASSERTION MESSAGES — shown when tests fail (include HOW TO FIX)
# =============================================================================
TEST_ASSERT_MSGS: Dict[str, str] = {
    "packages_failed": (
        "Required packages missing on nodes.\n"
        "Failed nodes: {failed_nodes}\n"
        "{details}\n\n"
        "HOW TO FIX:\n"
        "  1. Check functional_groups_config.yml\n"
        "  2. Verify package installation on node: ssh root@<node> rpm -qa | grep <pkg>\n"
        "  3. Re-run provision playbook to reinstall packages\n"
        "  4. Check package availability in local_repo"
    ),
}

# =============================================================================
# SKIP MESSAGES — for pytest.skip() calls
# =============================================================================
SKIP_MSGS: Dict[str, str] = {
    "openmpi_not_enabled": "OpenMPI is not enabled in software_config.json",
    "no_nodes_for_packages": "No nodes found in PXE mapping for package verification",
}
```

### 6.2 Message Formatting Rules

- Use `{placeholder}` syntax for dynamic values
- Include **"HOW TO FIX"** sections in assertion messages — tell the user exactly what to do
- Provide diagnostic commands users can run
- Never hardcode IPs or environment-specific values in messages — use `<placeholder>` format

---

## 7. Test Writing Rules

### 7.1 Test File Location

Tests MUST be placed in:
```
validations/<scenario_name>/tests/<suite>/test_<component>.py
```

Suites: `sanity/`, `negative/`, `regression/`, `smoke/`, `stress/`, `performance/`

### 7.2 Test File Docstring (MANDATORY)

Every test file MUST start with a module-level docstring listing all test cases:

```python
"""
Provision Slurm Test Cases.

Test cases for verifying Slurm cluster:
1. Services on slurm_control_node (slurmctld, slurmdbd, munge, mariadb, sssd if enabled)
2. Services on slurm_node (slurmd, munge, sssd if enabled)
3. Services on login_node (slurmd, munge, sssd if enabled)
4. Services on login_compiler_node (slurmd, munge, sssd if enabled)
5. Cross-node SSH between all Slurm nodes
6. sinfo shows all compute nodes
7. OpenMPI installation (if enabled in software_config.json)
8. UCX installation (if enabled in software_config.json)
9. LDAP slapd.conf configuration (if OpenLDAP enabled)
"""
```

**Reference:** `validations/provision/tests/sanity/test_slurm.py`, `test_cloudinit.py`, `test_k8s.py`, `test_packages.py`, `test_ssh.py`

### 7.3 Test Function Structure (MANDATORY)

Every test function MUST follow this pattern:

```python
@pytest.mark.sanity
@pytest.mark.build_stream
@pytest.mark.order(10)
def test_slurm_control_node_services(host):
    """
    Test Case 10: Verify services on slurm_control_node.

    Services: slurmctld, slurmdbd, munge, mariadb
    If OpenLDAP enabled: sssd
    If LDMS enabled: ldmsd.sampler
    """
    # 1. Initialize logger with descriptive test name
    log = TestLogger("Verify slurm_control_node services")

    # 2. Get nodes dynamically from PXE mapping (NEVER hardcode)
    nodes = get_slurm_control_nodes(host)
    if not nodes:
        log.skipped("No slurm_control_node in PXE mapping", "Check PXE mapping file")
        pytest.skip("No slurm_control_node in PXE mapping")

    # 3. Check reachability with retry
    reach = check_nodes_reachability(
        host, nodes,
        retry_limit=PROVISION_REACHABILITY_RETRY,
        retry_interval=PROVISION_REACHABILITY_INTERVAL
    )

    # 4. Check for conditional features
    openldap_enabled = is_openldap_enabled(host)
    services = list(SLURM_CONTROL_SERVICES)
    if openldap_enabled:
        services.append("sssd")

    # 5. Run verification function (returns dict with success/error)
    log.check(f"Checking services on {len(reach['reachable'])} slurm_control_node")
    result = verify_services_on_nodes(host, reach["reachable"], services)
    details = build_service_details(result)

    # 6. Handle failure with detailed output
    if reach["unreachable"] or not result["success"]:
        fail_parts = []
        if reach["unreachable"]:
            fail_parts.append(
                f"Unreachable: {', '.join(n['hostname'] for n in reach['unreachable'])}"
            )
        if not result["success"]:
            fail_parts.append(f"Services failed: {', '.join(result['failed_details'])}")
        log.failed("slurm_control_node services check failed", details)
        assert False, "; ".join(fail_parts)

    # 7. Pass with details
    log.passed("All services running on slurm_control_node", details)
```

### 7.4 Test Output Format

Test output MUST use the `✓`/`✗` format with grouping by functional group or component:

```
Expected nodes:
  ✓ node1 - Ready
  ✓ node2 - Ready
  ✗ node3 - NOT FOUND in cluster
Extra nodes (not in PXE mapping):
  ✗ extra_node1

SSH Results (4 nodes):
  [slurm_control_node_x86_64]
    ✓ slurmctld1: SSH OK
  [slurm_node_x86_64]
    ✓ compute1: SSH OK
    ✗ compute2: SSH failed
```

**Reference:** See how `test_k8s.py`, `test_ssh.py`, and `test_slurm.py` build `details_lines` arrays.

### 7.5 Test Naming Convention

- Test functions: `test_<feature>_<aspect>(host)` — e.g., `test_slurm_control_node_services`, `test_k8s_nodes_ready`
- Test names in messages: `<feature>_<aspect>` — e.g., `"slurm_services"`, `"k8s_nodes_ready"`
- File names: `test_<component>.py` — e.g., `test_slurm.py`, `test_k8s.py`, `test_ssh.py`

### 7.6 Import Structure for Test Files

```python
# Standard library
import pytest

# Core module — shared utilities
from automation_library.core import TestLogger, check_nodes_reachability, is_software_enabled

# Module functions — verification logic
from automation_library.provision.functions import (
    get_all_slurm_nodes,
    verify_services_on_nodes,
    build_service_details,
)

# Module vars — constants (service lists, retry configs)
from automation_library.provision.vars import (
    SLURM_CONTROL_SERVICES,
    PROVISION_REACHABILITY_RETRY,
    PROVISION_REACHABILITY_INTERVAL,
)

# Module messages — assertion templates
from automation_library.provision.messages import TEST_ASSERT_MSGS as ASSERT_MSGS
```

### 7.7 Test Guidelines

- Each test must be independent — do not rely on execution order unless using `@pytest.mark.order(n)`.
- Use `pytest.skip()` with a clear reason when preconditions are not met — never let tests fail due to missing infrastructure.
- Always assert with descriptive messages. Use message templates from the module's `messages/` directory.
- Use the `host` fixture from `conftest.py` for OIM server connections — do not create your own.
- Mark tests with appropriate pytest markers: `@pytest.mark.sanity`, `@pytest.mark.negative`, `@pytest.mark.smoke`, etc.
- Register any new markers in `pytest.ini`.

### 7.8 Test Execution

- Use `./run_validation.sh <scenario> verify --suite sanity` for quick validation.
- Use `./run_validation.sh --config` for batch execution via `test_run_config.yml`.
- Run `./run_validation.sh list` to verify scenario discovery before execution.
- The `build_stream` scenario always uses `verify` (no deploy step).

---

## 8. Repository Structure

### 8.1 Validation Scenarios

Scenarios live under `validations/<scenario_name>/tests/` with:
- `test_deploy.py` — PlaybookRunner deploy test (`@pytest.mark.deploy`)
- `sanity/` — Sanity verification tests
- `negative/` — Negative tests (optional)

Shared utilities go in `automation_library/core/`. Do not duplicate functions across modules.

### 8.2 Configuration Files

- **`omnia_test_config.yml`** — Central config for OIM server details. Each user maintains their own copy.
- **`test_run_config.yml`** — Batch scenario runner config. Tracked in git.
- **`pytest.ini`** — Pytest settings and custom marker registration.
- **`requirements.txt`** — Pinned Python dependencies.

---

## 9. Code Standards

### 9.1 License Header (MANDATORY)

Every Python file MUST start with the Apache 2.0 license header.
**The year MUST be the current year when creating or updating a file.**

```python
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
```

### 9.2 Python

- Target Python 3.9+ compatibility.
- Use type hints for all function signatures.
- Follow PEP 8. Use `snake_case` for functions/variables, `UPPER_SNAKE_CASE` for constants.
- Imports must always be at the top of the file, never inline.
- Use `automation_library.core` for shared utilities — do not reimplement host connections, config loading, or formatting.

### 9.3 Import Organization

```python
# Standard library
import json
import os
import time
from typing import Dict, Any, List, Tuple

# Third-party
import yaml
import pytest

# Local — Core module
from automation_library.core import TestLogger, get_nodes_info, is_software_enabled

# Local — Same module
from ..vars.common_vars import SSH_OPTS, CONTAINER_NAME
from ..messages.module_msgs import TEST_NAMES, TEST_LOG_MSGS, TEST_ASSERT_MSGS
```

### 9.4 Docstrings (MANDATORY)

Every function MUST have a docstring:

```python
def verify_services_on_nodes(host, nodes: list, services: list) -> Dict[str, Any]:
    """
    Verify that specified services are running on all nodes.

    Args:
        host: Testinfra host object
        nodes: List of node dicts with hostname and admin_ip
        services: List of service names to check

    Returns:
        Dict containing:
            - success (bool): True if all services running on all nodes
            - failed_details (list): List of failure descriptions
            - results (list): Per-node results with service statuses
    """
```

### 9.5 Type Hints (RECOMMENDED)

```python
from typing import Dict, Any, List, Optional, Tuple

def get_config(host) -> Dict[str, Any]: ...
def verify_pods(host, nodes: list, namespace: str = "telemetry") -> Dict[str, Any]: ...
def get_nodes_by_group(host) -> Dict[str, List[Dict[str, str]]]: ...
```

### 9.6 Ansible

- Use FQCNs for all modules (e.g., `ansible.builtin.shell`, not `shell`).
- Always set `changed_when` and `failed_when` for shell/command tasks.
- Use `no_log: true` when handling passwords or credentials.
- Prefer reusable roles and `ansible.builtin.include_tasks` over inline task duplication.

### 9.7 Shell Scripts

- Start every script with `set -euo pipefail`.
- Use functions for reusable logic.
- Support `--help` and `--debug` flags where applicable.

---

## 10. Automation Execution Architecture

### 10.1 Multi-Layer Architecture (CRITICAL)

The automation framework operates in a **multi-layer architecture**:

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Automation Server (Separate Server)                   │
│  - User runs: ./run_validation.sh telemetry test                │
│  - Pytest executes test functions via PlaybookRunner             │
│  - Testinfra connects to OIM server                             │
└────────────────────┬────────────────────────────────────────────┘
                     │ SSH Connection (from omnia_test_config.yml)
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: OIM Server (Target Server)                            │
│  - IP: Specified in omnia_test_config.yml (oim_server_ip)       │
│  - Containers running: omnia_core, pulp, auth, etc.             │
│  - Testinfra host.run() executes commands here                  │
└────────────────────┬────────────────────────────────────────────┘
                     │ podman exec omnia_core
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: omnia_core Container                                  │
│  - All Omnia configurations stored here                         │
│  - Path: /opt/omnia/input/project_default/                      │
│  - SSH operations to K8s nodes executed from here               │
└────────────────────┬────────────────────────────────────────────┘
                     │ SSH to K8s/Slurm nodes (via PXE mapping)
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4: Cluster Nodes (K8s / Slurm / Minimal OS)             │
│  - kubectl commands executed here                               │
│  - Service verification performed here                          │
│  - Package verification performed here                          │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Command Execution Patterns

**Pattern 1: Run on OIM Server**
```python
cmd = host.run("podman ps")
```

**Pattern 2: Run Inside omnia_core Container**
```python
cmd = host.run("podman exec omnia_core bash -lc 'pulp rpm repository list'")
```

**Pattern 3: SSH from omnia_core to Cluster Node**
```python
ssh_cmd = (
    f"podman exec omnia_core "
    f"ssh -o StrictHostKeyChecking=no root@{admin_ip} "
    f"'kubectl get nodes'"
)
cmd = host.run(ssh_cmd)
```

**Pattern 4: Run ochami commands (OUTSIDE container on OIM directly)**
```python
cmd = host.run("ochami smd component get")
```

### 10.3 Path Logic: Inside vs Outside Container (CRITICAL)

| Operation | Where to Execute | Path to Use |
|-----------|-----------------|-------------|
| Read PXE mapping | INSIDE container | `/opt/omnia/input/project_default/pxe_mapping_file.csv` |
| Read config files | INSIDE container | `/opt/omnia/input/project_default/<config>.yml` |
| Read nodes.yaml | INSIDE container | `/opt/omnia/openchami/workdir/nodes/nodes.yaml` |
| Run ochami commands | OUTSIDE container | Direct `ochami smd component get` |
| SSH to cluster nodes | FROM container | `podman exec omnia_core ssh root@{admin_ip}` |
| Read oim_metadata.yml | INSIDE container | `/opt/omnia/.data/oim_metadata.yml` |

**Common Mistakes to Avoid:**

1. ❌ Running `podman exec omnia_core ochami ...` — ochami is NOT in container
2. ❌ Reading `/opt/omnia/...` directly on OIM — Use container paths via `podman exec`
3. ❌ SSH to nodes directly from OIM — SSH keys are in container
4. ❌ Assuming hostname matches exactly — Nodes may have domain suffix

**Correct Patterns:**

```python
# Read file from INSIDE container
cmd = host.run("podman exec omnia_core cat /opt/omnia/input/project_default/pxe_mapping_file.csv")

# Run ochami OUTSIDE container
cmd = host.run("ochami smd component get")

# SSH to node FROM container
cmd = host.run(f"podman exec omnia_core ssh root@{admin_ip} hostname")

# Compare hostnames (handle domain suffix)
actual_short = actual_hostname.split('.')[0]
expected_short = expected_hostname.split('.')[0]
match = (actual_short == expected_short)
```

---

## 11. Error Handling Rules

### 11.1 Graceful Error Handling

```python
def get_config(host) -> Dict[str, Any]:
    """Get configuration with proper error handling."""
    try:
        cmd = host.run(f"podman exec {CONTAINER_NAME} cat {CONFIG_PATH}")
        if cmd.rc != 0:
            return {"error": f"Failed to read config: {cmd.stderr}"}

        config = yaml.safe_load(cmd.stdout)
        return config if config else {"error": "Config is empty"}

    except yaml.YAMLError as e:
        return {"error": f"Failed to parse YAML: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
```

### 11.2 Error Propagation

Functions should return errors in a consistent format:

```python
def verify_feature(host, nodes) -> Dict[str, Any]:
    config = get_config(host)
    if config.get("error"):
        return {
            "success": False,
            "error": config["error"],
        }
    # Continue with verification...
```

---

## 12. Security

- Never commit IP addresses, passwords, API keys, or internal endpoints.
- Use `<PLACEHOLDER>` format in documentation and examples.
- Use `no_log: true` in Ansible tasks that handle credentials.
- Use `automation_library.core.secrets` for ansible-vault decryption.
- Never hardcode credentials in test files — read from config or vault.

---

## 13. Documentation

- The README must reflect the current repository structure at all times.
- All `omnia_test_config.yml` parameters must be documented with type, default, and description.
- All validation scenarios must be listed in the scenarios table.
- All dataset files must be documented with which Omnia playbook consumes them.
- Use conventional commit format: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- Reference the scenario or module name when applicable (e.g., `feat(telemetry): add VictoriaMetrics retention test`).

---

## 14. Adding New Scenarios

When adding a new validation scenario:

1. **Analyze the Omnia code** — Clone the repo branch or `podman exec -it omnia_core bash` and study the target playbook and its roles.
2. Create `automation_library/<module>/` with `__init__.py`, `functions/`, `messages/`, `vars/`.
3. Create `validations/<scenario>/tests/` with `__init__.py` and `sanity/` subdirectory.
4. If the scenario deploys a playbook, add `test_deploy.py` with `@pytest.mark.deploy` using `PlaybookRunner`.
5. Add verification tests in `tests/sanity/test_<scenario>.py`.
6. Add the scenario to:
   - `test_run_config.yml` (with `run: false` default)
   - `run_validation.sh` `SUPPORTED_SCENARIOS` array
   - `README.md` scenarios table
7. Export public functions from the module's `__init__.py`.

---

## 15. Validation Lifecycle Rules

- **deploy** — `test_deploy.py` uses `PlaybookRunner` to execute the Ansible playbook inside `omnia_core` with live streaming output. Must check container existence first.
- **verify** — pytest-testinfra tests. Must handle missing infrastructure gracefully with `pytest.skip()`.
- **test** — Runs deploy followed by verify sequentially.

**Deploy sync + container rules:**

- `PlaybookRunner.run()` automatically syncs the dataset into the container (via `sync_dataset()`) **before** running the playbook when `sync_dataset_to_core: true`. Pass `sync=False` to opt out. The `omnia_test_credentials.yml` is decrypted in memory at runner init, and the dataset's `omnia_config_credentials.yml` is vault-encrypted before the rsync.
- `omnia_sh_install` uses `run_shell()` (`omnia.sh --build`/`--install`), **not** `run()`, so it never syncs project inputs — the container is being created.
- Cleanup/uninstall scenarios (`oim_cleanup`, `omnia_sh_uninstall`) combine the container pre-check and playbook execution into a **single deploy test case**: if the container is not running there is nothing to do, so the test is **skipped and reported as passed**. Normal deploy scenarios instead **fail** when the container is not running.

### 15.1 Validation Scenario Structure (MANDATORY)

```
validations/<scenario>/
└── tests/
    ├── __init__.py           # Test module marker
    ├── test_deploy.py        # PlaybookRunner deploy test (@pytest.mark.deploy)
    ├── sanity/
    │   ├── __init__.py
    │   └── test_<scenario>.py
    └── negative/             # Optional
        ├── __init__.py
        └── test_<scenario>_negative.py
```

### 15.2 PlaybookRunner Usage (for deploy tests)

```python
import pytest
from automation_library.playbook_runner import PlaybookRunner, run_playbook

@pytest.mark.deploy
@pytest.mark.order(0)
def test_deploy(host):
    """Deploy the playbook with live streaming output."""
    result = run_playbook("/omnia/<playbook_dir>/<playbook>.yml")
    assert result["success"], result["error"]
```

---

## 16. Configuration Management

### 16.1 omnia_test_config.yml

- Use placeholder values in documentation (e.g., `<OIM_SERVER_IP>`, `<SSH_PASSWORD>`).
- All config keys must have sensible defaults in the consuming code (use `.get(key, default)`).
- New parameters must be documented in the README parameter reference table.

### 16.2 test_run_config.yml

- A top-level `oim_prereq_test: true/false` flag (defined **above** `scenarios:`)
  gates the `oim-prereq-test` prerequisite tool. It is not a scenario.
- Keep all scenarios listed even if disabled (`run: false`).
- Each scenario entry must have exactly five fields: `order`, `run`,
  `command`, `suite`, `marker`.
- `order` values must be **unique** across scenarios (duplicates abort the
  batch) but need not be contiguous.
- Group scenarios with section comments (e.g., `# --- Install & Setup ---`).
- This file is tracked in git — keep it minimal and clean.

### 16.3 test_run_config.yml Validation

The `run_validation.sh --config` command validates `test_run_config.yml` **before** executing any scenarios. Validation checks:

- **Prerequisite gate** — when `oim_prereq_test: true`, `oim-prereq-test` runs first; a failure aborts the batch before any scenario runs.
- **Scenario order** — every scenario needs an `order` value; missing or duplicate order values abort the batch. Scenarios execute in ascending `order`.
- **`run` values** must be `true` or `false` (YAML booleans).
- **`command` values** must be one of: `test`, `verify`, `deploy`.
- **`suite` values** must be one of: `sanity`, `negative`, `regression`, `smoke`, `stress`, `performance`, `build_auto`, `deploy_auto`, `build_manual`, `deploy_manual`, `cleanup_manual`, or empty string (all tests).

When adding a new scenario or suite, update the `SUPPORTED_*` variables at the top of `run_validation.sh`.

### 16.4 Batch Execution Behavior

- **Stop on failure** — by default, `--config` mode stops the batch when any
  scenario fails. The user is expected to fix the issue and re-run; the batch
  automatically resumes from where it left off (see below).
- **`--continue-on-failure`** — when passed, the batch continues executing
  remaining scenarios even if one fails. The final exit code still reflects
  whether any scenario failed.
- **Resume with track file** — batch progress is recorded in `.batch_track`.
  On re-run, scenarios that completed successfully in a previous run are
  skipped. The track file is keyed by report ID: if the report ID changes,
  a fresh run starts automatically.
- **`--restart`** — discards the `.batch_track` file and starts the batch
  from the first scenario regardless of previous progress.
- **Track file cleanup** — when all scenarios pass, the track file is
  automatically deleted.

### 16.5 Custom Report ID

- `report_id` in `omnia_test_config.yml` sets a custom report identifier.
  When empty (default), a timestamp-based ID is auto-generated.
- When the same `report_id` is reused across runs, results are **appended**
  to the existing report entry instead of creating a new run.
- The report ID is shared across all scenarios in a batch run and drives
  both the JSON/HTML report grouping and the resume track file.

---

## 17. Dependencies and Git Workflow

- Pin all dependency versions in `requirements.txt`.
- Do not add dependencies without confirming compatibility with the existing stack.
- The `-e .` entry in `requirements.txt` installs the local package in editable mode — do not remove it.
- Keep commits atomic — one logical change per commit.
- Ensure `./run_validation.sh list` works before pushing.
- Run at least one `verify` scenario to confirm no import errors.
- Clone repository with release-specific branch: `git clone -b automation-<release> https://github.com/dell/omnia-artifactory.git`

---

## 18. Code Quality Rules (MANDATORY)

### 18.1 Ansible-Lint Rules (Configuration Files)

All YAML configuration and playbook files MUST pass `ansible-lint` with NO errors:

```bash
ansible-lint omnia_test_config.yml test_run_config.yml
podman exec omnia_core ansible-lint /omnia/<playbook_dir>/<playbook>.yml
```

Common ansible-lint issues to avoid:
- `yaml[truthy]` — Use `true`/`false` not `yes`/`no`
- `yaml[line-length]` — Lines must not exceed 160 characters
- `yaml[trailing-spaces]` — No trailing whitespace
- `yaml[new-line-at-end-of-file]` — Files must end with a newline
- `name[missing]` — All tasks MUST have a `name`

### 18.2 Ansible-Lint Rules

All Ansible playbook files MUST pass ansible-lint with NO errors.

```bash
podman exec omnia_core ansible-lint /omnia/<playbook_dir>/<playbook>.yml
```

Common ansible-lint issues to avoid:
- `yaml[truthy]` — Use `true`/`false` not `yes`/`no`
- `name[missing]` — All tasks MUST have a `name`
- `risky-shell-pipe` — Use `set -o pipefail` for shell pipes
- `no-changed-when` — Add `changed_when` to shell/command tasks

### 18.3 Python Import & Dead-Code Rules (MANDATORY)

- **No unused imports.** Every import must be used in the file. The only
  exception is a re-export: a name imported purely so a package/module
  `__init__.py` (or an aggregating module) can expose it. Re-exported names MUST
  appear in that file's `__all__`.
- **No `import *`.** Always import specific names, even when a matching `__all__`
  already exists (convert star imports to explicit imports).
- **No dead / duplicate functions.** Do not keep superseded implementations
  alongside their replacements. When a testinfra-based function replaces a legacy
  subprocess-based one, delete the legacy version and update all `__init__.py`
  exports — never leave two functions with the same name in one module.

Verify with `pyflakes` before committing:

```bash
python3 -m pyflakes automation_library/ validations/ utility/
```

Only re-export lines (imported-but-unused names that are listed in `__all__`)
are acceptable findings; all other unused imports must be removed.

### 18.4 Pre-Commit Quality Checks

Before committing any code, run these checks:

```bash
# 1. Lint for unused imports / dead code
python3 -m pyflakes automation_library/ validations/ utility/

# 2. Run tests
./run_validation.sh <scenario> verify

# 3. Verify scenario listing
./run_validation.sh list
```

---

## 19. Cloud-Init Customization

The `additional_cloud_init.yml` dataset file allows injecting custom cloud-init configuration into provisioned nodes:

- **`common`** section applies to ALL nodes.
- **`groups`** section provides per-functional-group overrides.
- Allowed keys: `write_files`, `runcmd` only.
- Prohibited keys: `bootcmd`, `network`, `network-config`, `packages` (platform-managed).
- Platform defaults always take precedence (`merge_how: no_replace`).
- Group names must match functional groups in `pxe_mapping_file.csv`.

---

## 20. Local Mode Execution

When `oim_server_ip` is empty or set to `localhost`:

- All Ansible plays use `ansible_connection: local` instead of SSH.
- `get_testinfra_host()` returns a `local://` connection.
- `omnia_sh_install` deploy runs `omnia.sh --install` on the local machine.
- No SSH credentials are required.
- Dataset sync uses localhost as the rsync target.

This allows running the full automation stack on a single OIM server without a remote control node.

---

## 21. Reference Implementations

For any questions about implementation patterns, refer to these modules:

### 21.1 Provision Module (`automation_library/provision/`) — Primary Reference

| File | What to Learn |
|------|--------------|
| `functions/common_func.py` | Node retrieval, SSH helpers, skip functions, reachability checks |
| `functions/slurm_func.py` | Service verification, cross-node SSH, software checks |
| `functions/ldap_func.py` | LDAP configuration, PAM verification, user login testing |
| `functions/package_collector.py` | Image YAML parsing, package list building |
| `vars/common_vars.py` | Container name, SSH opts, retry configs, path constants |
| `vars/slurm_vars.py` | Service lists as tuples |
| `messages/provision_msgs.py` | Complete TEST_NAMES, TEST_LOG_MSGS, TEST_ASSERT_MSGS, SKIP_MSGS |

### 21.2 Provision Test Files — Reference for Test Patterns

| Test File | Patterns Demonstrated |
|-----------|----------------------|
| `test_cloudinit.py` | First test (order=1), connectivity + cloud-init, grouped output |
| `test_ssh.py` | OIM and core SSH verification, reachability with retry, grouped details |
| `test_packages.py` | Build stream gating, package verification, message template usage |
| `test_slurm.py` | Service checks, conditional features, skip helpers, LDAP/PAM testing |
| `test_k8s.py` | K8s node ready, storage class, pod verification, unexpected detection |

### 21.3 Core Module (`automation_library/core/`) — Shared Utilities

- Host connection patterns (`get_testinfra_host()`)
- Input file loading with caching (`load_input_file()`, `get_input_value()`)
- PXE mapping parsing (`get_nodes_info()`, `get_functional_groups_from_pxe_mapping()`)
- Report generation (`TestReport`)
- Secrets management (`view_credentials_file()`)

---

## 22. Quality Checklist

Before submitting any new code, verify:

### Module Structure
- [ ] Follows `functions/`, `vars/`, `messages/` structure
- [ ] All `__init__.py` files properly export items
- [ ] License headers in all files (current year)
- [ ] Messages ONLY in `messages/` directory
- [ ] Variables/Constants ONLY in `vars/` directory

### Functions
- [ ] Checked core module for existing functions FIRST
- [ ] Return dictionaries with `success`, `error` keys
- [ ] Use dynamic inputs (no hardcoded IPs, paths, credentials)
- [ ] Include proper docstrings with Args/Returns
- [ ] Implement caching for expensive operations

### Variables
- [ ] Import shared constants from core (don't duplicate)
- [ ] Service lists as tuples (immutable)
- [ ] Config paths are constants, not hardcoded in functions

### Messages
- [ ] `TEST_NAMES`, `TEST_LOG_MSGS`, `TEST_ASSERT_MSGS` defined
- [ ] Assertion messages include "HOW TO FIX" sections
- [ ] All messages use `{placeholder}` syntax
- [ ] `SKIP_MSGS` defined for skip reasons

### Tests
- [ ] Module docstring lists all test cases
- [ ] Use `TestLogger` for structured logging
- [ ] Get inputs dynamically from PXE mapping/configs
- [ ] Include skip logic for optional features
- [ ] Follow the standard test function structure
- [ ] Output uses `✓`/`✗` format grouped by functional group
- [ ] Import messages from `messages/` directory (not inline strings)
- [ ] Import constants from `vars/` directory (not inline values)

### Connection Architecture
- [ ] Use `get_testinfra_host()` for OIM connection
- [ ] Use `get_nodes_info()` for cluster node IPs
- [ ] Read configs from inside omnia_core container
- [ ] Execute kubectl via SSH from omnia_core
- [ ] Never hardcode IPs, paths, or credentials

### Playbook Integration
- [ ] Analyzed the Omnia playbook (clone branch or inspect container)
- [ ] Identified all resources created by playbook
- [ ] Mapped each resource to verification test
- [ ] Tested connection chain before writing automation

---

*Last Updated: 2026*
*These rules are mandatory for all developers working on the Omnia Automation Framework.*
*Reference implementation: `automation_library/provision/` and `validations/provision/tests/sanity/`*
