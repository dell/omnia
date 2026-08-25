# Omnia Pipeline

GitLab CI/CD pipeline for automated Omnia deployment and cleanup on remote clusters.

## Directory Structure

```
test/pipeline/
├── .gitlab-ci.yml              # Parent pipeline (multi-cluster trigger)
├── .gitlab-ci-cluster.yml      # Child pipeline (per-cluster stages)
├── README.md                   # This file
└── clusters/
    ├── cluster1/
    │   ├── cluster.env         # Cluster 1 connection details
    │   ├── Inputs/
    │   │   ├── omnia.env       # Omnia environment config
    │   │   ├── repo_manager/   # repo_manager input files
    │   │   │   ├── repo_manager_config.yml
    │   │   │   ├── repo_manager_config_credentials.yml
    │   │   │   └── repo_manager_endpoint_config.yml
    │   │   └── image_build_manager/  # image_build_manager input files
    │   │       ├── image_build_config.yml
    │   │       ├── image_build_credentials.yml
    │   │       └── package_groups.yml
    │   └── catalogs/
    │       └── catalog_rhel.json
    ├── cluster2/
    │   └── ...                 # Same structure
    └── cluster3/
        └── ...                 # Same structure
```

## Pipeline Stages

### 1. initialization
- Loads cluster configuration from `clusters/<name>/cluster.env`
- Validates input files (`Inputs/omnia.env`, cluster config)
- Tests SSH connectivity to the target cluster
- Writes `target.env` artifact for downstream stages

### 2. setup_environment
- Clones the Omnia repository on the target server
- Copies `Inputs/omnia.env` to the cloned repo at `src/main/omnia.env`
- Runs `./omnia.sh -s` to create the Python venv and install all dependencies
- Activates the venv via `source /opt/omnia/activate-omnia.sh`
- Reads `OMNIA_DATA_PATH` from the target environment
- Copies `catalogs/catalog_rhel.json` to `<OMNIA_DATA_PATH>/catalog/` on target
- Verifies the environment (Python version, pip packages, Ansible)

### 3. repo_manager
- Reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the target
- Copies all files from `Inputs/repo_manager/` to `<OMNIA_DATA_PATH>/repo_manager/input/<project>/` on target
- Encrypts `repo_manager_config_credentials.yml` with `ansible-vault` (auto-generates vault key)
- Runs `ansible-playbook repo_manager.yml` from the cloned omnia repo

### 4. image_build_manager
- Reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the target
- Copies all files from `Inputs/image_build_manager/` to `<OMNIA_DATA_PATH>/image_build_manager/input/<project>/` on target
- Encrypts `image_build_credentials.yml` with `ansible-vault` (auto-generates vault key)
- Runs `ansible-playbook image_build_manager.yml` from the cloned omnia repo

### 5. clean_up
- Activates the omnia venv on the target
- Runs `./omnia.sh --cleanup --all` for a full Omnia cleanup
- Removes venv, system env files, and all data at `/opt/omnia/`

## Configuration

### GitLab CI/CD Variables

Set these in **Project > Settings > CI/CD > Variables**:

| Variable | Description | Example |
|---|---|---|
| `CLUSTERS` | Comma-separated list of clusters to run | `cluster1,cluster2` |
| `CLUSTER1_TARGET_PASS` | SSH password for cluster1 (masked) | `*****` |
| `CLUSTER2_TARGET_PASS` | SSH password for cluster2 (masked) | `*****` |
| `CLUSTER3_TARGET_PASS` | SSH password for cluster3 (masked) | `*****` |
| `OMNIA_REPO` | Git URL for the Omnia repository | `https://github.com/dell/omnia.git` |
| `OMNIA_BRANCH` | Branch to clone | `main` |
| `OMNIA_INSTALL_PATH` | Full path where omnia is installed on target | `/root/omnia` |

### Cluster Configuration

Each cluster has a `cluster.env` file in `clusters/<name>/`:

```bash
CLUSTER_NAME="cluster1"
TARGET_IP="10.0.0.1"           # Target cluster IP
TARGET_USER="root"             # SSH user
TARGET_PASS="${CLUSTER1_TARGET_PASS}"  # Resolved from GitLab CI/CD variable
```

### Omnia Environment

Edit `clusters/<name>/Inputs/omnia.env` with the correct settings for each target cluster:

```bash
SYSTEM_ADMIN_NIC_IPV4=<target_admin_ip>
SYSTEM_HOSTNAME=<target_hostname>
SYSTEM_DOMAIN_NAME=<target_domain>
```

Each cluster has its own `Inputs/omnia.env` file, allowing different configurations per cluster.

## Adding a New Cluster

1. Create `clusters/<name>/` directory
2. Create `clusters/<name>/cluster.env` with connection details
3. Create `clusters/<name>/Inputs/omnia.env` with Omnia environment config
4. Create `clusters/<name>/Inputs/repo_manager/` with repo_manager input files
5. Create `clusters/<name>/Inputs/image_build_manager/` with image_build_manager input files
6. Create `clusters/<name>/catalogs/` directory and add catalog files
7. Add `<NAME>_TARGET_PASS` as a masked GitLab CI/CD variable
8. Add a `trigger_cluster_<name>` job in `.gitlab-ci.yml`
9. Add the cluster name to the `CLUSTERS` CI/CD variable

## Target Paths (on remote server)

All paths are derived from `OMNIA_DATA_PATH` (default: `/opt/omnia`) and
`OMNIA_PROJECT_NAME` (default: `project_default`) read from `omnia.env`:

| Pipeline Source | Target Destination |
|---|---|
| `catalogs/catalog_rhel.json` | `<OMNIA_DATA_PATH>/catalog/catalog_rhel.json` |
| `Inputs/repo_manager/*` | `<OMNIA_DATA_PATH>/repo_manager/input/<project>/` |
| `Inputs/image_build_manager/*` | `<OMNIA_DATA_PATH>/image_build_manager/input/<project>/` |

## Credential Encryption

Credential files are automatically encrypted with `ansible-vault` during
the pipeline. For each credential file:
1. A random vault key is generated (`openssl rand -base64 32`)
2. The key is stored alongside the credential file (e.g., `.repo_manager_config_credentials_key`)
3. The credential file is encrypted with `ansible-vault encrypt`
4. The playbook decrypts it at runtime using the vault key

Credential files:
- `repo_manager_config_credentials.yml` -> vault key: `.repo_manager_config_credentials_key`
- `image_build_credentials.yml` -> vault key: `.image_build_credentials_key`

## Email Notifications

The pipeline can send execution reports via email. To enable email notifications:

1. Set the following GitLab CI/CD variables:
   - `EMAIL_RECIPIENTS` - Comma-separated list of recipient emails
   - `EMAIL_SENDER` - From address for emails
   - `SMTP_SERVER` - SMTP relay host
   - `SMTP_PORT` - SMTP relay port (default: 25)
   - `SMTP_USER` - SMTP username (optional, for authenticated relay)
   - `SMTP_PASSWORD` - SMTP password (optional, for authenticated relay)

2. The `email_notification` stage runs after `clean_up` and sends a pipeline summary report

3. Email notifications are non-fatal - pipeline success is not affected if email fails

## Venv Activation

The omnia venv is activated in every stage via the default `before_script`,
which sources `/opt/omnia/activate-omnia.sh` on the target server. This
ensures all stages have access to the Omnia Python environment, Ansible,
and installed collections.
