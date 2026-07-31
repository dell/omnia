# Omnia 2.2 -- Overall Architecture

## System Overview

Omnia is a Dell open-source HPC/AI cluster management solution that automates
infrastructure deployment on bare-metal servers. It is organized as a mono-repo
with independent **domains**, each packaged as an Ansible Galaxy collection.

**Every domain is independent and can be executed standalone.** Domains communicate
exclusively via YAML contract files (input/output). No domain imports code from
another domain.

```
  +----------------+     +---------------------+     +----------------+
  |                |     |                     |     |                |
  | repo_manager   |---->| image_build_manager |     | discovery      |
  | (Pulp RPM      |     | (OS image builds,  |     | (OME/BMC       |
  |  mirroring)    |     |  S3 storage)        |     |  inventory)    |
  |                |     |                     |     | [optional]     |
  +----------------+     +---------------------+     +----------------+
         |                        |                         |
         |    repo_status.yml     |    build_status.yml     | pxe_mapping.csv
         |                        |                         |
         v                        v                         v
  +--------------------------------------------------------------+
  |                                                              |
  |  orchestrator                                                |
  |  (OpenCHAMI deploy, PXE boot, K8s, Slurm, LDAP)             |
  |                                                              |
  +--------------------------------------------------------------+
                                  |
                                  v
                        +------------------+
                        |                  |
                        | telemetry        |
                        | (iDRAC, UFM,     |
                        |  Vector sinks)   |
                        |                  |
                        +------------------+

  +--------------------------------------------------------------+
  | build_stream (GitLab pipeline -- connects all domains)       |
  +--------------------------------------------------------------+
```

## Domain Catalog

| Domain | Collection | Purpose | Entry Point |
|--------|-----------|---------|-------------|
| **repo_manager** | `omnia.repo_manager` | Pulp-based RPM/tarball/pip/git mirroring for air-gapped clusters | `repo_manager.yml` |
| **image_build_manager** | `omnia.image_build` | OS image building (x86_64 + aarch64) via OpenCHAMI, S3 storage | `image_build_manager.yml` |
| **discovery** | `omnia.discovery` | OME/BMC server inventory, PXE mapping, network discovery (optional) | `discovery.yml` |
| **orchestrator** | `omnia.orchestrator` | OpenCHAMI deployment, PXE boot, K8s/Slurm/telemetry provisioning | `orchestrator.yml` |
| **telemetry** | `omnia.telemetry` | iDRAC/UFM telemetry collection via Vector bridge-sink architecture | `telemetry.yml` |
| **build_stream** | -- | CI/CD backend connecting all domains via GitLab pipeline | FastAPI app |

## Domain Independence

Each domain is **independently executable** via its own entry-point playbook.
A domain only needs its own input files and any upstream contract files it consumes.

```
+-------------------+          +-------------------+          +-------------------+
|   repo_manager    |          | image_build_mgr   |          |   orchestrator    |
|                   |          |                   |          |                   |
| IN:               |          | IN:               |          | IN:               |
|  repo_config.yml  |          |  image_build_     |          |  orchestrator_    |
|                   |          |   config.yml      |          |   config.yml      |
| OUT:              |   --->   |  repo_status.yml  |   --->   |  build_status.yml |
|  repo_status.yml  |          |                   |          |  pxe_mapping.csv  |
|                   |          | OUT:              |          |                   |
+-------------------+          |  build_status.yml |          +-------------------+
                               +-------------------+
```

**Key principle:** A domain can run without any other domain being installed.
It only requires the contract files it reads. These files can be manually created
or produced by an upstream domain.

## Typical Execution Order

When deploying a full cluster end-to-end, domains are executed in this order:

| Step | Domain | Purpose | Required |
|------|--------|---------|----------|
| 1 | **repo_manager** | Mirror RPM repos, generate `repo_status.yml` | Yes |
| 2 | **image_build_manager** | Build OS images using mirrored repos, upload to S3 | Yes |
| 3 | **discovery** | Discover servers via OME, generate PXE mapping | Optional |
| 4 | **orchestrator** | PXE boot nodes, deploy K8s/Slurm, configure services | Yes |
| 5 | **telemetry** | Enable iDRAC/UFM telemetry collection | Optional |

**BuildStream** orchestrates this sequence automatically via GitLab CI/CD pipeline,
but each domain can also be run manually via `ansible-playbook`.

## Inter-Domain Communication

Domains communicate exclusively via YAML contract files -- no direct code imports:

| Producer | Contract File | Consumer | Required |
|----------|--------------|----------|----------|
| `repo_manager` | `repo_status.yml` | `image_build_manager` | Yes |
| `repo_manager` | `repo_status.yml` | `orchestrator` | Yes |
| `image_build_manager` | `build_status.yml` | `orchestrator` (provision) | Yes |
| `discovery` | `bmc_pxe_mapping_file.csv` | `orchestrator` (PXE boot) | Optional |

## BuildStream -- Pipeline Orchestrator

BuildStream is a FastAPI-based CI/CD backend that connects all domains via
GitLab pipeline. It automates the full deployment sequence:

```
GitLab Pipeline (managed by BuildStream)
+-------+     +-----------+     +-----------+     +------------+     +-----------+
| repo  | --> | image     | --> | discovery | --> | orchestr-  | --> | telemetry |
| mgr   |     | build mgr |     | (optional)|     | ator       |     |           |
+-------+     +-----------+     +-----------+     +------------+     +-----------+
```

BuildStream provides:
- **Job management** -- submit, monitor, cancel build jobs
- **Catalog management** -- manage OS image catalogs and functional groups
- **Artifact tracking** -- S3 artifact paths and versioning
- **Pipeline triggers** -- automatic domain-to-domain handoff via contract files

## Repository Structure

```
omnia/
+-- docs/                              Cross-domain documentation
|   +-- architecture.md                This file -- overall architecture
|   +-- galaxy-testing-guide.md        Galaxy collection testing guide
|   +-- code-style/                    Coding standards (Ansible, Python, Jinja2)
|   +-- design/                        Cross-domain design documents
|       +-- domain-integration.md      Domain integration patterns
|       +-- omnia-domain-repo-design.md  Mono-repo design rationale
|       +-- test-automation-design.md  Test automation framework
+-- src/
|   +-- common/                        Shared library (callback_plugins, modules, vars)
|   +-- repo_manager/                  omnia.repo_manager collection
|   +-- image_build_manager/           omnia.image_build collection
|   +-- discovery/                     omnia.discovery collection
|   +-- orchestrator/                  omnia.orchestrator collection
|   +-- telemetry/                     omnia.telemetry collection
|   +-- build_stream/                  BuildStream CI/CD backend (FastAPI)
|   +-- main/                          omnia.sh, omnia-cli, environment setup
|   +-- playbooks/                     Cross-domain playbooks (utils, upgrade, rollback)
|   +-- utils/                         Shared utilities
+-- test/
    +-- fvt/                           Functional verification tests
    +-- nft/                           Non-functional tests
```

## Domain Architecture Pattern

Every domain follows the same Galaxy collection structure:

```
src/<domain>/
+-- galaxy.yml                 Collection metadata
+-- meta/runtime.yml           Ansible version requirements
+-- CHANGELOG.md               Version history
+-- README.md                  Domain documentation
+-- ansible.cfg                Local Ansible configuration
+-- plugins/
|   +-- modules/               Custom Ansible modules
|   +-- module_utils/          Shared Python utilities
|   |   +-- input_validation/  Input validation framework
|   |   |   +-- core/          Config, file utils, validation engine
|   |   |   +-- messages/      Centralized error message constants
|   |   |   +-- schema/        JSON schema files for L1 validation
|   |   |   +-- validators/    L2 business logic validators
|   |   +-- <domain_utils>/    Domain-specific utilities
|   +-- callback/              Ansible callback plugins
+-- roles/                     Ansible roles
+-- playbooks/                 Sub-playbooks (per-stage)
+-- input/                     Default input templates
+-- docs/                      Domain-specific documentation
    +-- architecture.md        Domain architecture overview
    +-- contracts/             Input/output YAML contract definitions
    +-- design/                Design documents
    +-- troubleshooting.md     Troubleshooting guide
```

## Input Validation Framework

All domains use a standardized two-level validation approach:

| Level | What | How | Where |
|-------|------|-----|-------|
| **L1 -- Schema** | Structure, types, required fields, enums | JSON Schema validation | `input_validation/schema/*.json` |
| **L2 -- Logic** | Cross-field consistency, business rules | Python validator functions | `input_validation/validators/*.py` |

Error messages are centralized in `input_validation/messages/` for consistency
and testability. The validation engine in `input_validation/core/validation_engine.py`
orchestrates both levels.

## Key Design Decisions

1. **Galaxy collections** -- Each domain is a standalone Ansible Galaxy collection
2. **Domain independence** -- Every domain works standalone; no cross-domain code imports
3. **Contract-based integration** -- Domains communicate via YAML contract files only
4. **BuildStream orchestration** -- GitLab pipeline automates the full deployment sequence
5. **Bare-metal execution** -- Playbooks run directly on RHEL hosts (no container required)
6. **Air-gap support** -- All package references account for Pulp-based local mirroring
7. **RHEL 10.x primary** -- OS-agnostic code for future Ubuntu support
8. **Tag-based execution** -- Each domain supports `--tags validate|prepare|build|cleanup|upgrade|rollback`

## Runtime Paths

| Path | Purpose |
|------|---------|
| `/opt/omnia/` | Shared runtime root for all domains |
| `/opt/omnia/input/<project>/` | Per-project input configuration |
| `/opt/omnia/output/<project>/` | Per-project output artifacts |
| `/opt/omnia/<domain>/log/` | Domain-specific logs |
| `/opt/omnia/.data/` | Internal metadata (upgrade locks, OIM state) |

## Related Documentation

- **Domain integration patterns**: `docs/design/domain-integration.md`
- **Mono-repo design**: `docs/design/omnia-domain-repo-design.md`
- **Test automation**: `docs/design/test-automation-design.md`
- **Code style guides**: `docs/code-style/`
- **Galaxy testing**: `docs/galaxy-testing-guide.md`
- **Per-domain docs**: `src/<domain>/docs/`
