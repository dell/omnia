# GitLab Ansible Automation

Ansible roles and playbooks to deploy or integrate GitLab for the Omnia catalog pipeline.

## Directory Tree

```text
build_stream/gitlab/
├── README.md
├── gitlab_config.yaml                    # User input file (edit before running)
├── gitlab.yml                            # Unified playbook (hosted / existing)
├── inventory/
│   └── hosts.ini                         # Target host for hosted mode
├── roles/
│   ├── gitlab_passwordless_ssh/
│   │   ├── tasks/
│   │   │   ├── main.yml                  # Entry point
│   │   │   ├── generate_keypair.yml
│   │   │   ├── authorize_key.yml
│   │   │   └── validate_ssh.yml
│   │   └── vars/
│   │       └── main.yml
│   ├── hosted_gitlab/
│   │   ├── tasks/
│   │   │   ├── main.yml                  # Entry point
│   │   │   ├── validate_prerequisites.yml
│   │   │   ├── install_packages.yml
│   │   │   ├── configure_firewall.yml
│   │   │   ├── create_directories.yml
│   │   │   ├── generate_tls_certs.yml
│   │   │   ├── install_gitlab.yml
│   │   │   ├── configure_gitlab.yml
│   │   │   ├── deploy_runner.yml
│   │   │   └── display_summary.yml
│   │   ├── templates/
│   │   │   ├── gitlab.rb.j2
│   │   │   └── san.cnf.j2
│   │   └── vars/
│   │       └── main.yml
│   └── external_gitlab/
│       ├── tasks/
│       │   ├── main.yml                  # Entry point
│       │   ├── validate_connectivity.yml
│       │   ├── create_project.yml
│       │   ├── create_trigger.yml
│       │   ├── push_ci_files.yml
│       │   └── display_summary.yml
│       ├── files/
│       │   └── .gitlab-ci.yml            # CI/CD template pushed to repo
│       └── vars/
│           └── main.yml
```

## Usage

### Running the unified playbook

The recommended entry point is now **`gitlab/gitlab.yml`**, which chooses the correct
roles based on `gitlab_deployment_mode` in `gitlab_config.yaml`.

```bash
cd build_stream/gitlab
ansible-playbook gitlab.yml
```

### Case 1 – Hosted GitLab (fresh install on a server)

1. Edit `gitlab_config.yaml`:
   ```yaml
   gitlab_deployment_mode: "hosted"
   gitlab_host: "gitlab.example.com"   # or IP
   ```
2. Add the target host to `inventory/hosts.ini`:
   ```ini
   [gitlab_server]
   10.3.0.4 ansible_user=root
   ```
3. Run the unified playbook (see above). The `gitlab_passwordless_ssh` role runs first
   to generate `/root/.ssh/omnia_gitlab` and push the public key to the target host.

### Case 2 – Existing GitLab (already running)

1. Edit `gitlab_config.yaml`:
   ```yaml
   gitlab_deployment_mode: "existing"
   gitlab_external_url: "https://gitlab.example.com"
   gitlab_api_token: "<your-pat>"
   ```
2. Run the unified playbook (see above). This targets `localhost` only.

## What Each Playbook Does

| Playbook | Mode | Actions |
| --- | --- | --- |
| `gitlab.yml` | hosted or existing | Hosted: bootstraps SSH, installs RPM packages + Podman, generates TLS certs, installs GitLab CE Omnibus, configures `gitlab.rb`, starts runner container. Existing: validates API connectivity, creates project + trigger, pushes `.gitlab-ci.yml` from role files |

## Role Structure

Each role follows the standard Omnia Ansible role layout (matching `discovery/roles/`):

- **`tasks/main.yml`** — entry point using `include_tasks` to split logic into sub-files
- **`tasks/<subtask>.yml`** — individual task files for each stage
- **`vars/main.yml`** — role-specific default variables
- **`templates/`** — Jinja2 templates (e.g. `gitlab.rb.j2`, `san.cnf.j2`)
- **`files/`** — static files (e.g. `.gitlab-ci.yml`)
