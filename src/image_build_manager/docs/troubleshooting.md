# Troubleshooting Guide

## Common Issues

### 1. repo_status.yml not found

```
repo_status.yml not found at .../repo_status.yml
```

**Fix**: Copy sample file and edit with actual URLs:
```bash
mkdir -p /opt/omnia/repo_manager/output/project_default
cp samples/repo_manager_output/repo_status.yml \
   /opt/omnia/repo_manager/output/project_default/
vi /opt/omnia/repo_manager/output/project_default/repo_status.yml
```

---

### 2. No x86_64 functional groups found

```
No functional groups found for the target architecture.
```

**Fix** (config mode): Ensure `input/project_default/package_groups.yml` has at least
one functional group defined with a matching `_x86_64` or `_aarch64` suffix:
```yaml
functional_groups:
  slurm_node_x86_64:
    packages:
      - munge
      - slurm-slurmd
```

**Fix** (catalog mode): Ensure the catalog JSON at `CATALOG_FILE_PATH` contains
functional layers ending with `_x86_64` or `_aarch64`.

---

### 3. Systemd directory does not exist

```
fatal: Destination directory /etc/containers/systemd does not exist
```

**Fix**: Ensure the `prepare` tag ran on the correct host (`oim` group).
The `deploy_minio` and `deploy_registry` roles create this directory automatically.

---

### 4. Repo manager certificate not found

```
Repo manager certificate not found at .../pulp_webserver.crt
```

**Fix**: Cert path comes from `repo_status.yml`. Options:
- Run `repo_manager` first so the cert exists
- Leave `server_crt` empty in `repo_status.yml` to skip cert validation

---

### 5. Compute image builds skipped / `_orchestrator_cmds` undefined

```
No compute image groups resolved for x86_64 — skipping compute builds
```
or:
```
'_orchestrator_cmds' is undefined
```

**Cause**: `compute_images_dict` is empty — no compute functional groups were resolved.

**Fix** (catalog mode): Verify the catalog JSON contains non-baseos functional layers
for the target architecture. The `parse_catalog` module classifies layers by their
**name prefix**: layers starting with `baseos` are base OS; all others are compute.
If all layers are named `baseos_*`, no compute groups will be resolved.

**Fix** (config mode): Ensure `package_groups.yml` contains entries in
`functional_groups` dict with architecture-matching keys (e.g. `slurm_node_x86_64`).
Functional groups are now derived from `package_groups.yml` keys — no separate list
in `image_build_config.yml` is needed.

---

### 6. Package not found during build

```
No match for argument: <package-name>
```

**Fix**: The RPM name in `functional_group_packages.yml` is not in any repo:
- Fix the package name
- Add the missing repo to `repo_status.yml`
- Sync the package in repo_manager

---

### 7. Registry TLS error

```
http: server gave HTTP response to HTTPS client
```

**Fix**: The local registry uses HTTP. If `regctl` defaults to HTTPS:
```bash
/usr/local/bin/regctl registry set --tls disabled <registry_ip>:5000
```

---

### 8. DNS resolution failure

```
dial tcp: lookup <hostname>.vm.cluster: no such host
```

**Fix**: Ensure `SYSTEM_ADMIN_NIC_IPV4` is set correctly:
```bash
export SYSTEM_ADMIN_NIC_IPV4=<your_admin_ip>
```

---

## Log Locations

| Log | Path |
|-----|------|
| Validation logs | `<OMNIA_DATA_PATH>/image_build_manager/log/<project>/` |
| Ansible playbook logs | `/var/log/omnia/image_build_manager/` |

---

## Debug Commands

```bash
# Verbose validation (no side effects)
cd playbooks
ansible-playbook image_build_manager.yml --tags validate -vvv

# Check package_groups.yml functional groups
grep -A2 'functional_groups:' /opt/omnia/image_build_manager/input/project_default/package_groups.yml

# Dry-run validation
ansible-playbook image_build_manager.yml --tags validate --check
```
