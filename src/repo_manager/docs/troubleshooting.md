# Troubleshooting Guide

## Common Issues

### 1. "Pulp CLI not found"

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

### 2. "Pulp server not responding"

**Error**:
```
Failed to connect to Pulp server at http://localhost:24817
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

### 3. "repo_manager_config.yml validation failed"

**Error**:
```
Validation failed for repo_manager_config.yml
```

**Fix**: Check the JSON schema validation:
```bash
cd /root/oim-multi-repo/omnia/src/repo_manager/playbooks
ansible-playbook repo_manager.yml --tags validate -vvv
```

Common issues:
- Missing required fields
- Invalid URL formats
- Invalid architecture specification
- Malformed YAML syntax

---

### 4. "software_config.json not found"

**Error**:
```
software_config.json not found at input/project_default/software_config.json
```

**Fix**: Ensure the file exists in the correct location:
```bash
ls -la /root/oim-multi-repo/omnia/src/repo_manager/input/project_default/software_config.json
```

Copy the sample if needed:
```bash
cp samples/software_config.json input/project_default/
```

---

### 5. "Download failed for repository"

**Error**:
```
Failed to download content from http://...
```

**Fix**: Check network connectivity and URL validity:
```bash
curl -I http://repository-url/
```

If using custom user repositories, verify the URLs in `repo_manager_config.yml`.

Check firewall rules:
```bash
firewall-cmd --list-all
```

---

### 6. "Podman container failed to start"

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

### 7. "SSL/TLS certificate error"

**Error**:
```
SSL: CERTIFICATE_VERIFY_FAILED
or
unable to get local issuer certificate
```

**Fix**: Ensure Pulp certificates are properly configured:
```bash
ls -la /opt/omnia/pulp_config/pulp/settings/certs/
```

If using self-signed certificates, ensure the CA cert is trusted.

---

### 8. "repo_status.yml generation failed"

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

### 9. "Permission denied on log directory"

**Error**:
```
Permission denied: /var/log/omnia/repo_manager/
```

**Fix**: Ensure the log directory exists with proper permissions:
```bash
mkdir -p /var/log/omnia/repo_manager/
chmod 755 /var/log/omnia/repo_manager/
```

---

### 10. "Cleanup failed to remove containers"

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
ansible-playbook repo_manager.yml --tags validate -vvv
```

### Verify Pulp distributions

```bash
/usr/local/bin/pulp rpm distribution list
/usr/local/bin/pulp file distribution list
/usr/local/bin/pulp python distribution list
```

### Check download status

```bash
cat /opt/omnia/repo_manager/output/<project_name>/status.csv
```

### Verify repo_status.yml

```bash
cat /opt/omnia/repo_manager/output/<project_name>/repo_status.yml
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
ansible-playbook repo_manager.yml --tags validate --check
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
| Ansible playbook logs | `/var/log/omnia/repo_manager/repo_manager.log` |
| Pulp API logs | `podman logs pulp-api` |
| Pulp content logs | `podman logs pulp-content` |
| Pulp worker logs | `podman logs pulp-worker` |
| Download status | `/opt/omnia/repo_manager/output/<project_name>/status.csv` |

---

## Performance Issues

### Slow downloads

**Fix**: Increase concurrency in `repo_manager_config.yml`:
```yaml
pulp_concurrency: 8  # Increase from default 4
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

Check disk usage:
```bash
df -h
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

**Fix**: If using a proxy, configure environment variables:
```bash
export http_proxy=http://proxy.example.com:8080
export https_proxy=http://proxy.example.com:8080
```

---

## Recovery Procedures

### Complete reset

If you need to completely reset Repo Manager:

```bash
# 1. Cleanup
ansible-playbook repo_manager.yml --tags cleanup

# 2. Remove output directory
rm -rf /opt/omnia/repo_manager/output/<project_name>/

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
# Restore the file
cp backup/repo_status.yml /opt/omnia/repo_manager/output/<project_name>/

# Verify it's valid
ansible-playbook repo_manager.yml --tags validate
```
