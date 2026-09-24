# Orchestrator — Test Automation

Functional and unit-test automation for the `orchestrator` domain in the
Omnia monorepo. The module validates the product lifecycle from OIM precheck
through node PXE boot, together with Kubernetes, Slurm, and Apptainer
post-boot behavior.

The framework uses the shared `omnia-auto` package for target connections,
playbook execution, structured logging, and JSON/HTML reports.

## Safety model

The runner separates product execution from verification:

| Command | Behavior |
|---|---|
| `exec` | Execute the selected Orchestrator playbook tag; do not run verification |
| `verify` | Verify existing state; do not execute the product playbook |
| `test` | Execute the selected tag once, then verify only if execution succeeds |

Most verification is observational. Tests that create workloads, download
images, drain scheduler nodes, reboot machines, or delete deployment state
are protected by explicit markers. Cleanup is excluded from every implicit
full-lifecycle run and must be selected by name.

## Prerequisites

| Requirement | Minimum or expectation |
|---|---|
| Python | 3.12 or later |
| Ansible Core | 2.20 or later; installed by `setup_env.sh` |
| Target | An Omnia OIM with `/etc/omnia/omnia.env` configured |
| Remote mode | SSH access to the OIM; `rsync` available on both ends |
| Cluster verification | The selected lifecycle must already have completed successfully |

The target OIM environment supplies these runtime locations:

| Variable | Purpose |
|---|---|
| `SYSTEM_ADMIN_NIC_IPV4` | Administrative address assigned to the OIM |
| `SYSTEM_HOSTNAME` | Expected OIM short hostname |
| `SYSTEM_DOMAIN_NAME` | Expected OIM DNS domain |
| `OMNIA_DATA_PATH` | Base Omnia data directory |
| `ORCHESTRATOR_DATA_PATH` | Optional Orchestrator data-root override |
| `REPO_MANAGER_DATA_PATH` | Optional Repo Manager data-root override |
| `IMAGE_BUILD_MANAGER_DATA_PATH` | Optional Image Build Manager data-root override |
| `OMNIA_PROJECT_NAME` | Active project used for input and output paths |

Prepare the target with the supported Omnia setup flow before running this
automation. The tests read the effective environment from the target, not
from hard-coded `/omnia` or `/opt/omnia` assumptions.

## Quick start

```bash
cd test/orchestrator

# Create an isolated environment and install the test requirements.
./setup_env.sh --venv
source .venv/bin/activate

# Configure encrypted test credentials when password-based SSH or external
# LDAP verification is required.
./setup_env.sh --set-creds

# On the execution OIM, configure encrypted product-domain credentials.
./setup_env.sh --set-domain-creds

# Review target, synchronization, and batch-selection settings.
vi test_config.yml
vi test_run_config.yml

# Show the supported lifecycle and suite names.
./run_validation.sh fvt_orchestrator list

# Verify prerequisites before running any product operation.
./run_validation.sh fvt_orchestrator precheck verify

# Execute and verify one lifecycle phase after precheck succeeds.
./run_validation.sh fvt_orchestrator prepare test
```

Leave `oim_server_ip` empty when the automation runs directly on the OIM. Set
it to the OIM address and configure `oim_ssh_user` and `oim_ssh_port` for
remote execution.

## Environment setup

### Installation modes

| Command | Result |
|---|---|
| `./setup_env.sh` | Install into the active virtual environment, or with `pip --user` when none is active |
| `./setup_env.sh --force` | Reinstall all requirements in the selected environment |
| `./setup_env.sh --venv` | Create `.venv` and install requirements there |
| `./setup_env.sh --venv --force` | Recreate `.venv` and reinstall requirements |
| `./setup_env.sh --debug` | Show verbose package-installation output |

Run `./setup_env.sh --help` for the authoritative option list.

### Credential stores

The automation keeps execution credentials separate from product-domain
credentials.

| Store | Location | Contents |
|---|---|---|
| Test credentials | `test_creds.yml` in this directory | OIM SSH password and, when external LDAP validation is enabled, the required LDAP test username, password, and bind secret |
| Domain credentials | Active Orchestrator project input on the execution OIM | Provision, BMC, Slurm database, OpenLDAP database, and CSI credentials |
| Standalone LDAP credentials | `utility/openldap_server_credentials.yml` | Credentials used only by the standalone LDAP utility |

The credential YAML files are encrypted with Ansible Vault. Vault keys and
credential files are excluded by `.gitignore`.

```bash
# Configure password-based SSH to a remote OIM. When external LDAP validation
# is enabled in test_config.yml, this also collects the LDAP test identity and
# external bind secret.
./setup_env.sh --set-creds

# Product credentials. In remote mode, run this on the target OIM.
./setup_env.sh --set-domain-creds

# Update the complete test credential store later.
./setup_env.sh --update-creds
```

Update an existing store with `--update-creds` or `--update-domain-creds`.
CI systems can send the complete test credential object to `--creds-stdin`
without putting secrets in process arguments:

```json
{
  "oim_password": "...",
  "ldap_username": "...",
  "ldap_password": "...",
  "external_ldap_bind_password": "..."
}
```

LDAP identity fields are required by the selected Slurm/PAM LDAP tests. The
external bind secret is additionally required when
`validate_external_ldap: true` and `configure_external_ldap: true`. Product-
domain credentials continue to use `--domain-creds-stdin`.

Detailed references:

- [test configuration](docs/test_config.md)
- [batch configuration](docs/test_run_config.md)
- [test credentials](docs/test_creds.md)

## Execution and synchronization

`test_config.yml` is the authoritative non-sensitive configuration.

### Local mode

```yaml
oim_server_ip: ""
```

Commands execute on the current OIM. Input and dependency outputs remain
untouched unless their synchronization flags are enabled.

### Remote mode

```yaml
oim_server_ip: "192.0.2.10"
oim_ssh_user: root
oim_ssh_port: 22
clone_path: "/omnia"
```

The framework synchronizes the source checkout to `clone_path` and executes
verification through SSH. Password authentication uses encrypted
`test_creds.yml`; key-based SSH needs no stored password.

### Input synchronization

| Setting | Source when `dataset` is empty | Source when `dataset` is set |
|---|---|---|
| `sync_orchestrator_input` | `src/orchestrator/input/` | `datasets/<name>/input/` |
| `sync_repo_manager_output` | `src/orchestrator/samples/repo_manager_output/` | `datasets/<name>/repo_manager_output/` |
| `sync_image_build_manager_output` | `src/orchestrator/samples/image_build_manager_output/` | `datasets/<name>/image_build_manager_output/` |

All synchronization flags default to `false`. Selecting a dataset alone does
not modify the OIM. Domain credentials are never copied as dataset content.
See [datasets/README.md](datasets/README.md) for generation and selection.

## Running tests

Run commands from `test/orchestrator`:

```text
./run_validation.sh fvt_orchestrator <command> [options]
./run_validation.sh fvt_orchestrator <tag> <command> [options]
./run_validation.sh fvt_orchestrator list
./run_validation.sh nft_orchestrator test
./run_validation.sh ut_orchestrator test
./run_validation.sh --config
```

The implemented categories are FVT, NFT, and UT. NFT executes real lifecycle
operations and includes destructive prepare, provision, and cleanup cases.

### Lifecycle tags and suites

| Tag | Suites | Main contract |
|---|---|---|
| `precheck` | `environment`, `storage`, `dependencies`, `inputs` | OIM identity, selected NFS reachability, upstream artifacts, and required inputs |
| `prepare` | `openchami`, `network`, `openldap` | OpenCHAMI, PostgreSQL, networking, DNS/DHCP, and LDAP readiness |
| `provision` | `openchami` | Provision reports plus SMD, Boot Service, Metadata Service, and network inventory |
| `pxeboot` | `connectivity`, `cloudinit`, `kubernetes`, `slurm`, `apptainer` | Node boot completion and workload-cluster behavior |
| `cleanup` | `openchami`, `openldap`, `slurm`, `kubernetes`, `artifacts`, `credentials` | Explicit full-cleanup postconditions |

An untagged FVT flow uses `precheck -> prepare -> provision -> pxeboot`.
Cleanup is always explicit. Untagged verification excludes negative and
disruptive cases.

### Options

| Option | Meaning |
|---|---|
| `--suite <name>` | Run one suite belonging to the selected lifecycle tag |
| `--marker <expr>` | Select tests by registered pytest markers |
| `-v`, `--verbose` | Increase output verbosity |
| `--debug` | Run pytest with full debug verbosity |

Do not use an unknown suite name. Use `fvt_orchestrator list` to discover the
current directories.

### Marker expressions

| Syntax | Meaning | Example |
|---|---|---|
| Single marker | Select tests carrying that marker | `--marker sanity` |
| Comma | Logical OR | `--marker sanity,functional` |
| Plus | Logical AND | `--marker slurm+non_disruptive` |

`sanity+functional` selects only tests carrying both markers; it does not mean
“run sanity, then functional.” Use `sanity,functional` for that union.

Registered selectors include:

- Baseline and capability: `sanity`, `functional`, `connectivity`,
  `cloudinit`, `kubernetes`, `slurm`, `openldap`, and `apptainer`.
- Controlled mutation: `image_download`, `negative`, and `non_disruptive`.
- Maintenance-window operations: `disruptive`, `reboot`, and
  `scheduler_state`.
- Cleanup authorization: `destructive`.
- Non-functional contracts: `nft`, `performance`, `idempotency`, and
  `security`.

`deploy` is attached to lifecycle execution cases and is normally managed by
the runner rather than selected manually.

## Lifecycle examples

### Precheck

```bash
./run_validation.sh fvt_orchestrator precheck test
./run_validation.sh fvt_orchestrator precheck verify --suite environment
./run_validation.sh fvt_orchestrator precheck verify --suite storage
./run_validation.sh fvt_orchestrator precheck verify --suite dependencies
./run_validation.sh fvt_orchestrator precheck verify --suite inputs
```

The NFS case applies the same targeting rules as the product: a mount is
probed only when `functional_group_prefix` matches a functional group in the
active PXE mapping, or `groups` matches a mapped `GROUP_NAME`. The stock
`vast_storage` entry is checked only when selected by
`slurm_cluster[0].vast_storage_name`.

### Prepare

```bash
./run_validation.sh fvt_orchestrator prepare test
./run_validation.sh fvt_orchestrator prepare verify --suite openchami
./run_validation.sh fvt_orchestrator prepare verify --suite network
./run_validation.sh fvt_orchestrator prepare verify --suite openldap
```

Set `validate_external_ldap: true` to run external proxy and backend checks.
Set `configure_external_ldap: true` only when those checks may also reconcile
the local `omnia_auth` proxy configuration. An unchanged desired configuration
is an idempotent no-op; a failed changed configuration is rolled back.

### Provision

```bash
./run_validation.sh fvt_orchestrator provision test
./run_validation.sh fvt_orchestrator provision verify --suite openchami
```

Provision verification is controller-side and read-only. It gets effective
XNAME values from live SMD data; it does not derive them from CSV ordering or
create temporary inventory. Every OpenCHAMI verification run obtains a fresh
access token.

### PXE boot

PXE verification defaults to `sanity` when no marker is supplied:

```bash
./run_validation.sh fvt_orchestrator pxeboot test
./run_validation.sh fvt_orchestrator pxeboot verify
./run_validation.sh fvt_orchestrator pxeboot verify --suite connectivity
./run_validation.sh fvt_orchestrator pxeboot verify --suite cloudinit
./run_validation.sh fvt_orchestrator pxeboot verify --suite kubernetes
./run_validation.sh fvt_orchestrator pxeboot verify --suite slurm
./run_validation.sh fvt_orchestrator pxeboot verify --suite apptainer
```

Focused workload and image examples:

```bash
# All functional cases across the PXE suites.
./run_validation.sh fvt_orchestrator pxeboot verify --marker functional

# Slurm health, jobs, LDAP, and PAM without drain/reboot cases.
./run_validation.sh fvt_orchestrator pxeboot verify \
  --suite slurm --marker slurm+non_disruptive

# Apptainer workload cases after an image is already present.
./run_validation.sh fvt_orchestrator pxeboot verify \
  --suite apptainer --marker apptainer+functional

# Authorize the shared-image downloader explicitly.
./run_validation.sh fvt_orchestrator pxeboot verify \
  --suite apptainer --marker functional+image_download
```

Run disruptive checks only in an approved maintenance window:

```bash
./run_validation.sh fvt_orchestrator pxeboot verify \
  --marker disruptive+reboot
./run_validation.sh fvt_orchestrator pxeboot verify \
  --suite slurm --marker disruptive+scheduler_state
```

The authorization checks are enforced even when pytest is invoked directly.

### Cleanup

Cleanup always invokes the supported full product entry point:

```bash
./run_validation.sh fvt_orchestrator cleanup test --marker sanity
./run_validation.sh fvt_orchestrator cleanup verify --marker sanity
```

Review these `test_config.yml` settings first:

| Setting | `true` | `false` |
|---|---|---|
| `cleanup_credentials` | Remove Orchestrator credential artifacts | Preserve them |
| `cleanup_slurm` | Delete Slurm shared data, then detach storage | Preserve data, but detach storage |
| `cleanup_k8s` | Delete Kubernetes shared data, then detach storage | Preserve data, but detach storage |

All default to `true`. Cleanup removes deployment state and is not a harmless
verification workflow.

## Non-functional tests

NFT measures lifecycle duration, repeated-execution behavior, and sensitive
artifact permissions:

```bash
./run_validation.sh nft_orchestrator test
./run_validation.sh nft_orchestrator test --marker performance
./run_validation.sh nft_orchestrator test --marker idempotency
./run_validation.sh nft_orchestrator test --marker security
```

A complete NFT run provisions state and finishes with full cleanup. Duration
limits come from `nft_performance_threshold_seconds` in `test_config.yml`.
Run NFT separately from FVT cleanup and review the cleanup policy first. See
[nft/README.md](nft/README.md) for its 11 contracts and execution order.

## Batch execution

Enable selected scenarios in `test_run_config.yml`, then run:

```bash
./run_validation.sh --config
```

Each scenario supports `run`, `command`, `suite`, `marker`, `dataset`, and
the three synchronization overrides. `skip_on_failure` controls whether the
batch continues after a failed scenario. Cleanup remains disabled in the
shipped configuration.

## Reports

FVT runs write structured JSON and HTML reports using `report_path` and
`report_name` from `test_config.yml`. The default files are:

```text
/opt/omnia/reports/orchestrator_test_report.json
/opt/omnia/reports/orchestrator_test_report.html
```

Console output and report entries use stable IDs defined in
`library/vars/test_case_vars.py`. Skips are reported with their reason; they
are not silently converted into passes.

## Unit tests

```bash
./run_validation.sh ut_orchestrator test
```

For direct pytest execution, isolate UT collection from the parent FVT hooks:

```bash
python3 -m pytest --confcutdir=ut ut -q
```

See [ut/README.md](ut/README.md) for the covered contracts.

## Directory structure

```text
orchestrator/
├── fvt/                 lifecycle and suite test modules
├── nft/                 performance, idempotency, and security contracts
├── ut/                  offline unit contracts
├── library/functions/   reusable verification behavior
├── library/messages/    operator-facing result messages
├── library/vars/        immutable commands, IDs, and domain registry
├── datasets/            generated input/dependency snapshots
├── utility/             standalone external LDAP utility
├── test_config.yml      target, sync, LDAP, cleanup, and report settings
├── test_run_config.yml  batch scenarios
├── setup_env.sh         environment and credential setup
└── run_validation.sh    supported runner entry point
```

Additional documentation:

- [FVT contracts and organization](fvt/README.md)
- [NFT contracts and execution](nft/README.md)
- [Dataset selection and synchronization](datasets/README.md)
- [Dataset generator](datasets/generator/README.md)
- [Standalone utilities](utility/README.md)
- [Unit contracts](ut/README.md)
