# Omnia CI/CD Pipeline — Quick Start Guide

Get your Omnia CI/CD pipeline up and running in 5 minutes.

> **Prerequisites:** You must have completed the [OpenBao Setup](OPENBAO_SETUP.md) before proceeding.

---

## Step 1: Prepare Your Configuration

Create or edit `pipeline_config.yml` in the pipeline directory:

```yaml
global:
  clusters: "cluster1"
  omnia:
    repo: "https://github.com/dell/omnia.git"
    branch: "main"
    install_path: "/root/omnia"
  vault:
    server_url: "https://<OPENBAO_IP>:8200"
    auth_role: "gitlab-role"
    secret_path: "secret/data/omnia"

cluster1:
  connection:
    target_ip: "10.43.0.100"
    target_user: "root"
  pipeline:
    pipeline_mode: "default"
    domains: "default"
    test_mode: "true"
```

See [Configuration Reference](CONFIGURATION.md) for all available options.

---

## Step 2: Install Dependencies

```bash
pip install pyyaml requests
```

---

## Step 3: Create the GitLab Project

Run the setup script to create the project and upload all files:

```bash
python3 setup_gitlab_project.py --create \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline \
    --config pipeline_config.yml
```

The script will:
- ✅ Create the GitLab project
- ✅ Upload pipeline files (`.gitlab-ci.yml`, `.gitlab-ci-cluster.yml`)
- ✅ Upload input file templates
- ✅ Create CI/CD variables from your config

---

## Step 4: Set Cluster Connection Details in GitLab

Go to your GitLab project > **Settings** > **CI/CD** > **Variables** and add:

| Variable | Value | Type |
|---|---|---|
| `CLUSTER1_TARGET_IP` | Your target server IP | Variable |
| `CLUSTER1_TARGET_USER` | SSH username (usually `root`) | Variable |
| `CLUSTER1_TARGET_PASS` | SSH password | Variable (masked) |

---

## Step 5: Edit Input Files

In your GitLab repository, navigate to `clusters/cluster1/inputs/` and edit:

- **`omnia.env`** — Omnia environment settings
- **`repo_manager/`** — Pulp repository configuration
- **`orchestrator/`** — Kubernetes configuration
- **`image_build_manager/`** — Image builder settings
- **`telemetry/`** — Monitoring configuration

---

## Step 6: Trigger the Pipeline

Go to **CI/CD > Pipelines > Run pipeline** in your GitLab project.

The pipeline will:
1. Clone Omnia on your target server
2. Set up the Python virtual environment
3. Deploy all selected domains
4. Run validation tests
5. Send a summary report

---

## What's Next?

- **[Pipeline Modes & Domains](PIPELINE_MODES.md)** — Learn how to customize deployments
- **[Configuration Reference](CONFIGURATION.md)** — Explore all available settings
- **[Troubleshooting](TROUBLESHOOTING.md)** — Solve common issues

---

## Common Tasks

### Redeploy a single domain

Edit `pipeline_config.yml`:

```yaml
pipeline:
  pipeline_mode: "deploy"
  domains: "repo_manager"
```

Then run the pipeline again.

### Clean up and start fresh

```yaml
pipeline:
  pipeline_mode: "cleanup"
  domains: "default"
```

### Deploy to multiple servers

See [Multi-Cluster Deployment](CONFIGURATION.md#multi-cluster-deployment).

### Rotate credentials

Update the secret in OpenBao — the next pipeline run picks it up automatically:

```bash
bao kv put secret/omnia/repo_manager \
    pulp_username="admin" \
    pulp_password="<new-password>"
```

---

## Need Help?

- Check [Troubleshooting](TROUBLESHOOTING.md) for common issues
- Review [Pipeline Modes](PIPELINE_MODES.md) for deployment strategies
- See [Configuration Reference](CONFIGURATION.md) for all options
