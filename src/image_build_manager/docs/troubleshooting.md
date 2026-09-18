# Troubleshooting Guide

## Common Issues

### 1. repo_status.yml not found

```
repo_status.yml not found at .../repo_status.yml
```

**Fix**: Copy sample file and edit with actual URLs:
```bash
mkdir -p /opt/omnia/repo_manager/output/project_default
cp src/image_build_manager/samples/repo_manager_output/repo_status.yml \
   /opt/omnia/repo_manager/output/project_default/
vi /opt/omnia/repo_manager/output/project_default/repo_status.yml
```

Run these commands from the repository root, or use an absolute source path.
Replace every `{{ admin_nic_ip }}` placeholder with a literal hostname or IP;
the reference template is not schema-valid until those URLs are resolved.

---

### 2. No x86_64 functional groups found

```
No functional groups found for the target architecture.
```

**Fix** (config mode): Ensure the staged
`<OMNIA_DATA_PATH>/image_build_manager/input/<project>/package_groups.yml` has
at least one functional group with the target `_x86_64` or `_aarch64` suffix:
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

**Fix**: Create the Quadlet directory, then rerun `prepare`:

```bash
sudo install -d -m 0755 /etc/containers/systemd
ansible-playbook image_build_manager.yml --tags prepare
```

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
No compute image groups resolved for x86_64 -- skipping compute builds
```
or:
```
'_orchestrator_cmds' is undefined
```

**Cause**: `compute_images_dict` is empty -- no compute functional groups were resolved.

**Fix** (catalog mode): Verify the catalog JSON contains non-baseos functional layers
for the target architecture. The `parse_catalog` module classifies layers by their
**name prefix**: layers starting with `baseos` are base OS; all others are compute.
If all layers are named `baseos_*`, no compute groups will be resolved.

**Fix** (config mode): Ensure `package_groups.yml` contains entries in
`functional_groups` dict with architecture-matching keys (e.g. `slurm_node_x86_64`).
Functional groups are now derived from `package_groups.yml` keys -- no separate list
in `image_build_config.yml` is needed.

---

### 6. Package not found during build

```
No match for argument: <package-name>
```

**Fix**: In config mode, check `package_groups.yml`; in catalog mode, check the
package entry in the catalog. The requested RPM is not in any configured repo:
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

**Fix**: Verify that `SYSTEM_HOSTNAME` and `SYSTEM_DOMAIN_NAME` form the
hostname used in the repository URLs and that it resolves to
`SYSTEM_ADMIN_NIC_IPV4`:
```bash
getent hosts "${SYSTEM_HOSTNAME}.${SYSTEM_DOMAIN_NAME}"
```

Correct DNS or `/etc/hosts` if it does not resolve, and confirm that
`SYSTEM_ADMIN_NIC_IPV4` is assigned to the intended local interface.

---

### 9. Registry verification failure (catalog ID mismatch)

```
FAILED: registry verification for rhel-<group>_omnia_<catalog_id>
```

**Cause**: When a catalog is updated between builds, previously cached images
retain the old catalog ID. Verification reconstructs the image name using the
current catalog ID, which does not match.

**Fix**: The build flow uses prefix matching (`rhel-<group>_omnia_*`) instead
of exact name matching. If you see this error on an older version, rebuild the
images with `force_rebuild: true` in `image_build_config.yml`.

---

### 10. AArch64 SSH setup failure

```
Failed to establish passwordless SSH to <aarch64_ip>
```

**Cause**: SSH keypair missing, incorrect password, or firewall blocking port 22.

**Fix**:
1. Verify SSH keypair exists on OIM: `ls /root/.ssh/id_rsa`
2. Check `aarch64_ssh_password` in `image_build_credentials.yml`
3. Verify SSH service on aarch64 node: `systemctl status sshd`
4. Check firewall: `firewall-cmd --list-ports`
5. Manual fix:
```bash
ssh-keygen -t rsa -b 4096
ssh-copy-id root@<aarch64_ip>
```

---

### 11. AArch64 builder image pull failure

```
Unable to pull the aarch64 image builder image from both repo manager and upstream registry
```

**Cause**: Neither the repo manager (Pulp) nor the selected builder's upstream
registry could provide the image.

**Fix**:
- Ensure repo manager has synced the builder image, or
- Ensure the aarch64 node can access the configured upstream registry

---

### 12. AArch64 regctl not found

```
regctl binary could not be obtained for the aarch64 node
```

**Cause**: The regctl binary could not be copied from OIM or downloaded.

**Fix**:
- Check the staged ARM binary on OIM at
  `$OMNIA_DATA_PATH/image_build_manager/aarch64/regctl-linux-arm64`; the
  aarch64 build flow attempts to download it before connecting to the node
- Ensure the aarch64 node is reachable via SSH from OIM
- Ensure either OIM or the aarch64 node can reach GitHub releases, or manually
  install `regctl` on the aarch64 node:
```bash
curl -L -o /usr/local/bin/regctl \
  https://github.com/regclient/regclient/releases/latest/download/regctl-linux-arm64
chmod 755 /usr/local/bin/regctl
```

---

## Log Locations

| Log | Path |
|-----|------|
| Validation logs | `<OMNIA_DATA_PATH>/image_build_manager/log/<project>/` |
| Ansible playbook logs | `/var/log/omnia/image_build_manager/` |
| Compute image build logs | `<OMNIA_DATA_PATH>/image_build_manager/log/<project>/*_compute_image.log` |

---

## Debug Commands

```bash
# Verbose validation (writes validation logs and may ensure runtime directories)
cd playbooks
ansible-playbook image_build_manager.yml --tags validate -vvv

# Check package_groups.yml functional groups
grep -A2 'functional_groups:' /opt/omnia/image_build_manager/input/project_default/package_groups.yml

# Parse and syntax-check the top-level playbook without executing tasks
ansible-playbook image_build_manager.yml --syntax-check

# Check MinIO status
systemctl status minio.service

# Check registry status
systemctl status registry.service

# List S3 buckets
s3cmd ls

# Check regctl config
cat ~/.regctl/config.json

# Verify registry images
/usr/local/bin/regctl tag ls <registry_ip>:5000/<image_name>
```
