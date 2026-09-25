# test_config.yml — Configuration Reference

`test_config.yml` contains non-sensitive settings for Orchestrator test
execution. It selects the execution OIM, optional dataset synchronization,
external LDAP verification, cleanup policy, and report output. Secrets never
belong in this file.

## Connection and execution mode

| Field | Required | Default | Purpose |
|---|---|---|---|
| `oim_server_ip` | No | `""` | Empty runs locally; a hostname or IPv4 address enables remote execution. |
| `oim_ssh_user` | Remote only | `root` | SSH identity on the execution OIM. |
| `oim_ssh_port` | Remote only | `22` | SSH port on the execution OIM. |
| `clone_path` | Remote only | `/omnia` | Absolute repository destination on the execution OIM. |

Password-based remote execution uses encrypted `test_creds.yml`. Key-based
SSH does not require `oim_password`.

## Dataset and synchronization

`dataset` is empty by default. A non-empty value selects
`datasets/<name>/`. Selection alone never copies data.

| Field | Default | Copied content when enabled |
|---|---|---|
| `sync_orchestrator_input` | `false` | Orchestrator project input. |
| `sync_repo_manager_output` | `false` | Repo Manager `repo_status.yml` handoff. |
| `sync_image_build_manager_output` | `false` | Image Build Manager `build_status.yml` handoff. |

Input synchronization excludes credential files, vault keys, locks, and
backups. `verify` does not enable synchronization implicitly.

## External LDAP verification

`validate_external_ldap` defaults to `false`. When false, the automation
skips external LDAP proxy and backend validation without changing
`omnia_auth`. Local OpenLDAP runtime, artifact, TLS, and listener checks still
run when OpenLDAP is enabled by the active Orchestrator catalog.

When `validate_external_ldap` is true, all of these non-sensitive fields are
required:

| Field | Example | Purpose |
|---|---|---|
| `external_ldap_server_ip` | `ldap.example.test` | Existing directory endpoint reachable from the OIM. |
| `external_ldap_server_port` | `1389` | LDAP TCP port. |
| `external_ldap_domain` | `example.test` | Domain converted to `dc=example,dc=test`. |
| `external_ldap_bind_username` | `ldapadmin` | Account name used to build the bind DN. |

Configure the matching LDAP test and bind secrets with
`./setup_env.sh --set-creds`. Set `configure_external_ldap` to true only when
the test may reconcile `slapd.conf`; otherwise validation checks the existing
deployed proxy without changing it. Reconciliation updates the file only when
desired content differs and rolls back if `omnia_auth` does not become ready.

## Cleanup policy

Cleanup is destructive and must be selected explicitly. These booleans are
always passed to the cleanup playbook:

| Field | `true` | `false` |
|---|---|---|
| `cleanup_credentials` | Remove project credential artifacts. | Preserve credential artifacts. |
| `cleanup_slurm` | Delete Slurm shared data, then detach storage. | Preserve data, then detach storage. |
| `cleanup_k8s` | Delete Kubernetes shared data, then detach storage. | Preserve data, then detach storage. |

## NFT performance thresholds

`nft_performance_threshold_seconds` is a required mapping when NFT executes.
Every value is a positive integer number of seconds.

| Key | Shipped limit | Contract |
|---|---:|---|
| `precheck` | 60 | Complete the current project precheck lifecycle. |
| `prepare` | 300 | Deploy and reconcile the OIM services. |
| `provision` | 1800 | Reconcile the current project into OpenCHAMI. |
| `cleanup` | 180 | Complete the selected full-cleanup policy. |

The limits apply to the supported reference OIM with the active input and
mapped-node inventory. Update a threshold only with a documented environment
or acceptance-contract change.

## Reports

| Field | Purpose |
|---|---|
| `report_path` | JSON and HTML report directory. |
| `report_name` | Report basename without an extension. |
| `run_id` | Optional stable run identifier; empty generates a timestamp. |

## Validation

Review the configuration and verify prerequisites before mutation:

```bash
./run_validation.sh fvt_orchestrator precheck verify
```
