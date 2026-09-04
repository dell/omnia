# Host & Config — config loading, credentials, testinfra, remote utilities

**Source file:** `src/omnia_auto/functions/host_func.py`

## What is this?

This module handles everything related to connecting to your target server
and reading configuration.  It loads your YAML config, manages encrypted
credentials, gives you a testinfra `Host` object to run commands on the
target, and provides utilities for reading environment variables and
managing directories on the remote host.

---

## `load_test_config() -> dict`

Load and parse your YAML config file (the one you registered with
`configure(config_file=...)`).

### Parameters

None — the config file path comes from `configure()`.

### Returns

`dict` — the parsed YAML contents.  You access your config values from here
(server IP, dataset name, clone path, report paths, etc.).

### Prerequisite

You **must** call `configure(module_root=..., config_file=...)` first.

### Raises

`RuntimeError` if `config_file` was not configured.

### Example

```python
from omnia_auto import load_test_config

config = load_test_config()

# Now you can access your config values:
server_ip  = config["oim_server_ip"]      # "10.20.0.100"
dataset    = config["dataset"]            # "data_set_01"
clone_path = config.get("clone_path", "/root/omnia")
```

### What should be in your `test_config.yml`?

That depends on your module, but typical keys include:

```yaml
oim_server_ip: "10.20.0.100"
oim_ssh_user: "root"
clone_path: "/root/omnia"
dataset: "data_set_01"
report_path: "/opt/omnia/reports"
report_name: "test_report"
```

---

## `load_test_credentials() -> dict`

Load credentials from the credentials YAML file (the one registered with
`configure(credentials_file=...)`).  Handles Ansible Vault encryption
automatically.

### Parameters

None — file paths come from `configure()`.

### Returns

`dict` — the credentials as key-value pairs.

### Behaviour

| Scenario | What happens |
|----------|--------------|
| Plain YAML file exists | Reads it, generates a vault key, encrypts the file in-place, returns the dict |
| Encrypted file + key file exists | Decrypts using the key, returns the dict |
| Encrypted file + key file **missing** | Raises `ValueError` — you need the key to decrypt |
| File not found | Returns `{}` (empty dict) — no credentials |

### Prerequisite

`configure(credentials_file=..., credentials_key=...)` must be called first.

### Example

```python
from omnia_auto import load_test_credentials

creds = load_test_credentials()
password = creds.get("oim_password", "")
```

### What should be in your `test_creds.yml`?

```yaml
oim_password: "my_ssh_password"
```

---

## `encrypt_test_credentials() -> bool`

Explicitly encrypt the credentials file using Ansible Vault.  Returns
`True` on success.  This is useful to call in `pytest_sessionstart` to
make sure credentials are encrypted before any tests run.

### Parameters

None — uses `configure()` settings.

### Prerequisite

`configure(credentials_file=..., credentials_key=...)`.

### Example

```python
from omnia_auto import encrypt_test_credentials

def pytest_sessionstart(session):
    encrypt_test_credentials()  # ensures creds file is vault-encrypted
```

---

## `get_testinfra_host() -> Host`

Get a [testinfra](https://testinfra.readthedocs.io/) `Host` object for
your target server.  This is how you run shell commands on the target
(locally or via SSH).

### Parameters

None — reads `oim_server_ip`, `oim_ssh_user`, `oim_password` from your
config and credentials files.

### Returns

A testinfra `Host` object.  You can run commands on it:

```python
result = host.run("hostname")
print(result.stdout)    # "image-builder"
print(result.rc)        # 0
```

### How it decides local vs SSH

| `oim_server_ip` value | Connection type |
|----------------------|-----------------|
| Empty string / not set | `testinfra.get_host("local://")` — runs commands locally |
| Matches a local network interface IP | `testinfra.get_host("local://")` — runs locally |
| Any other IP address | SSH connection via Ansible inventory |

### Prerequisite

`configure()` with `config_file` (and optionally `credentials_file`).

### Example

```python
from omnia_auto import get_testinfra_host

host = get_testinfra_host()

# Run any shell command on the target
result = host.run("podman ps --format '{{.Names}}'")
for line in result.stdout.strip().split("\n"):
    print(f"Container: {line}")
```

---

## `is_local_execution() -> bool`

Returns `True` if the target is the local machine (no SSH needed).

### Parameters

None — reads from config.

### Prerequisite

`configure()`.

### Example

```python
from omnia_auto import is_local_execution

if is_local_execution():
    print("Running locally — no SSH")
else:
    print("Running remotely via SSH")
```

---

## `run_on_host(host, cmd) -> result`

Run a shell command on the target host.  This is a thin wrapper around
`host.run(cmd)`.

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `host` | `Host` | **Yes** | A testinfra `Host` object from `get_testinfra_host()`. | *(see below)* |
| `cmd` | `str` | **Yes** | The shell command to run on the target. | `"podman ps"` |

### Returns

A result object with attributes:
- `.stdout` — standard output (string)
- `.stderr` — standard error (string)
- `.rc` — return code (int, 0 = success)

### Prerequisite

`get_testinfra_host()` to get the `host` object.

### Example

```python
from omnia_auto import get_testinfra_host, run_on_host

host = get_testinfra_host()
result = run_on_host(host, "cat /etc/os-release | grep PRETTY_NAME")
print(result.stdout)  # PRETTY_NAME="Rocky Linux 9.4 (Blue Onyx)"
```

---

## `run_ssh_command(host, target, command, user="root", connect_timeout=10)`

Run a passwordless SSH command from the current testinfra target to a
secondary node. The helper applies the configured SSH options, enables batch
mode, sets a bounded connection timeout, and safely quotes dynamic values.

```python
from omnia_auto import run_ssh_command

result = run_ssh_command(
    host,
    target="10.20.0.25",
    command="uname -m",
)
```

The return value has the same `stdout`, `stderr`, and `rc` attributes as
`run_on_host()`. An empty target, user, or command raises `ValueError`.

---

## `connection_params() -> dict`

Build a connection dictionary from your config and credentials, ready to
pass into `sync_files()` or `clone_repo()`.  This saves you from
manually extracting `mode`, `ip`, `user`, `password`, `ssh_opts` every time.

### Parameters

None — reads from your config and credentials files.

### Returns

A `dict` with these keys:

| Key | Type | Value |
|-----|------|-------|
| `mode` | `str` | `"local"` or `"ssh"` (based on `is_local_execution()`) |
| `ip` | `str` or `None` | Target server IP (or `None` if local) |
| `user` | `str` | SSH username (from `oim_ssh_user` in config) |
| `password` | `str` or `None` | SSH password (from credentials) |
| `ssh_opts` | `str` | SSH options string |

### Raises

`ValueError` if `oim_server_ip` or `oim_ssh_user` is missing in config
when running in remote mode.

### Prerequisite

`configure()` with `config_file` and `credentials_file`.

### Example

```python
from omnia_auto import connection_params, sync_files

conn = connection_params()
# conn = {
#     "mode": "ssh",
#     "ip": "10.20.0.100",
#     "user": "root",
#     "password": None,
#     "ssh_opts": "-o StrictHostKeyChecking=no ...",
# }

# Now pass directly to sync_files:
result = sync_files(
    mode=conn["mode"],
    src="/local/datasets/input",
    dest="/remote/input",
    ip=conn["ip"],
    user=conn["user"],
    password=conn["password"],
    ssh_opts=conn["ssh_opts"],
)
```

---

## `read_remote_env(host, var_name, env_file=None) -> str`

Read an environment variable from the target host.

### Why is this needed?

When you SSH into a host with testinfra, it uses a non-login shell.
This means environment variables set in `/etc/profile.d/` scripts are
**not** loaded automatically.  This function works around that by
explicitly sourcing the env file before reading the variable.

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `host` | `Host` | **Yes** | A testinfra `Host` object from `get_testinfra_host()`. | *(see below)* |
| `var_name` | `str` | **Yes** | The name of the environment variable you want to read. | `"OMNIA_DATA_PATH"` |
| `env_file` | `str` | No | Full path to the env file on the target to source before reading. If not given, uses `configure(env_file=...)` or defaults to `/etc/omnia/omnia.env`. | `"/etc/myapp/env"` |

### Returns

`str` — the variable value, whitespace-stripped.

### Raises

`ValueError` — if the variable is **not set** or **empty** on the target.

### Prerequisite

1. `configure()` (for the env_file default).
2. `get_testinfra_host()` to get the `host` object.

### Example

```python
from omnia_auto import get_testinfra_host, read_remote_env

host = get_testinfra_host()

# Read OMNIA_DATA_PATH from the target
data_path = read_remote_env(host, "OMNIA_DATA_PATH")
print(data_path)  # "/opt/omnia"

# Read from a custom env file
value = read_remote_env(host, "MY_VAR", env_file="/etc/myapp/env")
```

---

## `ensure_remote_dir(host, path) -> None`

Create a directory on the target host if it does not already exist
(equivalent to `mkdir -p`).

### When to use

Before syncing files to a remote path that might not exist yet.

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `host` | `Host` | **Yes** | A testinfra `Host` object. | *(see below)* |
| `path` | `str` | **Yes** | Absolute path to create on the target. | `"/opt/omnia/ibm/input/project_default"` |

### Returns

`None` — succeeds silently.

### Raises

| Error | When |
|-------|------|
| `ValueError` | `path` is empty |
| `RuntimeError` | `mkdir -p` command fails on the target |

### Prerequisite

`get_testinfra_host()` to get the `host` object.

### Example

```python
from omnia_auto import get_testinfra_host, ensure_remote_dir

host = get_testinfra_host()
ensure_remote_dir(host, "/opt/omnia/image_build_manager/input/project_default")
# Directory now exists on the target
```

---

## `resolve_domain_input_path(host, domain, data_path_var, project_var) -> str`

Build the full remote input directory path for a domain by reading
environment variables from the target host.

### What it builds

```
<OMNIA_DATA_PATH>/<domain>/input/<OMNIA_PROJECT_NAME>/
```

For example: `/opt/omnia/image_build_manager/input/project_default`

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `host` | `Host` | **Yes** | A testinfra `Host` object. | *(see below)* |
| `domain` | `str` | **Yes** | The domain name (your module's name). | `"image_build_manager"` |
| `data_path_var` | `str` | **Yes** | The **name** of the environment variable on the target that holds the data path. | `"OMNIA_DATA_PATH"` |
| `project_var` | `str` | **Yes** | The **name** of the environment variable on the target that holds the project name. | `"OMNIA_PROJECT_NAME"` |

**Important:** You pass the **names** of the env vars (strings like `"OMNIA_DATA_PATH"`),
not their values.  The function reads the values from the target host.

### Returns

`str` — the assembled absolute path on the target.

### Raises

`ValueError` — if `domain` is empty, or either env var is not set on the target.

### Prerequisite

1. `configure()` (for env_file default used internally by `read_remote_env`).
2. `get_testinfra_host()` to get the `host` object.
3. The env vars must actually exist on the target host.

### Example

```python
from omnia_auto import get_testinfra_host, resolve_domain_input_path

host = get_testinfra_host()

path = resolve_domain_input_path(
    host,
    domain="image_build_manager",
    data_path_var="OMNIA_DATA_PATH",       # reads value from target
    project_var="OMNIA_PROJECT_NAME",      # reads value from target
)
print(path)
# "/opt/omnia/image_build_manager/input/project_default"
```

---

## Prerequisite summary

| Function | What you need first |
|----------|-------------------|
| `load_test_config()` | `configure(config_file=...)` |
| `load_test_credentials()` | `configure(credentials_file=..., credentials_key=...)` |
| `encrypt_test_credentials()` | `configure(credentials_file=..., credentials_key=...)` |
| `get_testinfra_host()` | `configure()` with config and credentials |
| `is_local_execution()` | `configure()` |
| `run_on_host()` | `get_testinfra_host()` → `host` object |
| `run_ssh_command()` | `get_testinfra_host()` → `host` object; passwordless SSH from that host to the secondary target |
| `connection_params()` | `configure()` with config and credentials |
| `read_remote_env()` | `get_testinfra_host()` → `host` object |
| `ensure_remote_dir()` | `get_testinfra_host()` → `host` object |
| `resolve_domain_input_path()` | `get_testinfra_host()` → `host` object, env vars on target |
