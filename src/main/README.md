# Omnia Main Directory

This directory contains the core entry points for the Omnia Infrastructure Manager (OIM) deployment:

- **`omnia.sh`** — Setup and initialization script
- **`omnia-cli`** — Status and diagnostics CLI
- **`omnia.env`** — Environment configuration file

---

## Quick Start

```bash
# 1. Configure environment
vi omnia.env  # Set OMNIA_ADMIN_NIC_IP and other required variables

# 2. Set up Python virtual environment (one-time)
./omnia.sh --setup-venv  # or: ./omnia.sh -s

# 3. Check domain status
./omnia-cli status

# 4. Run domain playbooks
source /opt/omnia/venv/bin/activate
cd ../<domain>/playbooks
ansible-playbook <playbook>.yml --tags validate,prepare,build
```

---

## Documentation

- **[README_omnia.sh.md](README_omnia.sh.md)** — Detailed omnia.sh setup script documentation
- **[README_omnia-cli.md](README_omnia-cli.md)** — Detailed omnia-cli diagnostics CLI documentation
- **[README_omnia.env.md](README_omnia.env.md)** — Detailed omnia.env environment configuration documentation

---

## Directory Structure

After setup, Omnia creates the following directory structure:

```
/opt/omnia/
├── venv/                          # Python virtual environment
│   ├── bin/
│   │   ├── activate
│   │   ├── ansible
│   │   ├── ansible-playbook
│   │   └── python
│   └── lib/
├── log/                           # Shared log directory
│   ├── repo_manager/
│   ├── image_build_manager/
│   ├── discovery/
│   ├── orchestrator/
│   ├── telemetry/
│   └── build_stream/
├── .data/                         # Internal data
├── repo_manager/                  # Repo manager output
│   └── output/
│       └── project_default/
│           ├── repo_status.yml
│           └── functional_group_packages.yml
├── image_build_manager/          # Image build output
│   ├── output/
│   │   └── project_default/
│   │       └── build_status.yml
│   └── log/
├── discovery/                     # Discovery output
│   ├── output/
│   └── log/
├── orchestrator/                 # Orchestrator output
│   ├── output/
│   └── log/
├── telemetry/                     # Telemetry output
│   ├── output/
│   └── log/
└── build_stream/                 # Build stream output
    ├── output/
    └── log/
```

---

## Running Domain Playbooks

After venv setup, run domain playbooks directly:

```bash
# Activate the venv
source /opt/omnia/venv/bin/activate

# Navigate to a domain's playbook directory
cd ../repo_manager/playbooks

# Run the playbook
ansible-playbook repo_manager.yml

# Run with specific tags
ansible-playbook repo_manager.yml --tags validate,prepare
```

### Common Tags

Most domain playbooks support these tags:

- `validate` — Schema and runtime validation
- `prepare` — Deploy prerequisites (containers, services)
- `build` — Main build/execution phase
- `cleanup` — Stop services and remove artifacts
- `upgrade` - Upgrade of the domain
- `rollback` - Rollback of the domain

---

## Multi-Project Deployments

To manage multiple projects (e.g., `dev`, `staging`, `prod`):

```bash
# Set different project names
OMNIA_PROJECT_NAME=dev ./omnia-cli status
OMNIA_PROJECT_NAME=staging ./omnia-cli status
OMNIA_PROJECT_NAME=prod ./omnia-cli status

# Or use the --project flag
./omnia-cli status --project dev
./omnia-cli status --project staging
./omnia-cli status --project prod
```

Each project will have its own input/output directories under each domain.

---

## Version Information

Check your Omnia version:

```bash
./omnia-cli version
```

