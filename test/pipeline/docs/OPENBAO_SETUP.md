# OpenBao Setup Guide

Complete this guide before proceeding to the [Quick Start](QUICKSTART.md).

The pipeline fetches domain credentials from OpenBao using JWT authentication. Each pipeline job gets a short-lived JWT token from GitLab, authenticates with OpenBao, and reads the credentials it needs. No static secrets are stored in GitLab.

---

## Phase 1: Install and Configure OpenBao

### 1.1 Download and Install

```bash
curl -LO https://github.com/openbao/openbao/releases/download/v2.1.0/bao_2.1.0_linux_amd64.rpm
sudo yum localinstall bao_2.1.0_linux_amd64.rpm
```

### 1.2 Verify Installation

```bash
which bao
bao version

# Check config and TLS files
cat /etc/openbao/openbao.hcl
ls -la /opt/openbao/tls/
```

### 1.3 Configure OpenBao

```bash
sudo vi /etc/openbao/openbao.hcl
```

Set the following content:

```hcl
ui = true

storage "file" {
  path = "/opt/openbao/data"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/opt/openbao/tls/tls.crt"
  tls_key_file  = "/opt/openbao/tls/tls.key"
}

api_addr = "https://<YOUR_SERVER_IP>:8200"
```

> Replace `<YOUR_SERVER_IP>` with the IP address of the OpenBao server.

### 1.4 Open Firewall Port

```bash
sudo firewall-cmd --permanent --add-port=8200/tcp
sudo firewall-cmd --reload
```

### 1.5 Start OpenBao Service

```bash
sudo systemctl enable openbao
sudo systemctl start openbao
sudo systemctl status openbao
```

### 1.6 Set Environment Variables

```bash
export BAO_ADDR='https://127.0.0.1:8200'
export BAO_SKIP_VERIFY=true

# Make persistent across sessions
echo 'export BAO_ADDR="https://127.0.0.1:8200"' >> ~/.bashrc
echo 'export BAO_SKIP_VERIFY=true' >> ~/.bashrc
source ~/.bashrc
```

### 1.7 Initialize and Unseal

**Initialize:**

```bash
bao operator init
```

> **SAVE the 5 unseal keys and root token securely!**
> These are required to unseal the vault after every restart.

**Unseal (3 of 5 keys required):**

```bash
bao operator unseal    # Enter Unseal Key 1
bao operator unseal    # Enter Unseal Key 2
bao operator unseal    # Enter Unseal Key 3
```

**Verify status:**

```bash
bao status
```

Expected output:

```
Initialized     true
Sealed          false
```

**Login:**

```bash
bao login
# Enter root token when prompted
```

---

## Phase 2: Configure Secrets Engine

### 2.1 Enable KV v2 Secrets Engine

```bash
bao secrets enable -path=secret kv-v2
```

### 2.2 Store Domain Credentials

Store credentials for each domain you plan to deploy:

**Repo Manager credentials:**

```bash
bao kv put secret/omnia/repo_manager \
    pulp_username="admin" \
    pulp_password="<YourPulpPassword>" \
    docker_username="<yourdockeruser>" \
    docker_password="<YourDockerPassword>"
```

**Image Build Manager credentials:**

```bash
bao kv put secret/omnia/image_build_manager \
    aarch64_ssh_password="<YourPassword>" \
    s3_access_id="<YourS3AccessID>" \
    s3_secret_key="<YourS3SecretKey>"
```

**Orchestrator credentials:**

```bash
bao kv put secret/omnia/orchestrator \
    provision_password="<ProvPass>" \
    bmc_username="root" \
    bmc_password="<BmcPass>" \
    slurm_db_password="<SlurmPass>" \
    openldap_db_username="admin" \
    openldap_db_password="<LdapPass>" \
    csi_username="" \
    csi_password=""
```

**Telemetry credentials:**

```bash
bao kv put secret/omnia/telemetry \
    bmc_username="admin" \
    bmc_password="<BmcPassword>" \
    mysqldb_user="admin" \
    mysqldb_password="<MysqlPwd>" \
    mysqldb_root_password="<MysqlRootPwd>" \
    csi_username="admin" \
    csi_password="<CsiPassword>" \
    ldms_sampler_password="<LdmsPwd>" \
    ufm_username="admin" \
    ufm_password="<UfmPassword>" \
    vast_username="admin" \
    vast_password="<VastPassword>"
```

### 2.3 Verify Secrets

```bash
bao kv list secret/omnia/
bao kv get secret/omnia/repo_manager
```

---

## Phase 3: Configure JWT Authentication for GitLab

### 3.1 Extract GitLab SSL Certificate

If GitLab uses a self-signed or internal CA certificate:

```bash
echo | openssl s_client -connect <GITLAB_IP>:443 2>/dev/null | \
    openssl x509 -out /tmp/gitlab.crt
```

### 3.2 Enable JWT Auth Method

```bash
bao auth enable jwt
```

### 3.3 Configure JWT with GitLab OIDC Discovery

```bash
bao write auth/jwt/config \
    oidc_discovery_url="https://<GITLAB_URL>" \
    bound_issuer="https://<GITLAB_URL>" \
    oidc_discovery_ca_pem=@/tmp/gitlab.crt
```

**Verify:**

```bash
bao read auth/jwt/config
```

### 3.4 Create Policy

```bash
cat <<EOF > gitlab-policy.hcl
path "secret/data/omnia/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/omnia/*" {
  capabilities = ["read", "list"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}
EOF

bao policy write gitlab-policy gitlab-policy.hcl
```

### 3.5 Create JWT Role for GitLab

```bash
bao write auth/jwt/role/gitlab-role \
    role_type="jwt" \
    policies="gitlab-policy" \
    token_explicit_max_ttl=3600 \
    user_claim="user_email" \
    bound_audiences="https://<OPENBAO_SERVER_IP>:8200"
```

**Verify:**

```bash
bao read auth/jwt/role/gitlab-role
```

### 3.6 Set GitLab CI/CD Variables

Go to your GitLab project > **Settings** > **CI/CD** > **Variables** and add:

| Variable | Value | Type |
|---|---|---|
| `BAO_SERVER_URL` | `https://<OPENBAO_IP>:8200` | Variable |
| `BAO_AUTH_ROLE` | `gitlab-role` | Variable |
| `BAO_DATA_PATH` | `secret/data/omnia` | Variable |

These are also set automatically when using `pipeline_config.yml` with the setup script.

---

## Troubleshooting OpenBao Setup

### OpenBao won't start

```bash
sudo journalctl -u openbao -n 50
```

Check for configuration errors in `/etc/openbao/openbao.hcl`.

### Can't connect to OpenBao

```bash
curl -k https://<OPENBAO_IP>:8200/v1/sys/health
```

If this fails:
- Check firewall: `sudo firewall-cmd --list-ports`
- Verify OpenBao is running: `sudo systemctl status openbao`
- Check network connectivity from GitLab Runner to OpenBao host

### JWT authentication fails

1. Verify `oidc_discovery_url` matches your GitLab instance URL
2. Verify `bound_audiences` in the role matches the OpenBao server URL
3. If GitLab uses a self-signed certificate, verify `oidc_discovery_ca_pem` was set
4. Confirm GitLab version is 15.7+ (required for `id_tokens`)

---

## Next Steps

Once OpenBao is configured and verified, proceed to the [Quick Start Guide](QUICKSTART.md).
