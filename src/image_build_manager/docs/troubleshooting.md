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
No x86_64 functional groups found in functional_group_config.
```

**Fix**: Enable at least one group in `input/project_default/image_build_config.yml`:
```yaml
functional_groups:
  - name: "os_x86_64"
  - name: "slurm_node_x86_64"
```

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

### 5. Package not found during build

```
No match for argument: <package-name>
```

**Fix**: The RPM name in `functional_group_packages.yml` is not in any repo:
- Fix the package name
- Add the missing repo to `repo_status.yml`
- Sync the package in repo_manager

---

### 6. Registry TLS error

```
http: server gave HTTP response to HTTPS client
```

**Fix**: The local registry uses HTTP. If `regctl` defaults to HTTPS:
```bash
/usr/local/bin/regctl registry set --tls disabled <registry_ip>:5000
```

---

### 7. DNS resolution failure

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

# Check functional groups output
cat /opt/omnia/image_build_manager/output/project_default/.data/functional_groups_config.yml

# Dry-run validation
ansible-playbook image_build_manager.yml --tags validate --check
```
