# Omnia Galaxy Collections -- End-to-End Testing Guide

Testing guide for all Omnia Galaxy collections: `omnia.discovery`, `omnia.image_build`,
and `omnia.orchestrator`.

---

## Prerequisites

| Requirement | Minimum |
|------------|---------|
| Ansible | ansible-core 2.14+ |
| Python | 3.9+ |
| OS | RHEL 10.x / Rocky 10.x |

---

## Step 1: Install Collections

```bash
ansible-galaxy collection install omnia.discovery --force
ansible-galaxy collection install omnia.image_build --force
ansible-galaxy collection install omnia.orchestrator --force

# Verify
ansible-galaxy collection list | grep omnia
```

Set convenience variables:
```bash
DISCOVERY_HOME=~/.ansible/collections/ansible_collections/omnia/discovery
IMAGE_BUILD_HOME=~/.ansible/collections/ansible_collections/omnia/image_build
ORCHESTRATOR_HOME=~/.ansible/collections/ansible_collections/omnia/orchestrator
```

---

## Step 2: Module Resolution Tests

### Discovery Modules (5)

```bash
ansible-doc omnia.discovery.validate_discovery_config
ansible-doc omnia.discovery.validate_credentials
ansible-doc omnia.discovery.ome_server_inventory
ansible-doc omnia.discovery.generate_pxe_mapping
ansible-doc omnia.discovery.generate_discovery_report
```

### Image Build Modules (8)

```bash
ansible-doc omnia.image_build.validate_image_build_config
ansible-doc omnia.image_build.validate_system_environment
ansible-doc omnia.image_build.validate_yaml_schema
ansible-doc omnia.image_build.image_build_orchestrator
ansible-doc omnia.image_build.image_package_collector
ansible-doc omnia.image_build.base_image_package_collector
ansible-doc omnia.image_build.generate_functional_groups
ansible-doc omnia.image_build.functional_group_parser
```

### Orchestrator Modules (8)

```bash
ansible-doc omnia.orchestrator.validate_orchestrator_config
ansible-doc omnia.orchestrator.validate_credentials
ansible-doc omnia.orchestrator.fetch_credential_rule
ansible-doc omnia.orchestrator.generate_functional_groups
ansible-doc omnia.orchestrator.generate_xname_in_mapping_file
ansible-doc omnia.orchestrator.generate_argon2_password
ansible-doc omnia.orchestrator.slurm_conf
ansible-doc omnia.orchestrator.fetch_telemetry_status
```

### Callback Plugins

```bash
ansible-doc -t callback omnia.discovery.omnia_default
ansible-doc -t callback omnia.image_build.omnia_default
ansible-doc -t callback omnia.orchestrator.omnia_default
```

**Pass criteria:** Each command shows documentation without errors.

---

## Step 3: Syntax Check All Playbooks

### Discovery (3 playbooks)

```bash
cd $DISCOVERY_HOME
ansible-playbook discovery.yml --syntax-check
ansible-playbook playbooks/validate_discovery.yml --syntax-check
ansible-playbook playbooks/discovery_credentials.yml --syntax-check
```

### Image Build (8 playbooks)

```bash
cd $IMAGE_BUILD_HOME/playbooks
ansible-playbook image_build_manager.yml --syntax-check
ansible-playbook validate/validate_image_build_config.yml --syntax-check
ansible-playbook credentials/get_build_credentials.yml --syntax-check
ansible-playbook prepare/prepare_image_build_manager.yml --syntax-check
ansible-playbook build/build_image_x86_64.yml --syntax-check
ansible-playbook build/build_image_aarch64.yml --syntax-check
ansible-playbook cleanup/cleanup_image_build_manager.yml --syntax-check
ansible-playbook upgrade/upgrade_image_build_manager.yml --syntax-check
```

### Orchestrator (7 playbooks)

```bash
cd $ORCHESTRATOR_HOME
ansible-playbook orchestrator.yml --syntax-check
ansible-playbook playbooks/validate_orchestrator.yml --syntax-check
ansible-playbook playbooks/prepare_orchestrator.yml --syntax-check
ansible-playbook playbooks/orchestrator_credentials.yml --syntax-check
ansible-playbook playbooks/cleanup_orchestrator.yml --syntax-check
ansible-playbook playbooks/upgrade_orchestrator.yml --syntax-check
ansible-playbook playbooks/rollback_orchestrator.yml --syntax-check
```

**Pass criteria:** Each prints `playbook: <name>` with no errors.

---

## Step 4: Discovery -- Execution

### Validate Only (no OME needed)

```bash
cd $DISCOVERY_HOME
ansible-playbook discovery.yml --tags validate
```

### Credential Management

```bash
ansible-playbook playbooks/discovery_credentials.yml
```

### Full OME Discovery (requires live OME)

```bash
ansible-playbook discovery.yml -e "discovery_mechanism=ome"
```

### Custom Project Name

```bash
ansible-playbook discovery.yml -e "discovery_mechanism=ome" -e "project_name=my_cluster"
```

---

## Step 5: Image Build -- Execution

### Prepare Input

```bash
# Ensure repo_manager output exists (or copy sample files)
mkdir -p /opt/omnia/repo_manager/output/project_default
cp $IMAGE_BUILD_HOME/samples/repo_manager_output/repo_status.yml \
   /opt/omnia/repo_manager/output/project_default/
cp $IMAGE_BUILD_HOME/samples/repo_manager_output/functional_group_packages.yml \
   /opt/omnia/repo_manager/output/project_default/

# Copy input config
$IMAGE_BUILD_HOME/domain-init.sh
```

### Validate Only (no credentials)

```bash
cd $IMAGE_BUILD_HOME/playbooks
ansible-playbook image_build_manager.yml --tags validate
```

### Prepare (deploy MinIO + Registry)

```bash
ansible-playbook image_build_manager.yml --tags prepare
```

### Build OS Images

```bash
ansible-playbook image_build_manager.yml --tags build
```

### Cleanup

```bash
ansible-playbook image_build_manager.yml --tags cleanup
```

---

## Step 6: Orchestrator -- Execution

### Validate Only (no cluster needed)

```bash
cd $ORCHESTRATOR_HOME
ansible-playbook orchestrator.yml --tags validate
```

### Credential Management

```bash
ansible-playbook playbooks/orchestrator_credentials.yml
```

### Prepare OIM (requires OIM host)

```bash
ansible-playbook orchestrator.yml --tags prepare
```

### PXE Boot

```bash
ansible-playbook orchestrator.yml --tags pxe
```

### Provision Nodes (requires live cluster)

```bash
ansible-playbook orchestrator.yml --tags provision
```

### Full End-to-End

```bash
ansible-playbook orchestrator.yml
```

### Cleanup / Upgrade / Rollback

```bash
ansible-playbook orchestrator.yml --tags cleanup
ansible-playbook orchestrator.yml --tags upgrade
ansible-playbook orchestrator.yml --tags rollback
```

---

## Step 7: Tag Reference

### Discovery Tags

| Tag | Description | Infra Required |
|-----|-------------|----------------|
| `validate` | Config validation | None |
| `discovery` | Full OME discovery | OME |
| `cleanup` | Cleanup | None |

### Image Build Tags

| Tag | Description | Infra Required |
|-----|-------------|----------------|
| `precheck` | Environment precheck | None |
| `validate` | Config validation | None |
| `prepare` | Deploy MinIO + Registry | Podman |
| `build` / `execute` | Build OS images | Podman + S3 |
| `cleanup` | Remove services + artifacts | None |
| `upgrade` | Upgrade flow (placeholder) | Existing deployment |
| `rollback` | Rollback flow (placeholder) | After failed upgrade |

### Orchestrator Tags

| Tag | Description | Infra Required |
|-----|-------------|----------------|
| `validate` | Config validation | None |
| `prepare` | Deploy OpenCHAMI | OIM host |
| `pxe` | PXE boot orchestration | OIM + OpenCHAMI |
| `provision` | K8s/Slurm/telemetry/LDAP | Cluster nodes |
| `cleanup` | Teardown | None |
| `upgrade` | Upgrade workflow | Existing deployment |
| `rollback` | Rollback | After failed upgrade |

---

## Step 8: Quick Smoke Test

Minimal test requiring no infrastructure:

```bash
# Install
ansible-galaxy collection install omnia.discovery omnia.image_build omnia.orchestrator --force

# Set paths
DISCOVERY_HOME=~/.ansible/collections/ansible_collections/omnia/discovery
IMAGE_BUILD_HOME=~/.ansible/collections/ansible_collections/omnia/image_build
ORCHESTRATOR_HOME=~/.ansible/collections/ansible_collections/omnia/orchestrator

# Module resolution (spot check)
ansible-doc omnia.discovery.validate_discovery_config | head -3
ansible-doc omnia.image_build.validate_image_build_config | head -3
ansible-doc omnia.orchestrator.validate_orchestrator_config | head -3

# Syntax check
cd $DISCOVERY_HOME && ansible-playbook discovery.yml --syntax-check
cd $IMAGE_BUILD_HOME/playbooks && ansible-playbook image_build_manager.yml --syntax-check
cd $ORCHESTRATOR_HOME && ansible-playbook orchestrator.yml --syntax-check
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Module not found` | Collection not in path | `ansible-galaxy collection list`, reinstall if missing |
| `oim_metadata.yml not found` | First run, no metadata | `mkdir -p /opt/omnia/.data && echo -e "---\noim_metadata: {}" > /opt/omnia/.data/oim_metadata.yml` |
| `repo_status.yml not found` | repo_manager not run | Copy sample from `$IMAGE_BUILD_HOME/samples/repo_manager_output/` |
| `Permission denied (SSH)` | SSH instead of local | Verify `ansible_connection: local` on `oim` host group |
| `discovery_config.yml not found` | Input files not staged | Copy from `$COLLECTION_HOME/input/` to `/opt/omnia/input/project_default/<domain>/` |
