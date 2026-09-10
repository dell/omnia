# Host & Config — config loading, credentials, testinfra, remote utilities

**Source file:** `omnia_auto/functions/host_func.py`

## What is this?

This module handles everything related to connecting to your target server
and reading configuration.  It loads your YAML config, manages encrypted
credentials, gives you a testinfra `Host` object to run commands on the
target, and provides utilities for reading environment variables and
managing directories on the remote host.

---

## `load_test_config(config_path=None) -> dict`

Load and parse your YAML config file (the one you registered with
`configure(config_file=...)`).

### Parameters

`config_path` is optional. When supplied, it is used directly. Otherwise the
path comes from `configure(module_root=..., config_file=...)`.

### Returns

`dict` — the parsed YAML contents.  You access your config values from here
(server IP, dataset name, clone path, report paths, etc.).

### Prerequisite

You **must** call `configure(module_root=..., config_file=...)` first.

### Raises

- `RuntimeError` if no explicit path is supplied and `config_file` was not configured.
- `OSError` if the selected file cannot be read.
- `yaml.YAMLError` if the file contains invalid YAML.

A missing selected file returns `{}`.

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

## `load_test_credentials(creds_path=None, key_path=None) -> dict`

Load credentials from the credentials YAML file (the one registered with
`configure(credentials_file=...)`). It decrypts existing Ansible Vault
payloads and automatically migrates plaintext YAML to encrypted storage.

### Parameters

`creds_path` and `key_path` are optional explicit paths. Any omitted path is
resolved from `configure()`.

### Returns

`dict` — the credentials as key-value pairs.

### Behaviour

| Scenario | What happens |
|----------|--------------|
| Plain YAML file exists | Reads it, creates a Vault key if needed, atomically encrypts it in place, and returns the mapping |
| Encrypted file + key file exists | Decrypts using the key, returns the dict |
| Encrypted file + key file **missing** | Raises `ValueError` — you need the key to decrypt |
| File not found | Returns `{}` (empty dict) — no credentials |
| YAML root is not a mapping | Raises `ValueError` |

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
oim_password: ""
```

Populate the value with the credential CLI described in
`08_credentials.md`, then encrypt the file before use.

---

## `encrypt_test_credentials(creds_path=None, key_path=None) -> bool`

Explicitly encrypt the credentials file using Ansible Vault. Returns `True`
on success. This is useful when a workflow needs to enforce encrypted storage
before any credential read occurs; normal plaintext reads also migrate the
file automatically.

### Parameters

Both paths are optional; omitted paths use `configure()` settings.

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
manually extracting `mode`, `ip`, `user`, `port`, `auth_secret`, and
`ssh_opts` every time.

### Parameters

None — reads from your config and credentials files.

### Returns

A `dict` with these keys:

| Key | Type | Value |
|-----|------|-------|
| `mode` | `str` | `"local"` or `"ssh"` (based on `is_local_execution()`) |
| `ip` | `str` or `None` | Target server IP (or `None` if local) |
| `user` | `str` | SSH username (from `oim_ssh_user` in config) |
| `port` | `int` | SSH port (from `oim_ssh_port`, default `22`) |
| `auth_secret` | `str` or `None` | SSH authentication secret (from credentials) |
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
#     "port": 22,
#     "auth_secret": None,
#     "ssh_opts": "-o StrictHostKeyChecking=accept-new ...",
# }

# Now pass directly to sync_files:
result = sync_files(
    mode=conn["mode"],
    src="/local/datasets/input",
    dest="/remote/input",
    ip=conn["ip"],
    user=conn["user"],
    port=conn["port"],
    auth_secret=conn["auth_secret"],
    ssh_opts=conn["ssh_opts"],
)
```

---

## `read_remote_env(host, var_name, env_file=None, required=True) -> str`

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
| `required` | `bool` | No | Raise when the value is missing. Use `False` only for an optional variable with an explicit fallback. | `False` |

### Returns

`str` — the variable value, whitespace-stripped.

### Raises

`ValueError` — if the input is invalid, or a required variable is **not set**
or **empty** on the target.

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

# An absent optional override returns an empty string.
override = read_remote_env(
    host, "TELEMETRY_DATA_PATH", required=False,
)
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

## `read_remote_yaml(host, file_path) -> dict`

Read a YAML mapping from the target host. An empty YAML document returns `{}`.

### Raises

| Error | When |
|-------|------|
| `ValueError` | `file_path` is empty, YAML is malformed, or the YAML root is not a mapping |
| `RuntimeError` | The target command cannot read the file |

```python
from omnia_auto import get_testinfra_host, read_remote_yaml

host = get_testinfra_host()
config = read_remote_yaml(host, "/etc/omnia/example.yml")
```

---

## `read_yaml_key(data, key_path, default=None)`

Read a dot-separated path from a YAML mapping. Integer path segments address
list elements. Missing or incompatible segments return `default`.

```python
from omnia_auto import read_yaml_key

endpoint = read_yaml_key(config, "clusters.0.endpoint", default="")
```

---

## `get_inventory_hosts(host, inventory_path, groups, prefix_match=True) -> dict`

Read an Ansible YAML inventory and collect unique host names from selected
groups. With `prefix_match=True`, a request for `slurm_node` also matches
groups such as `slurm_node_x86_64`.

The result contains `success`, `hostnames`, `by_group`, and `error`. Invalid
input or no matching hosts is represented by `success: False`; file and YAML
errors from `read_remote_yaml()` are raised.

```python
from omnia_auto import get_inventory_hosts

result = get_inventory_hosts(
    host,
    "/opt/omnia/orchestrator.yml",
    ["slurm_control_node", "slurm_node"],
)
```

## `get_inventory_host_var(...)`

Read one host variable from
`all.children.<group>.hosts.<hostname>.<var_name>`. Missing data returns the
provided `default`; file and YAML errors from `read_remote_yaml()` are raised.

```python
from omnia_auto import get_inventory_host_var

address = get_inventory_host_var(
    host,
    "/opt/omnia/orchestrator.yml",
    "slurm_control_node_x86_64",
    "control01",
    "ansible_host",
    default="",
)
```

---

## `resolve_domain_data_path(host, domain, data_path_var, domain_data_path_var=None) -> str`

Resolve a domain's complete data root from the target environment. A non-empty
domain-specific variable takes precedence; otherwise the function derives
`<base-data-path>/<domain>`.

```python
from omnia_auto import resolve_domain_data_path

data_root = resolve_domain_data_path(
    host,
    domain="telemetry",
    data_path_var="OMNIA_DATA_PATH",
    domain_data_path_var="TELEMETRY_DATA_PATH",
)
```

With `TELEMETRY_DATA_PATH=/data/telemetry`, the result is `/data/telemetry`.
When that optional variable is absent or empty and
`OMNIA_DATA_PATH=/opt/omnia`, the result is `/opt/omnia/telemetry`.

---

## `resolve_domain_input_path(host, domain, data_path_var, project_var, domain_data_path_var=None) -> str`

Build the full remote input directory path for a domain by reading
environment variables from the target host.

### What it builds

```
<effective-domain-data-path>/input/<OMNIA_PROJECT_NAME>/
```

For example: `/opt/omnia/image_build_manager/input/project_default`

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `host` | `Host` | **Yes** | A testinfra `Host` object. | *(see below)* |
| `domain` | `str` | **Yes** | The domain name (your module's name). | `"image_build_manager"` |
| `data_path_var` | `str` | **Yes** | The **name** of the environment variable on the target that holds the data path. | `"OMNIA_DATA_PATH"` |
| `project_var` | `str` | **Yes** | The **name** of the environment variable on the target that holds the project name. | `"OMNIA_PROJECT_NAME"` |
| `domain_data_path_var` | `str` | No | Name of the optional variable holding the complete domain root. | `"IMAGE_BUILD_MANAGER_DATA_PATH"` |

**Important:** You pass the **names** of the env vars (strings like `"OMNIA_DATA_PATH"`),
not their values.  The function reads the values from the target host.

### Returns

`str` — the assembled absolute path on the target.

### Raises

`ValueError` — if the domain/path is unsafe, the project is unset, or neither
the optional domain override nor the required base data path can be resolved.

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
    domain_data_path_var="IMAGE_BUILD_MANAGER_DATA_PATH",
)
print(path)
# "/opt/omnia/image_build_manager/input/project_default"
```

---

## Prerequisite summary

| Function | What you need first |
|----------|-------------------|
| `load_test_config()` | An explicit `config_path`, or `configure(config_file=...)` |
| `load_test_credentials()` | Explicit credential/key paths, or corresponding `configure()` settings |
| `encrypt_test_credentials()` | Explicit credential/key paths, or corresponding `configure()` settings |
| `get_testinfra_host()` | `configure()` with config and credentials |
| `is_local_execution()` | `configure()` |
| `run_on_host()` | `get_testinfra_host()` → `host` object |
| `run_ssh_command()` | `get_testinfra_host()` → `host` object; passwordless SSH from that host to the secondary target |
| `connection_params()` | `configure()` with config and credentials |
| `read_remote_env()` | `get_testinfra_host()` → `host` object |
| `ensure_remote_dir()` | `get_testinfra_host()` → `host` object |
| `read_remote_yaml()` | `get_testinfra_host()` → `host` object and a readable YAML file |
| `read_yaml_key()` | A parsed mapping and dot-separated key path |
| `get_inventory_hosts()` | A readable Ansible YAML inventory and group names |
| `get_inventory_host_var()` | A readable Ansible YAML inventory and host-variable path |
| `resolve_domain_data_path()` | `get_testinfra_host()` → `host` object, env vars on target |
| `resolve_domain_input_path()` | `get_testinfra_host()` → `host` object, env vars on target |
