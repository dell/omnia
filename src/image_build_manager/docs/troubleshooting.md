# Troubleshooting Guide

## Common Issues

### 1. "repo_status.yml not found"

**Error**:
```
repo_status.yml not found at .../repo_manager_output/repo_status.yml.
Copy repo_status.yml from your repo_manager output into .../repo_manager_output/.
```

**Fix**: Copy `repo_status.yml` from your repo_manager host to the runtime path:
```bash
mkdir -p /opt/omnia/repo_manager/output/project_default
cp src/image_build_manager/samples/repo_manager_output/repo_status.yml \
   /opt/omnia/repo_manager/output/project_default/
```
Edit the file with your actual Pulp server URLs and cert paths.

---

### 2. "Unexpected property 'functional_groups'"

**Error**:
```
image_build_config.yml: Unexpected property 'functional_groups'
```

**Fix**: The JSON schema at `plugins/module_utils/image_build_validation/schema/image_build_config.json`
must include the `functional_groups` property. This was added in the standalone migration.
Verify the schema file has the `functional_groups` entry.

---

### 3. "No x86_64 functional groups found"

**Error**:
```
No x86_64 functional groups found in functional_group_config.
Please ensure x86_64 functional groups are defined in image_build_config.yml.
```

**Fix**: Uncomment at least one `x86_64` functional group in
`input/project_default/image_build_config.yml`:

```yaml
functional_groups:
  - name: "os_x86_64"
  - name: "slurm_node_x86_64"
```

---

### 4. "Destination directory /etc/containers/systemd does not exist"

**Error** during MinIO or Registry deployment:
```
fatal: Destination directory /etc/containers/systemd does not exist
```

**Fix**: The `deploy_minio` and `deploy_registry` roles create this directory
automatically. If you see this error, ensure the `prepare` tag ran on the
correct host (the `oim` host group).

---

### 5. Pulp certificate not found

**Error**:
```
Pulp certificate not found at /opt/omnia/pulp/settings/certs/pulp_webserver.crt.
Ensure repo_manager has been run and the certificate exists on this host.
```

**Fix**: The playbook reads the cert path directly from `repo_status.yml`.
Ensure `repo_manager` has been run and the certificate exists at the path
specified in `repo_status.yml → repo_manager.certificates.server_crt`.

---

### 6. Package not found during image build

**Error** in OpenCHAMI build log:
```
No match for argument: <package-name>
```

**Fix**: The RPM package name in `functional_group_packages.yml` does not exist
in any of the Pulp repos defined in `repo_status.yml`. Either:
- Fix the package name in `functional_group_packages.yml`
- Add the missing repo to `repo_status.yml → rpm_repos`
- Sync the package in your Pulp server

---

### 7. Validation log location

Validation logs are written to:
```
/opt/omnia/image_build_manager/log/<project_name>/
```

Ansible playbook logs are in:
```
/opt/omnia/image_build_manager/log/playbooks/
```

---

### 8. Registry TLS error ("http: server gave HTTP response to HTTPS client")

**Error**:
```
failed to list repositories for 10.x.x.x:5000: Get "https://10.x.x.x:5000/v2/_catalog":
http: server gave HTTP response to HTTPS client
```

**Fix**: The local container registry runs HTTP (not HTTPS). `regctl` defaults to
HTTPS for IP addresses. The playbook now auto-configures this, but if you see
this error, run:
```bash
/usr/local/bin/regctl registry set --tls disabled <registry_ip>:5000
```

---

### 9. DNS resolution failure for registry hostname

**Error**:
```
dial tcp: lookup <hostname>.vm.cluster on <dns>:53: no such host
```

**Fix**: In standalone mode, the playbook uses `admin_nic_ip` (IP address) for
the registry host. If you see DNS errors, ensure `OMNIA_ADMIN_NIC_IP` is set
correctly in `omnia.env`.

---

## Debug Tips

### Check loaded variables

```bash
cd src/image_build_manager/playbooks
ansible-playbook image_build_manager.yml --tags validate -vvv
```

### Verify functional groups were written

```bash
cat /opt/omnia/image_build_manager/output/project_default/.data/functional_groups_config.yml
```

### Check which packages will be installed

The `fetch_build_packages` role logs the count:
```
Standalone: 2 functional groups, 35 base packages
```

Use `-v` to see the full debug output.

### Run only validation (no side effects)

```bash
cd src/image_build_manager/playbooks
ansible-playbook image_build_manager.yml --tags validate --check
```

### Check omnia-cli status

```bash
./src/main/omnia-cli status
./src/main/omnia-cli repo-manager
./src/main/omnia-cli image-build
```
