# Provision Roles Overview

This directory contains Ansible roles for the Omnia node provisioning process. Each role handles a specific aspect of cluster node provisioning, configuration, and service deployment.

## Active Roles

### 1. **configure_ochami**
Configures OpenCHAMI (Open Composable HPC Architecture Management Interface) for node management. Creates groups, sets up Boot Script Service (BSS), and configures cloud-init for node provisioning.

**Key Functions**:
- SMD group creation and management
- BSS boot parameter configuration
- Cloud-init template generation
- Node metadata management

[View Detailed README](./configure_ochami/README.md)

---

### 2. **provision_validations**
Validates all node provision-related configuration files and inputs before the provision process begins. Acts as a gatekeeper to prevent misconfigured deployments.

**Key Functions**:
- Provision input file validation
- Software configuration consistency checks
- Mapping file validation
- Telemetry configuration validation
- Hosts file updates

[View Detailed README](./provision_validations/README.md)

---

### 3. **telemetry**
Configures telemetry services for comprehensive HPC cluster monitoring, including iDRAC telemetry streaming and LDMS (Lightweight Distributed Metric Service).

**Key Functions**:
- iDRAC telemetry streamer deployment
- LDMS sampler/aggregator/storage configuration
- Kafka and time-series database setup
- Service cluster telemetry infrastructure

[View Detailed README](./telemetry/README.md)

---

### 4. **k8s_config**
Creates Kubernetes configuration files for the service cluster and stores them in NFS-shared storage for access by service cluster nodes.

**Key Functions**:
- Kubernetes manifest generation
- Helm chart values file creation
- ConfigMap and Secret generation
- RBAC resource definitions
- NFS-based configuration management

[View Detailed README](./k8s_config/README.md)

---

### 5. **nfs_client**
Configures NFS client mounts on cluster nodes based on their functional roles. Intelligently filters and mounts only relevant NFS shares.

**Key Functions**:
- Role-based NFS mount filtering (Slurm, Kubernetes)
- NFS client package installation
- Mount point creation and configuration
- fstab management for persistent mounts
- Bolt-on storage support

[View Detailed README](./nfs_client/README.md)

---

### 6. **openldap**
Configures OpenLDAP connection parameters for centralized authentication and user management.

**Key Functions**:
- LDAP search base extraction from domain
- LDAP bind DN construction
- Connection type configuration (LDAP/LDAPS)
- Server IP and credentials setup
- Variable preparation for other roles

[View Detailed README](./openldap/README.md)

---

### 7. **slurm_config**
Configures Slurm workload manager settings and creates necessary directory structures on NFS.

**Key Functions**:
- Slurm node identification by role
- Shared directory structure creation
- State, spool, and log directory setup
- Configuration file preparation
- Support for HA Slurm deployments

[View Detailed README](./slurm_config/README.md)

---

## Role Execution Order

Typical provision workflow role sequence:

1. **provision_validations** - Validate all inputs
2. **nfs_client** - Mount NFS shares (if needed early)
3. **openldap** - Setup LDAP connection parameters
4. **k8s_config** - Generate Kubernetes configurations
5. **slurm_config** - Setup Slurm directories and configuration
6. **telemetry** - Deploy telemetry infrastructure
7. **configure_ochami** - Configure node provisioning
8. **nfs_client** - Mount role-specific NFS shares

---

## Common Variables

### Configuration Files
All roles reference these common configuration files:
- `omnia_config.yml`: Main cluster configuration
- `omnia_config_credentials.yml`: Sensitive credentials
- `software_config.json`: Software stack definitions
- `storage_config.yml`: NFS and storage settings
- `telemetry_config.yml`: Telemetry settings (if enabled)

### Network Configuration
- Admin network: Primary management network
- BMC network: IPMI/Redfish access
- Compute network: High-performance interconnect
- Data network: External connectivity

### Node Categories
- **Control Plane**: Kubernetes masters, Slurm controllers
- **Compute**: Workload execution nodes
- **Login**: User access nodes
- **Service**: Infrastructure services (monitoring, storage)

---

## Dependencies

### Prerequisites
- NFS server configured and accessible
- OpenCHAMI installed (for node provisioning)
- Kubernetes cluster (for service deployments)

### Network Requirements
- All nodes accessible via admin network
- NFS server reachable from all nodes
- DNS resolution configured
- Firewall rules allow required ports

---

## Integration Points

### With Other Omnia Playbooks
- **Prerequisite**: Run after base infrastructure setup
- **Followed By**: Node provisioning, workload deployment
- **Integrates With**: Control plane, monitoring, security

### With External Systems
- **OpenCHAMI**: Node lifecycle management
- **Kubernetes**: Service orchestration
- **Slurm**: Workload management
- **OpenLDAP**: User authentication
- **NFS**: Shared storage

