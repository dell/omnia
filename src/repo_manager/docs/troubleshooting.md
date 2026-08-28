# Troubleshooting Guide

## Environment Variable Issues

### 1. "OMNIA_DATA_PATH not set"

**Error**:
```
Path not found: /repo_manager/input/project_default/
```

**Fix**: Set the `OMNIA_DATA_PATH` environment variable:
```bash
export OMNIA_DATA_PATH=/opt/omnia
# Or use custom path
export OMNIA_DATA_PATH=/custom/omnia
```

**Verification**:
```bash
echo $OMNIA_DATA_PATH
ls -la $OMNIA_DATA_PATH/repo_manager/
```

---

### 2. "OMNIA_PROJECT_NAME not set"

**Error**:
```
Project directory not found: project_default
```

**Fix**: Set the `OMNIA_PROJECT_NAME` environment variable:
```bash
export OMNIA_PROJECT_NAME=my_project
# Or use default
export OMNIA_PROJECT_NAME=project_default
```

**Verification**:
```bash
echo $OMNIA_PROJECT_NAME
ls -la $OMNIA_DATA_PATH/repo_manager/input/$OMNIA_PROJECT_NAME/
```

---

### 3. "Input files not found in custom path"

**Error**:
```
repo_manager_config.yml not found in /custom/omnia/repo_manager/input/my_project/
```

**Fix**: Ensure both environment variables are set correctly:
```bash
export OMNIA_DATA_PATH=/custom/omnia
export OMNIA_PROJECT_NAME=my_project
# Verify input files exist
ls -la $OMNIA_DATA_PATH/repo_manager/input/$OMNIA_PROJECT_NAME/
```

---

## Policy Configuration Issues

### 4. "Invalid repo_config value"

**Error**:
```
Invalid repo_config value: 'invalid'. Must be 'always' or 'partial'
```

**Fix**: Update `repo_manager_config.yml` with valid value:
```yaml
repo_config: "partial"  # Options: always | partial
```

---

### 5. "Invalid caching_policy value"

**Error**:
```
Invalid caching_policy value: 'invalid'. Must be true or false
```

**Fix**: Update `repo_manager_config.yml` with valid value:
```yaml
caching_policy: true    # Options: true (on_demand) | false (immediate)
```

---

### 6. "Per-repo caching override not working"

**Error**:
```
Repository not using expected caching behavior
```

**Fix**: Check policy prioritization order:
1. Per-repo `caching` field (highest priority)
2. Global `caching_policy` setting
3. Default behavior based on `repo_config` setting

**Example Configuration**:
```yaml
# Global policy
caching_policy: true  # on_demand by default

# Per-repo override
additional_repos:
  custom_repo:
    url: "http://custom-repo.example.com/rhel10/"
    caching: false  # This repo uses immediate sync, overriding global policy
```

---

### 7. "additional_repos configuration not working"

**Error**:
```
Additional repositories not being processed
```

**Fix**: Verify `additional_repos` configuration format:
```yaml
additional_repos:
  custom_repo:
    url: "http://custom-repo.example.com/rhel10/"
    caching: false  # Optional: override global caching_policy
```

---

### 8. "user_repos configuration not working"

**Error**:
```
User repositories not being processed
```

**Fix**: Verify `user_repos` configuration format:
```yaml
user_repos:
  custom_rhel_repo:
    url: "http://my-repo.example.com/rhel10/"
```

---

## Common Issues

### 9. "Pulp CLI not found"

**Error**:
```
/usr/bin/env: 'python3': No such file or directory
or
pulp: command not found
```

**Fix**: Ensure Python 3 is installed and the Pulp CLI symlink exists:
```bash
which python3
ls -la /usr/local/bin/pulp
```

If the symlink doesn't exist, run the deploy tag:
```bash
cd /root/oim-multi-repo/omnia/src/repo_manager/playbooks
ansible-playbook repo_manager.yml --tags deploy
```

---

### 10. "Pulp server not responding"

**Error**:
```
Failed to connect to Pulp server at https://localhost:24817
```

**Fix**: Check if Pulp containers are running:
```bash
podman ps -a | grep pulp
```

If containers are not running, redeploy Pulp:
```bash
ansible-playbook repo_manager.yml --tags deploy
```

Check Pulp service status:
```bash
podman logs pulp-api
podman logs pulp-content
```

---

### 11. "repo_manager_config.yml validation failed"

**Error**:
```
Validation failed for repo_manager_config.yml
```

**Fix**: Check the JSON schema validation:
```bash
cd /root/oim-multi-repo/omnia/src/repo_manager/playbooks
ansible-playbook repo_manager.yml --tags precheck -vvv
```

Common issues:
- Missing required fields
- Invalid URL formats
- Invalid architecture specification
- Malformed YAML syntax

---

### 12. "software_config.json not found"

**Error**:
```
software_config.json not found at input/project_default/software_config.json
```

**Fix**: Ensure the file exists in the correct location (using environment variables):
```bash
export OMNIA_DATA_PATH=${OMNIA_DATA_PATH:-/opt/omnia}
export OMNIA_PROJECT_NAME=${OMNIA_PROJECT_NAME:-project_default}
ls -la $OMNIA_DATA_PATH/repo_manager/input/$OMNIA_PROJECT_NAME/software_config.json
```

Copy the sample if needed:
```bash
cp samples/software_config.json input/$OMNIA_PROJECT_NAME/
```

---

### 13. "Download failed for repository"

**Error**:
```
Failed to download content from https://...
```

**Fix**: Check network connectivity and URL validity:
```bash
curl -I https://repository-url/
```

If using custom user repositories, verify the URLs in `repo_manager_config.yml`.

Check firewall rules:
```bash
firewall-cmd --list-all
```

---

### 14. "Podman container failed to start"

**Error**:
```
Error: container creation failed
```

**Fix**: Check Podman status and available resources:
```bash
podman info
systemctl status podman
```

Check disk space:
```bash
df -h
```

Check container logs:
```bash
podman logs <container_name>
```

---

### 15. "SSL/TLS certificate error"

**Error**:
```
SSL: CERTIFICATE_VERIFY_FAILED
or
unable to get local issuer certificate
```

**Fix**: Ensure Pulp certificates are properly configured (using environment variables):
```bash
export OMNIA_DATA_PATH=${OMNIA_DATA_PATH:-/opt/omnia}
ls -la $OMNIA_DATA_PATH/repo_manager/pulp_config/settings/certs/
```

If using self-signed certificates, ensure the CA cert is trusted.

---

### 16. "repo_status.yml generation failed"

**Error**:
```
Failed to generate repo_status.yml
```

**Fix**: Check Pulp distribution status:
```bash
/usr/local/bin/pulp rpm distribution list
/usr/local/bin/pulp file distribution list
/usr/local/bin/pulp python distribution list
```

Ensure distributions exist before generating status:
```bash
ansible-playbook repo_manager.yml --tags download
ansible-playbook repo_manager.yml --tags status
```

---

### 17. "Permission denied on log directory"

**Error**:
```
Permission denied: /var/log/omnia/repo_manager/
```

**Fix**: Ensure the log directory exists with proper permissions (using environment variables):
```bash
export OMNIA_DATA_PATH=${OMNIA_DATA_PATH:-/opt/omnia}
mkdir -p $OMNIA_DATA_PATH/repo_manager/log/
chmod 755 $OMNIA_DATA_PATH/repo_manager/log/
```

---

### 18. "Cleanup failed to remove containers"

**Error**:
```
Failed to remove Pulp containers
```

**Fix**: Manually remove containers:
```bash
podman stop pulp-api pulp-content pulp-worker
podman rm pulp-api pulp-content pulp-worker
```

Then run cleanup again:
```bash
ansible-playbook repo_manager.yml --tags cleanup
```

---

## Debug Tips

### Check loaded variables

```bash
cd /root/oim-multi-repo/omnia/src/repo_manager/playbooks
ansible-playbook repo_manager.yml --tags precheck -vvv
```

### Verify Pulp distributions

```bash
/usr/local/bin/pulp rpm distribution list
/usr/local/bin/pulp file distribution list
/usr/local/bin/pulp python distribution list
```

### Check download status

```bash
export OMNIA_DATA_PATH=${OMNIA_DATA_PATH:-/opt/omnia}
export OMNIA_PROJECT_NAME=${OMNIA_PROJECT_NAME:-project_default}
cat $OMNIA_DATA_PATH/repo_manager/output/$OMNIA_PROJECT_NAME/status.csv
```

### Verify repo_status.yml

```bash
export OMNIA_DATA_PATH=${OMNIA_DATA_PATH:-/opt/omnia}
export OMNIA_PROJECT_NAME=${OMNIA_PROJECT_NAME:-project_default}
cat $OMNIA_DATA_PATH/repo_manager/output/$OMNIA_PROJECT_NAME/repo_status.yml
```

### Check Pulp container logs

```bash
podman logs pulp-api
podman logs pulp-content
podman logs pulp-worker
```

### Run only validation (no side effects)

```bash
cd /root/oim-multi-repo/omnia/src/repo_manager/playbooks
ansible-playbook repo_manager.yml --tags precheck --check
```

### Test specific tags

```bash
# Test only Pulp deployment
ansible-playbook repo_manager.yml --tags deploy

# Test only download
ansible-playbook repo_manager.yml --tags download

# Test only status generation
ansible-playbook repo_manager.yml --tags status
```

---

## Log Locations

| Log Type | Location |
|----------|----------|
| Ansible playbook logs | `$OMNIA_DATA_PATH/repo_manager/log/repo_manager.log` |
| Pulp API logs | `podman logs pulp-api` |
| Pulp content logs | `podman logs pulp-content` |
| Pulp worker logs | `podman logs pulp-worker` |
| Download status | `$OMNIA_DATA_PATH/repo_manager/output/$OMNIA_PROJECT_NAME/status.csv` |

**Default locations** (when environment variables are not set):
| Log Type | Default Location |
|----------|-----------------|
| Ansible playbook logs | `/var/log/omnia/repo_manager/repo_manager.log` |
| Download status | `/opt/omnia/repo_manager/output/project_default/status.csv` |

---

## Performance Issues

### Slow downloads

**Fix**: Adjust caching policy in `repo_manager_config.yml`:
```yaml
caching_policy: false    # Use immediate sync for faster downloads
# Or use per-repo override for specific repos
additional_repos:
  custom_repo:
    url: "http://custom-repo.example.com/rhel10/"
    caching: false  # Immediate sync for this repo
```

### High memory usage

**Fix**: Reduce concurrency or check available system resources:
```bash
free -h
```

### Disk space issues

**Fix**: Clean up old Pulp content:
```bash
ansible-playbook repo_manager.yml --tags cleanup
```

Check disk usage (using environment variables):
```bash
export OMNIA_DATA_PATH=${OMNIA_DATA_PATH:-/opt/omnia}
df -h
du -sh $OMNIA_DATA_PATH/repo_manager/pulp_config/
du -sh /var/lib/containers/
```

---

## Network Issues

### DNS resolution failures

**Fix**: Check DNS configuration:
```bash
cat /etc/resolv.conf
nslookup repository-url
```

### Firewall blocking connections

**Fix**: Check firewall rules and open required ports:
```bash
firewall-cmd --list-all
firewall-cld --add-port=24817/tcp --permanent
firewall-cmd --reload
```

### Proxy configuration

**Fix**: If using a proxy, configure environment variables (HTTPS only):
```bash
export https_proxy=https://proxy.example.com:8080
export no_proxy=localhost,127.0.0.1
```

---

## Recovery Procedures

### Complete reset

If you need to completely reset Repo Manager:

```bash
# Set environment variables
export OMNIA_DATA_PATH=${OMNIA_DATA_PATH:-/opt/omnia}
export OMNIA_PROJECT_NAME=${OMNIA_PROJECT_NAME:-project_default}

# 1. Cleanup
ansible-playbook repo_manager.yml --tags cleanup

# 2. Remove output directory
rm -rf $OMNIA_DATA_PATH/repo_manager/output/$OMNIA_PROJECT_NAME/

# 3. Redeploy
ansible-playbook repo_manager.yml --tags deploy

# 4. Download content
ansible-playbook repo_manager.yml --tags download

# 5. Generate status
ansible-playbook repo_manager.yml --tags status
```

### Restore from backup

If you have a backup of `repo_status.yml`:

```bash
# Set environment variables
export OMNIA_DATA_PATH=${OMNIA_DATA_PATH:-/opt/omnia}
export OMNIA_PROJECT_NAME=${OMNIA_PROJECT_NAME:-project_default}

# Restore the file
cp backup/repo_status.yml $OMNIA_DATA_PATH/repo_manager/output/$OMNIA_PROJECT_NAME/

# Verify it's valid
ansible-playbook repo_manager.yml --tags precheck
```
