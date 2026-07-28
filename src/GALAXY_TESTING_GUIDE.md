# Omnia Galaxy Collections — End-to-End Testing Guide

Complete test sequence for `omnia.discovery` and `omnia.orchestrator` collections,
from Galaxy install to executing every playbook and play.

---

## Prerequisites

```bash
# Ansible core >= 2.14
ansible --version

# Python >= 3.9
python3 --version
```

---

## Step 1: Install Collections from Galaxy

```bash
# Install both collections (use --force to re-install)
ansible-galaxy collection install omnia.discovery --force
ansible-galaxy collection install omnia.orchestrator --force

# Verify installation
ansible-galaxy collection list | grep omnia
# Expected output:
#   omnia.discovery       2.2.0
#   omnia.orchestrator    2.2.0
```

Collections are installed to: `~/.ansible/collections/ansible_collections/omnia/`

Set convenience variables for the rest of this guide:
```bash
DISCOVERY_HOME=~/.ansible/collections/ansible_collections/omnia/discovery
ORCHESTRATOR_HOME=~/.ansible/collections/ansible_collections/omnia/orchestrator
```

---

## Step 2: Prepare Input Files

### Discovery Input

```bash
# Create discovery input directory
mkdir -p /opt/omnia/input/project_default/discovery

# Copy default input templates from collection
cp $DISCOVERY_HOME/input/discovery_config.yml /opt/omnia/input/project_default/discovery/
cp $DISCOVERY_HOME/input/network_spec.yml     /opt/omnia/input/project_default/discovery/

# Edit discovery_config.yml — set your OME IP
vi /opt/omnia/input/project_default/discovery/discovery_config.yml
#   enable_bmc_discovery: true
#   ome_ip: "192.168.1.100"
```

### Orchestrator Input

```bash
# Create orchestrator input directory
mkdir -p /opt/omnia/input/project_default/orchestrator

# Copy default input templates from collection
cp $ORCHESTRATOR_HOME/input/orchestrator_config.yml     /opt/omnia/input/project_default/orchestrator/
cp $ORCHESTRATOR_HOME/input/network_spec.yml            /opt/omnia/input/project_default/orchestrator/
cp $ORCHESTRATOR_HOME/input/omnia_config.yml            /opt/omnia/input/project_default/orchestrator/
cp $ORCHESTRATOR_HOME/input/pxe_mapping_file.csv        /opt/omnia/input/project_default/orchestrator/
cp $ORCHESTRATOR_HOME/input/security_config.yml         /opt/omnia/input/project_default/orchestrator/
cp $ORCHESTRATOR_HOME/input/storage_config.yml          /opt/omnia/input/project_default/orchestrator/
cp $ORCHESTRATOR_HOME/input/high_availability_config.yml /opt/omnia/input/project_default/orchestrator/
cp $ORCHESTRATOR_HOME/input/additional_cloud_init.yml   /opt/omnia/input/project_default/orchestrator/

# Edit orchestrator_config.yml — set your cluster config
vi /opt/omnia/input/project_default/orchestrator/orchestrator_config.yml

# Edit pxe_mapping_file.csv — populate with discovered nodes
vi /opt/omnia/input/project_default/orchestrator/pxe_mapping_file.csv
```

### Create OIM Metadata (required by orchestrator)

```bash
mkdir -p /opt/omnia/.data
cat > /opt/omnia/.data/oim_metadata.yml << 'EOF'
---
oim_metadata: {}
EOF
```

---

## Step 3: Module Resolution Tests

Verify all collection modules are resolvable by Ansible.

### Discovery Modules (5)

```bash
ansible-doc omnia.discovery.validate_discovery_config
ansible-doc omnia.discovery.validate_credentials
ansible-doc omnia.discovery.ome_server_inventory
ansible-doc omnia.discovery.generate_pxe_mapping
ansible-doc omnia.discovery.generate_discovery_report
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
ansible-doc -t callback omnia.orchestrator.omnia_default
```

**Pass criteria:** Each command shows module/plugin documentation without errors.

---

## Step 4: Syntax Check All Playbooks

### Discovery (3 playbooks)

```bash
cd $DISCOVERY_HOME

ansible-playbook discovery.yml --syntax-check
ansible-playbook playbooks/validate_discovery.yml --syntax-check
ansible-playbook playbooks/discovery_credentials.yml --syntax-check
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

## Step 5: Discovery — Individual Play Execution

### 5.1 Validate Only (no OME needed)

Runs: setup → L1/L2 config validation.  
Requires: `discovery_config.yml` in input dir.

```bash
cd $DISCOVERY_HOME
ansible-playbook discovery.yml --tags validate
```

**Expected:** `Discovery configuration validation passed.`

### 5.2 Credential Management Only

Runs: setup → credential prompt/encrypt.  
No OME needed. Will prompt for OME username/password if `enable_bmc_discovery: true`.

```bash
cd $DISCOVERY_HOME
ansible-playbook playbooks/discovery_credentials.yml
```

**Expected:** Credential file created/updated at `/opt/omnia/input/project_default/discovery/discovery_credentials.yml`

### 5.3 Full OME Discovery (requires live OME)

Runs: setup → validate → credentials → OME inventory → PXE mapping → report.  
Requires: OME appliance reachable at configured `ome_ip`.

```bash
cd $DISCOVERY_HOME
ansible-playbook discovery.yml -e "discovery_mechanism=ome"
```

**Expected outputs:**
- `/opt/omnia/output/project_default/discovery/bmc_pxe_mapping_file.csv`
- `/opt/omnia/output/project_default/discovery/bmc_discovery_report_<timestamp>.csv`

### 5.4 Full Discovery with Verbose

```bash
cd $DISCOVERY_HOME
ansible-playbook discovery.yml -e "discovery_mechanism=ome" -vv
```

### 5.5 Custom Project Name

```bash
cd $DISCOVERY_HOME
ansible-playbook discovery.yml -e "discovery_mechanism=ome" -e "project_name=my_cluster"
# Reads:  /opt/omnia/input/my_cluster/discovery/
# Writes: /opt/omnia/output/my_cluster/discovery/
```

---

## Step 6: Orchestrator — Individual Play Execution

### 6.1 Validate Only (no cluster needed)

Runs: setup → L1/L2 config validation → functional groups generation.  
Requires: `orchestrator_config.yml` + `pxe_mapping_file.csv` in input dir.

```bash
cd $ORCHESTRATOR_HOME
ansible-playbook orchestrator.yml --tags validate
```

**Expected:** `Orchestrator configuration validation passed.`

### 6.2 Validate via Sub-Playbook

```bash
cd $ORCHESTRATOR_HOME
ansible-playbook playbooks/validate_orchestrator.yml
```

### 6.3 Credential Management Only

Runs: setup → credential prompt/encrypt for all services.  
Prompts for: OpenCHAMI admin, Kubernetes, Slurm, OpenLDAP, and conditional credentials (UFM, VAST).

```bash
cd $ORCHESTRATOR_HOME
ansible-playbook playbooks/orchestrator_credentials.yml
```

**Expected:** Credential file created/updated at `/opt/omnia/input/project_default/orchestrator/omnia_config_credentials.yml`

### 6.4 Prepare OIM (requires OIM host)

Runs: setup → validate → credentials → deploy OpenCHAMI containers on OIM.  
Requires: OIM host accessible (or localhost in container mode).

```bash
cd $ORCHESTRATOR_HOME
ansible-playbook orchestrator.yml --tags prepare
```

### 6.5 Prepare via Sub-Playbook

```bash
cd $ORCHESTRATOR_HOME
ansible-playbook playbooks/prepare_orchestrator.yml
```

### 6.6 PXE Boot Only

Runs: setup → PXE boot orchestration.  
Requires: OpenCHAMI deployed, nodes in `pxe_mapping_file.csv`.

```bash
cd $ORCHESTRATOR_HOME
ansible-playbook orchestrator.yml --tags pxe
```

### 6.7 Provision Nodes (requires live cluster)

Runs: setup → Kubernetes, Slurm, telemetry, mounts, LDAP configuration.  
Requires: Cluster nodes SSH-accessible.

```bash
cd $ORCHESTRATOR_HOME
ansible-playbook orchestrator.yml --tags provision
```

### 6.8 Full End-to-End

Runs everything: setup → validate → credentials → prepare → PXE → provision.

```bash
cd $ORCHESTRATOR_HOME
ansible-playbook orchestrator.yml
ansible-playbook orchestrator.yml -vv  # verbose
```

### 6.9 Cleanup

Tears down orchestrator resources.

```bash
cd $ORCHESTRATOR_HOME
ansible-playbook orchestrator.yml --tags cleanup
ansible-playbook playbooks/cleanup_orchestrator.yml  # sub-playbook
```

### 6.10 Upgrade

Runs upgrade workflow for existing deployments.

```bash
cd $ORCHESTRATOR_HOME
ansible-playbook orchestrator.yml --tags upgrade
ansible-playbook playbooks/upgrade_orchestrator.yml  # sub-playbook
```

### 6.11 Rollback

Rolls back a failed upgrade.

```bash
cd $ORCHESTRATOR_HOME
ansible-playbook orchestrator.yml --tags rollback
ansible-playbook playbooks/rollback_orchestrator.yml  # sub-playbook
```

---

## Step 7: Tag Reference

### Discovery Tags

| Tag | Plays Executed | Infra Required |
|-----|---------------|----------------|
| `validate` | setup + validation | None |
| `discovery` | setup + validate + creds + OME discovery | OME |
| `cleanup` | setup + cleanup | None |
| *(no tag)* | All plays | OME + `-e discovery_mechanism=ome` |

### Orchestrator Tags

| Tag | Plays Executed | Infra Required |
|-----|---------------|----------------|
| `validate` | setup + validation + functional groups | None |
| `prepare` | setup + validate + creds + OpenCHAMI deploy | OIM host |
| `pxe` | setup + PXE boot orchestration | OIM + OpenCHAMI |
| `provision` | setup + K8s/Slurm/telemetry/mounts/LDAP | Cluster nodes |
| `cleanup` | setup + teardown | None |
| `upgrade` | setup + upgrade workflow | Existing deployment |
| `rollback` | setup + rollback | After failed upgrade |
| *(no tag)* | All plays | Full infrastructure |

### Invalid Tag Combinations

- Discovery: `discovery` + `cleanup`
- Orchestrator: `prepare` + `cleanup`, `provision` + `cleanup`, `pxe` + `cleanup`, `prepare` + `upgrade`, `provision` + `upgrade`, `cleanup` + `upgrade`, `upgrade` + `rollback`

---

## Step 8: Quick Smoke Test (copy-paste)

Minimal test requiring no infrastructure — validates install, modules, syntax, and config validation:

```bash
# Install
ansible-galaxy collection install omnia.discovery omnia.orchestrator --force

# Set paths
DISCOVERY_HOME=~/.ansible/collections/ansible_collections/omnia/discovery
ORCHESTRATOR_HOME=~/.ansible/collections/ansible_collections/omnia/orchestrator

# Module resolution (spot check)
ansible-doc omnia.discovery.validate_discovery_config | head -3
ansible-doc omnia.orchestrator.validate_orchestrator_config | head -3

# Syntax check
cd $DISCOVERY_HOME && ansible-playbook discovery.yml --syntax-check
cd $ORCHESTRATOR_HOME && ansible-playbook orchestrator.yml --syntax-check

# Validate (needs input files in /opt/omnia/input/project_default/)
cd $DISCOVERY_HOME && ansible-playbook discovery.yml --tags validate
cd $ORCHESTRATOR_HOME && ansible-playbook orchestrator.yml --tags validate
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Could not find or access .../vars/common_vars.yml` | Running sub-playbook with old `playbook_dir` refs | Rebuild & reinstall collection with `role_path` fixes |
| `oim_metadata.yml not found` | First run, no OIM metadata yet | Create empty: `mkdir -p /opt/omnia/.data && echo -e "---\noim_metadata: {}" > /opt/omnia/.data/oim_metadata.yml` |
| `Module not found` | Collection not in `collections_paths` | Check `ansible-galaxy collection list`, reinstall if missing |
| `Permission denied (SSH)` | OIM group connecting via SSH instead of local | Verify `ansible_connection: local` on `oim` host group |
| `discovery_config.yml not found` | Input files not copied to project dir | Copy from `$COLLECTION_HOME/input/` to `/opt/omnia/input/project_default/<domain>/` |
