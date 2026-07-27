# Omnia Test Cases — Main Module

> **Module:** `main` (omnia.sh lifecycle)
> **Version:** Omnia 2.3
> **Last Updated:** Jul 2026

---

## 1. Test Case ID Convention

```
TC_<AREA>_<SEQ>
```

| Prefix   | Functional Area         | Scenario              |
|----------|-------------------------|-----------------------|
| `TC_IT`  | Install Tests           | `omnia_sh_install`    |
| `TC_RI`  | Reinstall Tests         | `omnia_sh_reinstall`  |
| `TC_UT`  | Uninstall Tests         | `omnia_sh_uninstall`  |
| `TC_NF`  | Non-Functional Tests    | `nft/`                |

---

## 2. Install Scenario — `omnia_sh_install`

### 2.1 Container (Deploy)

| TC ID       | Test Function                          | Description                                      | Marker(s)        | Pre-condition              | Expected Result                               |
|-------------|----------------------------------------|--------------------------------------------------|------------------|----------------------------|-----------------------------------------------|
| `TC_IT_001` | `test_build_container_images`          | Build omnia_core container image via `--build`   | sanity           | omnia.sh script exists     | Image built, rc=0                             |
| `TC_IT_002` | `test_omnia_sh_install`                | Run `omnia.sh --install` (fresh install)         | sanity           | Container NOT running      | Container running, rc=0                       |

**File:** `fvt/omnia_sh_install/container/test_deploy.py`
**Command:** `run_validation omnia_sh_install deploy`

### 2.2 Container (Verify)

| TC ID       | Test Function                          | Description                                      | Marker(s)        | Pre-condition              | Expected Result                               |
|-------------|----------------------------------------|--------------------------------------------------|------------------|----------------------------|-----------------------------------------------|
| `TC_IT_003` | `test_omnia_core_container_running`    | Verify omnia_core container is running           | sanity, smoke    | Deploy completed           | Container state = `running`                   |
| `TC_IT_004` | `test_omnia_core_container_file_exists`| Verify `.container` unit file exists             | sanity           | Deploy completed           | File at `/etc/containers/systemd/`            |
| `TC_IT_005` | `test_omnia_core_service_running`      | Verify systemd service is active                 | sanity, smoke    | Deploy completed           | `systemctl is-active` = `active`              |
| `TC_IT_006` | `test_oim_metadata_file_exists`        | Verify `oim_metadata.yml` inside container       | sanity           | Deploy completed           | File exists with valid YAML                   |
| `TC_IT_012` | `test_container_image_exists`          | Verify omnia_core image exists locally           | sanity           | Deploy completed           | `podman images` shows omnia_core              |
| `TC_IT_013` | `test_omnia_dir_in_container`          | Verify `/omnia/` directory inside container      | sanity, smoke    | Deploy completed           | `/omnia/` exists with content                 |
| `TC_IT_014` | `test_log_dirs_exist`                  | Verify log directories in shared path            | sanity           | Deploy completed           | `log/core/container` and `playbooks` exist    |
| `TC_IT_015` | `test_omnia_version`                   | Verify `omnia.sh --version` output               | sanity, functional| Deploy completed          | Non-empty version string returned             |

**File:** `fvt/omnia_sh_install/container/test_verify.py`
**Command:** `run_validation omnia_sh_install verify --suite container`

### 2.3 Security (Verify)

| TC ID       | Test Function                                  | Description                                      | Marker(s)              | Pre-condition              | Expected Result                               |
|-------------|------------------------------------------------|--------------------------------------------------|------------------------|----------------------------|-----------------------------------------------|
| `TC_IT_007` | `test_passwordless_ssh_to_container`            | SSH from OIM server to omnia_core (no password)  | sanity, smoke, security| Deploy completed           | `ssh omnia_core whoami` returns `root`         |
| `TC_IT_008` | `test_passwordless_ssh_from_container_to_host`  | SSH from omnia_core to OIM server (no password)  | sanity, security       | Deploy completed           | `ssh <oim_ip> hostname` succeeds              |
| `TC_IT_009` | `test_ssh_key_pair_exists`                     | Verify SSH key pair (oim_rsa) exists             | sanity, security       | Deploy completed           | `~/.ssh/oim_rsa` + `.pub` exist               |
| `TC_IT_010` | `test_ssh_config_entry`                        | Verify SSH config entry for omnia_core           | sanity, security       | Deploy completed           | `Host omnia_core` in `~/.ssh/config`          |
| `TC_IT_011` | `test_authorized_key`                          | Verify oim_rsa.pub in authorized_keys            | sanity, security       | Deploy completed           | Public key present in `authorized_keys`       |

**File:** `fvt/omnia_sh_install/security/test_ssh.py`
**Command:** `run_validation omnia_sh_install verify --suite security`

---

## 3. Reinstall Scenario — `omnia_sh_reinstall`

### 3.1 Container (Deploy)

| TC ID       | Test Function                          | Description                                      | Marker(s)        | Pre-condition              | Expected Result                               |
|-------------|----------------------------------------|--------------------------------------------------|------------------|----------------------------|-----------------------------------------------|
| `TC_RI_001` | `test_omnia_sh_reinstall_overwrite`    | Reinstall via overwrite path (2 → 2 → y)        | sanity           | Container IS running       | Container re-created, rc=0                    |

**File:** `fvt/omnia_sh_reinstall/container/test_deploy.py`
**Command:** `run_validation omnia_sh_reinstall deploy`

### 3.2 Container (Verify)

| TC ID       | Test Function                              | Description                                      | Marker(s)              | Pre-condition              | Expected Result                               |
|-------------|--------------------------------------------|--------------------------------------------------|------------------------|----------------------------|-----------------------------------------------|
| `TC_RV_001` | `test_container_running_after_reinstall`   | Verify container is running after reinstall      | sanity, smoke          | Reinstall completed        | Container state = `running`                   |
| `TC_RV_002` | `test_container_file_after_reinstall`      | Verify `.container` unit file after reinstall    | sanity                 | Reinstall completed        | File at `/etc/containers/systemd/`            |
| `TC_RV_003` | `test_service_running_after_reinstall`     | Verify systemd service active after reinstall    | sanity, smoke          | Reinstall completed        | `systemctl is-active` = `active`              |
| `TC_RV_004` | `test_metadata_file_after_reinstall`       | Verify `oim_metadata.yml` after reinstall        | sanity                 | Reinstall completed        | File exists with valid YAML                   |
| `TC_RV_005` | `test_ssh_key_pair_after_reinstall`        | Verify SSH key pair after reinstall              | sanity, security       | Reinstall completed        | `~/.ssh/oim_rsa` + `.pub` exist               |
| `TC_RV_006` | `test_ssh_config_after_reinstall`          | Verify SSH config entry after reinstall          | sanity, security       | Reinstall completed        | `Host omnia_core` in `~/.ssh/config`          |
| `TC_RV_007` | `test_authorized_key_after_reinstall`      | Verify authorized_keys after reinstall           | sanity, security       | Reinstall completed        | Public key present in `authorized_keys`       |
| `TC_RV_008` | `test_ssh_to_container_after_reinstall`    | Verify SSH to container after reinstall          | sanity, smoke, security| Reinstall completed        | `ssh omnia_core whoami` returns `root`         |
| `TC_RV_009` | `test_container_image_after_reinstall`     | Verify container image after reinstall           | sanity                 | Reinstall completed        | `podman images` shows omnia_core              |
| `TC_RV_010` | `test_omnia_dir_after_reinstall`           | Verify `/omnia/` directory after reinstall       | sanity, smoke          | Reinstall completed        | `/omnia/` exists with content                 |
| `TC_RV_011` | `test_log_dirs_after_reinstall`            | Verify log directories after reinstall           | sanity                 | Reinstall completed        | `log/core/container` and `playbooks` exist    |
| `TC_RV_012` | `test_version_after_reinstall`             | Verify `omnia.sh --version` after reinstall      | sanity, functional     | Reinstall completed        | Non-empty version string returned             |

**File:** `fvt/omnia_sh_reinstall/container/test_verify.py`
**Command:** `run_validation omnia_sh_reinstall verify`

---

## 4. Uninstall Scenario — `omnia_sh_uninstall`

### 4.1 Cleanup (Deploy)

| TC ID       | Test Function                          | Description                                      | Marker(s)        | Pre-condition              | Expected Result                               |
|-------------|----------------------------------------|--------------------------------------------------|------------------|----------------------------|-----------------------------------------------|
| `TC_UT_001` | `test_omnia_sh_uninstall`              | Run `omnia.sh --uninstall` with `y` confirmation | sanity           | Container IS running       | Container removed, rc=0                       |

**File:** `fvt/omnia_sh_uninstall/cleanup/test_deploy.py`
**Command:** `run_validation omnia_sh_uninstall deploy`

### 4.2 Cleanup (Verify)

| TC ID       | Test Function                          | Description                                      | Marker(s)        | Pre-condition              | Expected Result                               |
|-------------|----------------------------------------|--------------------------------------------------|------------------|----------------------------|-----------------------------------------------|
| `TC_UT_002` | `test_container_removed`               | Verify container is NOT running after uninstall  | sanity           | Uninstall completed        | `podman ps` returns no match                  |
| `TC_UT_003` | `test_container_file_removed`          | Verify `.container` unit file is removed         | sanity           | Uninstall completed        | File does not exist                           |
| `TC_UT_004` | `test_service_removed`                 | Verify systemd service is inactive               | sanity           | Uninstall completed        | `systemctl is-active` = `inactive`/`unknown`  |
| `TC_UT_005` | `test_fstab_entry_removed`             | Verify NFS fstab entry is removed                | sanity           | Uninstall + NFS external   | No `/opt/omnia` in `/etc/fstab`               |
| `TC_UT_006` | `test_mount_removed`                   | Verify NFS mount point is removed                | sanity           | Uninstall + NFS external   | `mount` shows no `/opt/omnia`                 |
| `TC_UT_007` | `test_ssh_key_pair_removed`            | Verify SSH key pair removed                      | sanity, security | Uninstall completed        | `~/.ssh/oim_rsa` + `.pub` removed             |
| `TC_UT_008` | `test_ssh_config_entry_removed`        | Verify SSH config entry removed                  | sanity, security | Uninstall completed        | No `Host omnia_core` in `~/.ssh/config`       |
| `TC_UT_009` | `test_known_hosts_cleaned`             | Verify known_hosts entry cleaned                 | sanity, security | Uninstall completed        | No `[localhost]:2222` in `known_hosts`        |

**File:** `fvt/omnia_sh_uninstall/cleanup/test_verify.py`
**Command:** `run_validation omnia_sh_uninstall verify --suite cleanup`

---

## 5. Quick Reference — Commands

| What You Want                     | Command                                                         |
|-----------------------------------|-----------------------------------------------------------------|
| Full install lifecycle            | `run_validation omnia_sh_install test`                          |
| Build + install only              | `run_validation omnia_sh_install deploy`                        |
| Verify after install              | `run_validation omnia_sh_install verify`                        |
| Verify container tests only       | `run_validation omnia_sh_install verify --suite container`      |
| Verify SSH tests only             | `run_validation omnia_sh_install verify --suite security`       |
| Run smoke tests only              | `run_validation omnia_sh_install verify --marker smoke`         |
| Run reinstall                     | `run_validation omnia_sh_reinstall deploy`                      |
| Verify after reinstall            | `run_validation omnia_sh_reinstall verify`                      |
| Full uninstall lifecycle          | `run_validation omnia_sh_uninstall test`                        |
| Uninstall only                    | `run_validation omnia_sh_uninstall deploy`                      |
| Verify cleanup                    | `run_validation omnia_sh_uninstall verify --suite cleanup`      |
| List all scenarios                | `run_validation list`                                           |

---

## 6. Marker Reference (IEEE 829 / SDD Aligned)

| Marker        | Purpose                                           | When to Use                                  |
|---------------|---------------------------------------------------|----------------------------------------------|
| `sanity`      | Baseline verification — must pass after deploy    | Default for all verification tests           |
| `smoke`       | Minimal critical-path subset (< 2 min)            | CI gate, quick health check                  |
| `regression`  | Full regression coverage across all areas         | Nightly / release validation                 |
| `functional`  | Feature-level functional verification             | Feature-specific test sets                   |
| `negative`    | Invalid input, error handling, boundary tests     | Error path validation                        |
| `security`    | Auth, credentials, SSH, access control            | Security audit, compliance checks            |
| `performance` | Timing, throughput, resource benchmarks           | NFT performance baseline                     |
| `stress`      | Sustained load, concurrency, exhaustion           | NFT stress / soak testing                    |
| `integration` | Cross-component interaction                       | Multi-service interaction tests              |
| `acceptance`  | End-to-end user acceptance criteria               | UAT, customer sign-off                       |

> **Note:** Markers are validation quality categories. Actions like `deploy`, `verify`,
> `reinstall` are CLI commands — not markers.

---

## 7. Dataset vs Marker — Important Distinction

| Concept    | What It Is                  | How It Works                                      | Example                          |
|------------|-----------------------------|---------------------------------------------------|----------------------------------|
| **Dataset**| Storage configuration input | Selected via `test_config.yml` → `use_dataset`    | NFS external, NFS internal, Local|
| **Marker** | Validation quality category | Applied via `@pytest.mark.<marker>` on test funcs | `sanity`, `smoke`, `security`    |

Datasets control **what storage configuration** the test uses.
Markers control **which quality level** of tests to run.
They are orthogonal and can be combined freely.
