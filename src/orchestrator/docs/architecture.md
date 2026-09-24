# Orchestrator -- Architecture

**Domain**: `orchestrator` | **Collection**: `omnia.orchestrator`

## System Context

```text
 Discovery                 Image Build Manager       Repository Manager
 pxe_mapping_file.csv      build_status.yml          repo_status.yml
          |                       |                         |
          +-----------------------+-------------------------+
                                  |
                    +-------------v--------------+
                    |       Omnia Orchestrator   |
                    |                            |
                    | validate -> prepare        |
                    | -> deploy -> provision     |
                    | -> validate -> PXE         |
                    +------+------+--------------+
                           |      |
                    +------v--+ +-v-------------------------+
                    |OpenCHAMI| | Provisioned node services |
                    |SMD/BSS/MS| | Kubernetes, Slurm, LDAP   |
                    +---------+ +---------------------------+
```

The Orchestrator is the post-discovery lifecycle domain. It deploys supporting
services on the OIM, translates desired cluster input into OpenCHAMI state,
provisions functional groups, initiates physical-server PXE boot, verifies
fresh boot and cloud-init completion, and publishes lifecycle reports.

## Scope and Ownership

Orchestrator owns the transition from validated cluster intent to a bootable
and verifiable physical-node configuration. It does not build OS images or
publish software repositories; those are upstream contracts.

| Concern | System of record | Orchestrator responsibility |
|---------|------------------|-----------------------------|
| Physical-node input | Discovery PXE mapping | Validate and normalize the current desired node set |
| Permanent node identity | SMD Hardware Inventory | Resolve Service Tag to XNAME and reject conflicting bindings |
| Current topology | SMD components and Ethernet interfaces | Reconcile node, NodeBMC, MAC, IP, and group state |
| Boot artifacts | Image Build Manager `build_status.yml` | Validate artifacts and reference them from boot configurations |
| Repository content | Repository Manager `repo_status.yml` | Consume endpoints, certificates, and staged package/image data |
| Boot policy | OpenCHAMI Boot Service | Reconcile functional-group configurations and remove conflicting MAC ownership |
| Node metadata | OpenCHAMI Metadata Service | Reconcile defaults, groups, per-node hostnames, and cloud-init |
| Workload configuration | `omnia_config.yml` and related project inputs | Generate Kubernetes, Slurm, storage, LDAP, and custom group content |
| Physical restart | iDRAC Redfish | Configure one-time PXE boot and reboot reachable selected servers |
| Applied-state evidence | Node SSH plus cloud-init | Verify fresh boot and publish per-node lifecycle status |

Orchestrator deliberately does not:

- infer a new hardware identity from CSV row position on later runs;
- delete an SMD Hardware Inventory identity merely because a row is absent;
- claim metadata is active on a running node before a verified new boot;
- continuously monitor Kubernetes, Slurm, CSI, or application health; or
- provide an in-place rollback for the v2.3 one-way OpenCHAMI upgrade.

## Runtime Topology

```text
                         OIM / Ansible controller
 +-----------------------------------------------------------------------+
 | omnia.sh -> orchestrator.yml                                          |
 |                                                                       |
 |  project input  -> validation -> desired-state roles                  |
 |                                      |                                |
 |  Vault credentials -> JWT ----------+|                                |
 |  gateway CA -------------------------||                                |
 |                                      vv                               |
 |  +---------------- OpenCHAMI HTTPS gateway :8443 ------------------+  |
 |  | TokenSmith | SMD | Boot Service | Metadata Service | CoreDHCP  |  |
 |  +---------------------------------------------------------------+-+  |
 |                                                                  |    |
 |  optional omnia_auth OpenLDAP       S3/image and repository data |    |
 +-------------------------------------------+-----------------------+----+
                                             |
                   DHCP/TFTP/iPXE + rootfs + cloud-init
                                             |
                         +-------------------v-------------------+
                         | provisioned physical servers          |
                         | Kubernetes | Slurm | OS-only | custom |
                         +-------------------+-------------------+
                                             ^
                                             |
                                  iDRAC Redfish power/PXE
```

There are four execution boundaries:

1. `localhost` resolves paths, validates project input, maintains controller
   output, and constructs dynamic inventory.
2. `oim` owns deployed services, OpenCHAMI API access, generated working files,
   and category provisioning.
3. `bmc` targets receive Redfish operations through
   `dellemc.openmanage` modules.
4. Provisioned node addresses receive passwordless SSH setup and post-boot
   verification.

## Execution Mode

The domain runs from the OIM through Ansible. Controller-side service tasks use
local execution; OIM service tasks use the generated `oim` inventory group;
node verification and configuration use SSH; iDRAC PXE operations use Redfish.

The canonical entry point is:

```bash
cd src/orchestrator/playbooks
ansible-playbook orchestrator.yml --tags <tag>
```

Direct phase-playbook execution is supported only when that phase's documented
setup and persisted-state prerequisites are already satisfied.

The top-level playbook is intentionally an import graph rather than one large
play. `orchestrator_setup` runs under `always`, validates public tags, resolves
environment-derived paths, creates the OIM group, and reconstructs persisted
state needed by independently selected phases.

## Tag Reference

| Tag | Main action | Credentials | Persistent services required |
|-----|-------------|-------------|------------------------------|
| *(none)* | Full lifecycle and conditional PXE | Yes | Created by flow |
| `precheck` | Input, parameter, repository, and image checks | No | No |
| `validate` | Input schema and logic validation | No | No |
| `credentials` | Credential collection and Vault encryption | Yes | No |
| `prepare` | Credentials, deploy, and readiness validation | Yes | Created by flow |
| `deploy` | Deploy OpenCHAMI and enabled OpenLDAP | Yes | Created by flow |
| `provision` | Reconcile services and node configuration | Yes | Yes |
| `execute` | Provision followed by conditional PXE | Yes | Yes |
| `validate-deployment` | Service readiness checks | No prompt | Yes |
| `pxeboot` | iDRAC boot and optional node verification | No prompt | Yes |
| `cleanup` | Selected component teardown | No prompt | Depends on target |
| `cleanup_credentials` | Remove credential and vault-key files | No | No |
| `upgrade` | Supported component upgrades | Existing | Yes |
| `rollback` | Reserved; report that rollback is unsupported | Existing | Yes |

The setup role rejects unsupported tags and known conflicting combinations.
Cleanup, credential cleanup, upgrade, and rollback carry `never` and cannot run
accidentally during the default lifecycle.

### Public Tag Composition

```text
prepare
  credentials -> deploy OpenCHAMI -> deploy OpenLDAP -> validate services

provision
  preamble -> Kubernetes -> Slurm/login -> OS-only -> custom -> validate

execute
  provision -> conditional PXE boot -> node verification -> reports

default (no tag)
  setup -> precheck -> credentials/deploy -> provision
        -> conditional PXE boot
```

`validate` is intentionally limited to input schema and cross-file logic.
`validate-deployment` checks already deployed OpenCHAMI and OpenLDAP services.
`precheck` adds environment, repository, image, mapping, storage, and timezone
prerequisites needed before deployment or provisioning.

## Execution Flow

### Step 0: Setup

- Resolve `OMNIA_DATA_PATH`, `ORCHESTRATOR_DATA_PATH`, and project identity.
- Reject unsupported or conflicting tags.
- Enforce the upgrade-in-progress guard.
- Initialize a missing project input directory from source templates.
- Load domain variables and the selected project configuration.
- Validate inputs before later setup tasks dereference them.
- Create persistent output state only for lifecycle phases that need it.

### Step 1: Validate and Precheck

- Validate YAML and CSV inputs against domain schemas and cross-file rules.
- Generate functional groups from the PXE mapping when required.
- Validate environment, networking, catalog, repository, and boot artifacts.
- Verify component-specific prerequisites without changing deployed services.

The `validate` tag is input-only. The broader `precheck` tag consumes upstream
repository, catalog, and image information required by later provisioning.

### Step 2: Credentials

- Collect missing mandatory credentials interactively.
- Store credentials in `orchestrator_credentials.yml` encrypted with Ansible
  Vault.
- Keep the vault key beside the project input as a root-protected hidden file.
- Reuse valid existing encrypted credentials on repeated runs.

Credentials are redacted with `no_log` in sensitive tasks. Cleanup removes the
credential file and key by default; `cleanup_credentials=false` preserves them.

### Step 3: Deploy and Validate Services

- Deploy OpenCHAMI containers and configuration on the OIM.
- Deploy `omnia_auth` OpenLDAP when enabled.
- Establish TokenSmith authentication and the trusted gateway CA.
- Validate OpenCHAMI, OpenLDAP, object storage, and required artifacts.

OpenCHAMI is exposed through its HTTPS gateway. Orchestrator API clients require
a TokenSmith JWT and verify the configured CA certificate.

### Step 4: Provision

Provisioning runs a shared preamble and then processes Kubernetes, Slurm,
OS-only, and custom categories:

1. Read and normalize the PXE mapping.
2. Resolve permanent Service Tag-to-XNAME bindings from SMD Hardware Inventory.
3. Reconcile SMD components, interfaces, and group membership.
4. Reconcile Boot Service configurations for functional groups.
5. Reconcile Metadata Service InstanceInfo, Group, and ClusterDefaults data.
6. Configure category-specific Kubernetes, Slurm, LDAP, and storage content.
7. Generate downstream inventories.
8. Validate registered nodes, interfaces, groups, boot configurations, and
   metadata.
9. Write provisioning and aggregate lifecycle reports.

Identity behavior is specified in
[`hardware-identity-mapping.md`](hardware-identity-mapping.md).

### Functional-Group Routing

The generated functional-group model classifies each mapping row before the
category plays run:

| Name pattern | Category play | Default layer | Default bolt-ons |
|--------------|---------------|---------------|------------------|
| `service_kube_*` | `provision_kubernetes.yml` | management | mounts, Kubernetes configuration, telemetry selection |
| `slurm_*` | `provision_slurm.yml` | control nodes: management; workers: compute | mounts, Slurm configuration, OpenLDAP |
| `login_node_*`, `login_compiler_node_*` | `provision_slurm.yml` | management | shares Slurm lifecycle and storage content |
| `os_*` | `provision_os.yml` | compute | none |
| all other names | `provision_custom.yml` | compute | none |

The configured `orchestrator.bolt_ons` map may override category defaults.
Registration is separated from final publication so Kubernetes and Slurm
bolt-ons can first produce mounts, configuration, and cloud-init fragments.

### Category Provisioning Sequence

```text
filter category rows
        |
        v
resolve Service Tag -> XNAME
        |
        v
clean category-owned stale endpoints
        |
        v
static discovery -> SMD components/interfaces
        |
        v
reconcile SMD groups and membership
        |
        +------> category bolt-ons create configuration
        |
        v
reconcile Boot Service configuration
        |
        v
reconcile Metadata Service defaults/groups/InstanceInfo
        |
        v
validate complete desired state and write reports
```

Category cleanup is scoped. Later categories must not remove nodes registered
by earlier categories in the same run. A functional-group move removes stale
membership and boot configuration associated with the affected node MAC before
publishing the new category state.

### Step 5: PXE Boot

When `enable_pxe_boot` is true, Orchestrator:

1. Resolves each Service Tag to its permanent SMD XNAME.
2. Selects the BMC targets from the current mapping or custom inventory.
3. Checks iDRAC reachability and readiness.
4. Configures one-time PXE boot and reboots reachable targets.
5. Optionally connects to each node over SSH.
6. Verifies that the boot timestamp is newer than the PXE request.
7. Verifies cloud-init completion with the node-local `node_boot_status` module.
8. Writes `pxeboot_status.yml`, `failed_nodes.json`, and the aggregate status.

A successful verified boot clears pending metadata application state. A boot
without node verification is reported as initiated but unverified.

### Step 6: Cleanup

The top-level cleanup route runs the canonical aggregate cleanup and reports
the result of every selected component. Component-specific cleanup is available
through `playbooks/cleanup/cleanup_orchestrator.yml` for Slurm, Kubernetes,
OpenCHAMI, OpenLDAP, storage mounts, artifacts, and credentials.

### Step 7: Upgrade and Rollback

Upgrade is an opt-in component workflow. The setup guard blocks normal
lifecycle operations while an upgrade lock exists. The OpenCHAMI upgrade path
detects the installed version, backs up configuration and SMD data, performs
the supported one-way upgrade, restarts services, verifies readiness, and
removes the lock after success. The OpenLDAP upgrade moves a deployed
`omnia_auth` service to the configured target image and verifies LDAP health.

Rollback is reserved for a future release. Both v2.3 rollback
playbooks fail explicitly without modifying the deployment. Recovery from an
unsuccessful one-way upgrade therefore depends on a full system backup taken
before the upgrade; the existence of pre-upgrade artifacts does not make the
`rollback` tag operational.

## OpenCHAMI Integration

```text
                         HTTPS + JWT + CA
 Orchestrator ------------------------------------------+
     |                                                  |
     +--> SMD: identity, components, interfaces, groups |
     +--> Boot Service: artifacts and boot parameters   |
     +--> Metadata Service: cloud-init and hostnames     |
     +--> TokenSmith: authentication/JWKS               |
                                                        |
 Provisioned nodes <---- iPXE, images, cloud-init ------+
```

The `openchami_reconcile` module provides declarative API operations. Shared
Python clients centralize authentication, TLS verification, response limits,
timeouts, and safe retries. Ansible tasks prepare desired state and consume
structured module results instead of parsing shell command output.

### Client and Reconciler Layers

```text
Ansible tasks
    |
    v
openchami_reconcile module
    |
    +-- OpenChamiReconciler
    |      +-- SMD identity/group/component operations
    |      +-- Metadata ownership and reconciliation
    |      +-- registration verification
    |
    +-- OpenChamiClient
    |      +-- SMDClient
    |      +-- MetadataClient
    |      +-- BootServiceClient
    |
    +-- StaticDiscovery
           +-- fixed-argument ochami discover static subprocess
```

The module exposes the following action contract:

| Action | Effect |
|--------|--------|
| `check_apis` | Verify required OpenCHAMI endpoints with JWT and CA trust |
| `resolve_identities` | Resolve or bootstrap persistent Service Tag-to-XNAME bindings |
| `reconcile_groups` | Create or update complete desired SMD group membership |
| `remove_group_memberships` | Remove selected nodes from non-protected SMD groups |
| `delete_groups` | Delete explicitly selected SMD groups |
| `cleanup_smd` | Remove category-scoped stale SMD endpoints and interfaces |
| `discover_static` | Invoke supported static discovery without a shell |
| `verify_components` | Read back expected node registration |
| `reconcile_instanceinfos` | Create, update, and deduplicate per-XNAME metadata |
| `reconcile_metadata_groups` | Reconcile project-owned Metadata Service groups |
| `prune_metadata_groups` | Safely remove stale owned groups with no SMD members |
| `reconcile_cluster_defaults` | Reconcile the project-owned cluster default |

The declarative module owns identity and Metadata Service reconciliation.
Selected service tasks use the `ochami` CLI or direct Ansible `uri` calls for
static discovery and Boot Service operations. They are not a second identity
authority. New service integration should use the shared Python client when
its API is supported.

### OpenCHAMI Data Model

| OpenCHAMI resource | Key used by Orchestrator | Meaning |
|--------------------|--------------------------|---------|
| Node component | Node XNAME | Physical server identity |
| NodeBMC component | Parent XNAME | Server-management controller |
| Hardware Inventory | Node XNAME plus Service Tag serial | Permanent identity binding |
| Ethernet interface | Normalized MAC ID | Admin or BMC address bound to a component |
| SMD group | Group label | Functional/common membership |
| Boot configuration | Functional-group name and member MACs | Kernel, initrd, rootfs, and boot parameters |
| InstanceInfo | Node XNAME | Hostname and per-node metadata |
| Metadata group | Group name | Group-scoped cloud-init configuration |
| ClusterDefaults | Project-owned name | Shared cluster identity and public keys |

The PXE mapping remains desired input, while SMD Hardware Inventory persists
identity across row reordering, hostname changes, IP changes, NIC replacement,
and functional-group moves.

### Authentication and Trust

1. `gen_access_token` obtains a short-lived TokenSmith JWT on the OIM.
2. Sensitive token facts and credential operations are protected by
   `no_log`.
3. The reconciliation module requires an HTTPS cluster URI and a CA path.
4. The shared client validates the gateway certificate, bounds response size,
   uses finite timeouts, and retries only safe operations.
5. The static-discovery adapter receives the token in a specifically named
   environment variable and passes the CA as an argument.

The CA proves the gateway identity; it does not replace JWT authorization.
OpenLDAP uses a separate TLS configuration and credential lifecycle.

## Runtime State

The domain data root defaults to `$OMNIA_DATA_PATH/orchestrator`:

```text
orchestrator/
+-- input/<project>/
|   +-- orchestrator_config.yml
|   +-- pxe_mapping_file.csv
|   +-- orchestrator_credentials.yml
+-- output/<project>/
|   +-- .data/functional_groups_config.yml
|   +-- orchestrator_state.yml
|   +-- provisioning_report.yml
|   +-- pxeboot_status.yml
|   +-- orchestrator_status.yml
|   +-- failed_nodes.json
+-- log/
```

Ansible execution logs are stored under `/var/log/omnia/orchestrator/`, with
separate files for the top-level, cleanup, credentials, deploy, prepare,
provision, PXE, rollback, upgrade, and validation flows.

### Desired State Versus Applied State

`orchestrator_status.yml` is not a general monitoring database. It is a
project-scoped lifecycle report that correlates the current inventory with the
last provisioning and PXE verification results.

| Field | Interpretation |
|-------|----------------|
| `identity_changed` | This lifecycle created the Service Tag-to-XNAME binding |
| `metadata_changed` | Desired metadata differs from the last verified applied state |
| `reprovision_required` | A verified fresh boot is still needed |
| `running_state_updated` | PXE freshness and node verification proved application |
| `provisioning.status` | OpenCHAMI desired-state reconciliation result |
| `pxeboot.status` | BMC boot and optional node verification result |

Running `provision` twice without PXE boot does not clear an existing
`reprovision_required` condition. A successful fresh boot with node
verification clears it. Manual boot without an Orchestrator verification run
is not automatically observed.

## Output Contracts

| Output | Producer | Primary consumers |
|--------|----------|-------------------|
| `functional_groups_config.yml` | Functional-group generation | Provisioning and validation |
| `orchestrator_state.yml` | Setup lifecycle | Standalone provision phases |
| `provisioning_report.yml` | Provision validation | PXE and operators |
| `pxeboot_status.yml` | PXE workflow | Operators and automation |
| `orchestrator_status.yml` | Provision and PXE workflows | Resume, reporting, and operators |
| Generated inventories | Inventory generation | Kubernetes, Slurm, telemetry, and validation |

See [`contracts/input-contract.md`](contracts/input-contract.md) and
[`contracts/output-contract.md`](contracts/output-contract.md) for complete
field-level contracts.

## Validation Boundaries

- Input validation checks structure and cross-file consistency before mutation.
- Service validation checks OpenCHAMI and OpenLDAP readiness.
- Provision validation checks desired registration and configuration state.
- PXE verification proves a fresh boot and acceptable cloud-init completion.
- Orchestrator does not continuously monitor Kubernetes, Slurm, CSI, or
  application health after the lifecycle finishes.

## Idempotency and Mutation Rules

- Setup and validation reconstruct facts without treating them as deployed
  state.
- Existing encrypted credentials are reused unless the credential workflow
  requires a change.
- Identity allocation is serialized with a root-owned lock and persists only
  missing Hardware Inventory records.
- Metadata resources are compared before create/update and carry
  project-ownership labels for safe pruning.
- SMD cleanup is scoped by category and component ownership.
- Boot configurations for the target groups are replaced deliberately so MAC
  ownership and artifact references cannot remain stale.
- Removing a PXE mapping row does not free its XNAME or delete its Hardware
  Inventory record.
- Cleanup is destructive and opt-in; credentials are included by default
  unless `cleanup_credentials=false` is supplied.

## Failure and Recovery Model

| Failure point | Recorded behavior | Safe next action |
|---------------|-------------------|------------------|
| Input/schema failure | Stops before service mutation | Correct project input and rerun validation |
| Identity conflict | Stops before conflicting discovery | Correct PXE mapping or deliberately repair SMD |
| OpenCHAMI API/TLS/auth failure | Reconciliation fails with endpoint detail | Restore service, JWT generation, DNS, or CA trust |
| Category provisioning failure | Earlier successful service writes may remain | Correct cause and rerun; reconciliation is designed to converge |
| Unreachable iDRAC | Node is reported failed at `pxe_boot` | Restore BMC access and rerun PXE |
| SSH not yet ready | Action plugin returns retryable `unreachable` | Allow built-in retries or rerun PXE verification |
| Cloud-init terminal failure | Node remains failed/reprovision-required | Correct metadata or node issue, then perform a fresh verified boot |
| Interrupted upgrade | Upgrade lock blocks normal lifecycle | Resume supported upgrade or restore a full pre-upgrade backup |

Provisioning is convergent, not transactional across every external service.
Reports identify the last completed phase and per-node result so a rerun can
continue from a known desired-state input.

## Code Organization

| Path | Responsibility |
|------|----------------|
| `playbooks/orchestrator.yml` | Canonical lifecycle and public tag composition |
| `playbooks/<phase>/` | Focused prepare, deploy, provision, validate, PXE, cleanup, upgrade, and reserved rollback plays |
| `roles/orchestrator_setup/` | Environment, path, tag, inventory, and persisted-state setup |
| `roles/orchestrator_validations/` | Cross-file, image, storage, mapping, and environment prerequisites |
| `roles/provision_common/` | Active category registration and OpenCHAMI publication |
| `roles/configure_ochami/` | Shared OpenCHAMI templates and service task library |
| `roles/<category>_config/` | Kubernetes, Slurm, mount, LDAP, and other bolt-on configuration |
| `roles/validate_provisioning/` | Desired-state readback and lifecycle reports |
| `roles/idrac_pxe_boot/` | Dell iDRAC one-time boot and reset operation |
| `roles/verify_node_registration/` | Fresh-boot and cloud-init verification orchestration |
| `plugins/modules/` | Structured validation, reconciliation, inventory, and node modules |
| `plugins/module_utils/openchami/` | Shared OpenCHAMI transport, identity, discovery, and reconciliation logic |
| `plugins/action/node_boot_status.py` | Controller-side SSH failure normalization and retry support |
| `containers/omnia_auth/` | Optional OpenLDAP container source |
| `docs/contracts/` | Maintained input and output interfaces |

`configure_ochami` owns reusable templates and focused service tasks.
`provision_common` coordinates those resources through the category
provisioning workflow; it is the supported lifecycle entry point.

## Extension Rules

When adding a functional group that matches an existing pattern, update the
input/catalog data only. A genuinely new category requires:

1. a classification entry in `vars/functional_group_classification.yml`;
2. a category provisioning play or an explicit mapping to an existing play;
3. any required boot and metadata templates;
4. input validation and contract updates;
5. desired-state readback in provisioning validation; and
6. cleanup ownership rules for newly managed artifacts.

When adding an OpenCHAMI operation, keep JWT handling, CA validation, response
limits, error normalization, and idempotent comparison in the shared client
and reconciler rather than adding shell-output parsing to a role.
