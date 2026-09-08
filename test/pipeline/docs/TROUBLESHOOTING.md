# Troubleshooting Guide

Common issues and solutions for the Omnia CI/CD pipeline.

---

## Pipeline Fails at Initialization

**Symptoms:** Pipeline fails immediately with SSH connection errors.

**Solutions:**

1. Verify SSH connectivity to the target server:
   ```bash
   ssh -v root@<TARGET_IP>
   ```

2. Check that `CLUSTER1_TARGET_IP`, `CLUSTER1_TARGET_USER`, and `CLUSTER1_TARGET_PASS` are set in GitLab CI/CD variables:
   - Go to **Settings > CI/CD > Variables**
   - Verify all three variables exist and have correct values

3. Verify firewall allows SSH (port 22):
   ```bash
   sudo firewall-cmd --list-ports
   ```

4. Check SSH service is running on target:
   ```bash
   sudo systemctl status sshd
   ```

---

## OpenBao Server is NOT Reachable

**Symptoms:** Pipeline fails with "OpenBao server is NOT reachable" message.

**Solutions:**

1. Verify `VAULT_SERVER_URL` is correct:
   - Should be in format: `https://<OPENBAO_IP>:8200`
   - Check in **Settings > CI/CD > Variables**

2. Check if OpenBao is running:
   ```bash
   sudo systemctl status openbao
   ```

3. Verify network connectivity from GitLab Runner to OpenBao host:
   ```bash
   curl -k https://<OPENBAO_IP>:8200/v1/sys/health
   ```

4. Check firewall rules on OpenBao host:
   ```bash
   sudo firewall-cmd --list-ports
   # Must include 8200/tcp
   ```

5. Verify OpenBao is unsealed:
   ```bash
   bao status
   # Should show: Sealed = false
   ```

---

## OpenBao Authentication Failed

**Symptoms:** Pipeline fails with "OpenBao authentication failed" or JWT validation errors.

**Solutions:**

1. Verify `oidc_discovery_url` matches your GitLab instance URL:
   ```bash
   bao read auth/jwt/config
   # oidc_discovery_url should match your GitLab URL
   ```

2. Verify `bound_audiences` in the role matches the OpenBao server URL:
   ```bash
   bao read auth/jwt/role/gitlab-role
   # bound_audiences should be: https://<OPENBAO_IP>:8200
   ```

3. If GitLab uses a self-signed certificate, verify `oidc_discovery_ca_pem` was set:
   ```bash
   bao read auth/jwt/config | grep oidc_discovery_ca_pem
   ```

4. Confirm GitLab version is 15.7+ (required for `id_tokens`):
   ```bash
   # In GitLab UI: Help > About GitLab
   ```

5. Check OpenBao logs:
   ```bash
   sudo journalctl -u openbao -n 50
   ```

---

## Failed to Fetch Secret

**Symptoms:** Pipeline fails with "Failed to fetch secret" or "secret not found" errors.

**Solutions:**

1. Verify the secret exists in OpenBao:
   ```bash
   bao kv get secret/omnia/repo_manager
   bao kv get secret/omnia/orchestrator
   # etc. for each domain
   ```

2. Check the policy path includes `/data/` for KV v2:
   ```bash
   bao policy read gitlab-policy
   # Should include: path "secret/data/omnia/*"
   ```

3. Verify `VAULT_SECRET_PATH` is set to `secret/data/omnia`:
   - Go to **Settings > CI/CD > Variables**
   - Check `VAULT_SECRET_PATH` value

4. Verify the domain name matches the secret path:
   - For repo_manager: `secret/omnia/repo_manager`
   - For orchestrator: `secret/omnia/orchestrator`
   - etc.

---

## Omnia venv Not Found

**Symptoms:** Pipeline fails with "Python venv not found" or similar errors.

**Solutions:**

The Python environment has not been created on the target. Either:

1. Run a `default` mode pipeline first (includes full setup):
   ```yaml
   pipeline:
     pipeline_mode: "default"
     domains: "default"
   ```

2. Or set `enable_setup: "true"` to force environment setup:
   ```yaml
   pipeline:
     pipeline_mode: "deploy"
     enable_setup: "true"
     domains: "repo_manager"
   ```

3. Or manually set up the environment on the target:
   ```bash
   ssh root@<TARGET_IP>
   cd /root/omnia
   bash omnia.sh -s
   ```

---

## Deploy Fails with Ansible Errors

**Symptoms:** Pipeline fails during domain deployment with Ansible playbook errors.

**Solutions:**

1. Check input files in `clusters/<name>/inputs/<domain>/`:
   - Go to your GitLab repository
   - Navigate to `clusters/cluster1/inputs/`
   - Verify all required files exist and have correct content

2. Enable verbose logging for detailed Ansible output:
   ```yaml
   pipeline:
     verbose: "true"
   ```
   This adds `-vvv` flag to Ansible commands.

3. Run a dry-run to see what would execute without making changes:
   ```yaml
   pipeline:
     dry_run: "true"
   ```

4. SSH into target and run the playbook manually to debug:
   ```bash
   ssh root@<TARGET_IP>
   cd /root/omnia
   source .venv/bin/activate
   ansible-playbook src/repo_manager/repo_manager.yml -vvv
   ```

5. Check Ansible inventory and variables:
   ```bash
   ssh root@<TARGET_IP>
   cat /root/omnia/test/pipeline/inventory.ini
   cat /root/omnia/test/pipeline/vars.yml
   ```

---

## Test Failures

**Symptoms:** Pipeline fails during test stages (test_repo_manager, test_orchestrator, etc.).

**Solutions:**

1. Check test configuration files:
   - Go to your GitLab repository
   - Navigate to `clusters/cluster1/inputs/test/<domain>/`
   - Verify test config files exist

2. Run tests manually on target:
   ```bash
   ssh root@<TARGET_IP>
   cd /root/omnia/test/repo_manager
   source .venv/bin/activate
   ./run_validation.sh fvt_repo_manager verify
   ```

3. Check test logs in the pipeline job output:
   - Go to **CI/CD > Pipelines > [Pipeline] > [Job]**
   - Scroll to the test stage output

4. If tests are non-critical, you can skip them:
   ```yaml
   pipeline:
     test_mode: "false"
   ```

---

## CI/CD Variables Not Set

**Symptoms:** Pipeline fails with "variable not found" or similar errors.

**Solutions:**

1. Verify variables are set in GitLab:
   - Go to **Settings > CI/CD > Variables**
   - Check that all required variables exist

2. Run the setup script again to create/update variables:
   ```bash
   python3 setup_gitlab_project.py --update \
       --gitlab-url https://gitlab.example.com \
       --token glpat-xxxx \
       --project-name omnia-pipeline \
       --config pipeline_config.yml
   ```

3. List all variables:
   ```bash
   python3 setup_gitlab_project.py --list-vars \
       --gitlab-url https://gitlab.example.com \
       --token glpat-xxxx \
       --project-name omnia-pipeline
   ```

---

## GitLab Project Creation Fails

**Symptoms:** `setup_gitlab_project.py --create` fails with authentication or project errors.

**Solutions:**

1. Verify GitLab token is valid:
   - Go to **Settings > Access Tokens**
   - Create a new token with `api` and `write_repository` scopes
   - Use the new token

2. Verify GitLab URL is correct:
   - Should be in format: `https://gitlab.example.com`
   - Not: `https://gitlab.example.com/`

3. Check network connectivity to GitLab:
   ```bash
   curl -k https://gitlab.example.com/api/v4/user
   # Should return your user info (with -H "PRIVATE-TOKEN: <token>")
   ```

4. Verify project name doesn't already exist:
   - Go to GitLab and check if the project already exists
   - If it does, use `--update` instead of `--create`

5. Check script logs for detailed errors:
   ```bash
   python3 setup_gitlab_project.py --create \
       --gitlab-url https://gitlab.example.com \
       --token glpat-xxxx \
       --project-name omnia-pipeline \
       --config pipeline_config.yml 2>&1 | tee setup.log
   ```

---

## Pipeline Hangs or Times Out

**Symptoms:** Pipeline runs but never completes, or times out.

**Solutions:**

1. Check SSH connectivity to target:
   ```bash
   ssh -v root@<TARGET_IP>
   ```

2. SSH into target and check if Ansible is running:
   ```bash
   ps aux | grep ansible
   ```

3. Check target server resources:
   ```bash
   ssh root@<TARGET_IP>
   free -h  # Memory
   df -h    # Disk
   top      # CPU
   ```

4. Increase job timeout in `.gitlab-ci-cluster.yml`:
   ```yaml
   repo_manager:
     timeout: 4h  # Increase from 3h
   ```

5. Check GitLab Runner status:
   - Go to **Admin > Runners**
   - Verify runner is online and not stuck

---

## Email Notifications Not Sent

**Symptoms:** Pipeline completes but email notification is not received.

**Solutions:**

1. Verify SMTP settings in `pipeline_config.yml`:
   ```yaml
   global:
     email:
       recipients: "admin@example.com"
       smtp_server: "smtp.example.com"
       smtp_port: 25
   ```

2. Verify SMTP server is reachable from GitLab Runner:
   ```bash
   telnet smtp.example.com 25
   ```

3. Check email sender is set:
   ```yaml
   global:
     email:
       sender: "omnia-pipeline@example.com"
   ```

4. Check pipeline logs for email errors:
   - Go to **CI/CD > Pipelines > [Pipeline] > summary**
   - Look for email-related errors

---

## Getting Help

If you can't find a solution:

1. **Check the logs:**
   - Go to **CI/CD > Pipelines > [Pipeline] > [Job]**
   - Scroll through the full job output

2. **Enable verbose mode:**
   ```yaml
   pipeline:
     verbose: "true"
   ```

3. **Run a dry-run:**
   ```yaml
   pipeline:
     dry_run: "true"
   ```

4. **Check related documentation:**
   - [Quick Start](QUICKSTART.md)
   - [Pipeline Modes](PIPELINE_MODES.md)
   - [Configuration Reference](CONFIGURATION.md)

---

## Next Steps

- [Quick Start](QUICKSTART.md) — Get started quickly
- [Configuration Reference](CONFIGURATION.md) — Explore all settings
- [Pipeline Modes](PIPELINE_MODES.md) — Learn deployment strategies
