# Omnia Orchestrator

Orchestrator is an Ansible Galaxy collection that deploys OpenCHAMI services, configures Slurm and Kubernetes clusters, manages networking and storage, and orchestrates PXE boot for HPC and AI cluster provisioning. It is the primary domain responsible for node lifecycle management and cluster configuration.

## Overview

Orchestrator automates cluster provisioning and configuration by:

- Deploying OpenCHAMI services (Metadata Service, Boot Service, CoreDHCP, CoreDNS, CoreSMD)
- Optionally deploying OpenLDAP for authentication
- Configuring Slurm workload manager for HPC workloads
- Configuring Kubernetes for service workloads
- Managing network configuration (bonding, segmentation, DNS, DHCP)
- Configuring storage (NFS mounts, PowerScale, VAST)
- Orchestrating iDRAC PXE boot for physical node provisioning
- Managing node registration and completion verification
- Reconciling OpenCHAMI state with persistent Service Tag-to-XNAME identity

## Key Responsibilities

Orchestrator is the **primary provisioning domain** that:
- Deploys and configures OpenCHAMI infrastructure services
- Configures cluster-wide networking and storage
- Provisions Slurm or Kubernetes clusters
- Bootstraps physical nodes via PXE
- Manages node lifecycle from boot to registration
- Reconciles hardware identity through SMD Hardware Inventory

Orchestrator does **not**:
- Build OS images (Image Build Manager responsibility)
- Discover hardware (Discovery responsibility)
- Synchronize repositories (Repository Manager responsibility)
- Deploy telemetry (Telemetry responsibility)

## Prerequisites

| Requirement | Supported version | Source |
|-------------|-------------------|--------|
| OIM operating system | RHEL 10.x or Rocky Linux 10.x | Omnia platform support matrix |
| Python | 3.12+ | Omnia virtual environment |
| Ansible | `ansible-core` 2.20+ | `requirements.txt` |
| Podman | 5.0+ | OpenCHAMI and OpenLDAP service deployment |
| `ansible.posix` | 2.0.0 | `requirements.yml` |
| `ansible.utils` | 5.1.1 | `requirements.yml` |
| `community.general` | 10.3.0 | `requirements.yml` |
| `dellemc.openmanage` | 10.0.3+ | `requirements.yml` |

## Quick Start

```bash
# From the repository root
cd src/main

# Configure the host, create the shared virtual environment, and stage inputs
vi omnia.env
sudo ./omnia.sh -s
source /etc/profile.d/omnia-env.sh

# Edit the staged project inputs
vi "$ORCHESTRATOR_DATA_PATH/input/$OMNIA_PROJECT_NAME/orchestrator_config.yml"
vi "$ORCHESTRATOR_DATA_PATH/input/$OMNIA_PROJECT_NAME/pxe_mapping_file.csv"

# Validate, prepare services, and provision nodes
./omnia.sh --run orchestrator --tags validate
./omnia.sh --run orchestrator --tags prepare
./omnia.sh --run orchestrator --tags provision
```

## Tags

| Tag | Description |
|-----|-------------|
| `precheck` | Generate functional groups and validate inputs, parameters, and boot images |
| `validate` | Validate project input files without contacting deployed services |
| `credentials` | Collect or reuse encrypted Orchestrator credentials |
| `prepare` | Collect credentials, deploy services, and validate readiness |
| `deploy` | Deploy OpenCHAMI and enabled OpenLDAP services and validate them |
| `provision` | Reconcile OpenCHAMI data, configure nodes, and validate provisioning |
| `execute` | Run provisioning and conditional PXE boot |
| `validate-deployment` | Validate deployed OpenCHAMI and OpenLDAP services |
| `pxeboot` | Run iDRAC PXE boot and optional node/cloud-init verification |
| `verify_node_registration` | Verify pending manually or hypervisor-booted nodes over SSH without iDRAC |
| `cleanup` | Remove enabled components and credentials by default |
| `cleanup_credentials` | Remove only the Orchestrator credential file and vault key |

## Node Registration

After PXE boot, verify and record node completion with:

```bash
./omnia.sh --run orchestrator --tags verify_node_registration
```

For nodes whose PXE attempt failed, boot manually or through hypervisor, then run verification. The external verifier requires a boot newer than the persisted lifecycle status.

## Cleanup

```bash
# Full cleanup (removes components and credentials)
sudo ./omnia.sh --run orchestrator --tags cleanup

# Preserve credentials for redeployment
sudo ./omnia.sh --run orchestrator --tags cleanup \
  -e cleanup_credentials=false
```

## Documentation

- [Orchestrator Documentation](https://omnia.readthedocs.io/en/latest/HowTo/orchestrator/index.html)
- [Architecture](docs/architecture.md)
- [Hardware Identity Mapping](docs/hardware-identity-mapping.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Input Contract](docs/contracts/input-contract.md)
- [Output Contract](docs/contracts/output-contract.md)

## License

Apache-2.0
