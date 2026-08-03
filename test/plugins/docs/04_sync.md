# Sync — `clone_repo()`, `sync_files()`

**Source file:** `src/omnia_auto/functions/sync_func.py`

## What is this?

Two functions for transferring files to the target host:

- **`clone_repo()`** — clone or pull a git repository (locally or over SSH)
- **`sync_files()`** — rsync a directory or copy a single file (locally or over SSH)

Both work in two modes:
- `"local"` — everything happens on the local machine
- `"ssh"` — commands run on a remote host over SSH

---

## `clone_repo(mode, url, dest, ...)` → `dict`

Clone a git repository to a destination path.  If the repo already exists
at `dest`, it does a `git pull` instead (unless `force=True`, which
deletes and re-clones).

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `mode` | `str` | **Yes** | `"local"` — clone on local machine. `"ssh"` — clone on a remote host. | `"ssh"` |
| `url` | `str` | **Yes** | Git clone URL. | `"https://github.com/dell/omnia.git"` |
| `dest` | `str` | **Yes** | Where to clone the repo. If `mode="ssh"`, this is a path on the remote host. | `"/root/omnia"` |
| `ip` | `str` | **Required for SSH** | Target host IP address. Only needed when `mode="ssh"`. | `"100.10.0.84"` |
| `user` | `str` | No | SSH username. Default: `"root"`. | `"root"` |
| `password` | `str` | No | SSH password. If provided, `sshpass` is used automatically. If not provided, key-based auth is assumed. | `"my_password"` |
| `ssh_opts` | `str` | No | SSH options string. Default: `"-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"`. | `"-o StrictHostKeyChecking=no"` |
| `force` | `bool` | No | If `True`, removes the existing repo and re-clones from scratch. Default: `False`. | `True` |
| `timeout` | `int` | No | Maximum seconds to wait for the clone to complete. Default: `300` (5 minutes). | `600` |

### Returns

A `dict` with these keys:

| Key | Type | Description |
|-----|------|-------------|
| `success` | `bool` | `True` if the clone/pull succeeded |
| `details` | `str` | Human-readable message like `"Cloned https://... -> /root/omnia"` |
| `error` | `str` | Error message if something went wrong (empty string on success) |

### Error conditions (returns `success: False`)

- `mode` is not `"local"` or `"ssh"`
- `mode="ssh"` but `ip` is not provided
- `url` or `dest` is empty
- `git clone` command fails
- Timeout exceeded

### Prerequisite

None — this function is standalone.  But you'll typically get `ip`, `user`,
`password` from `connection_params()`.

### Example — SSH clone

```python
from omnia_auto import clone_repo, connection_params

conn = connection_params()

result = clone_repo(
    mode=conn["mode"],
    url="https://github.com/dell/omnia.git",
    dest="/root/omnia",
    ip=conn["ip"],
    user=conn["user"],
    password=conn["password"],
    ssh_opts=conn["ssh_opts"],
)

if result["success"]:
    print(result["details"])   # "Cloned https://... -> /root/omnia"
else:
    raise RuntimeError(result["error"])
```

### Example — local clone

```python
from omnia_auto import clone_repo

result = clone_repo(
    mode="local",
    url="https://github.com/dell/omnia.git",
    dest="/tmp/omnia",
)
assert result["success"], result["error"]
```

### Example — force re-clone

```python
result = clone_repo(
    mode="ssh",
    url="https://github.com/dell/omnia.git",
    dest="/root/omnia",
    ip="100.10.0.84",
    user="root",
    force=True,    # deletes /root/omnia and clones fresh
    timeout=600,   # allow 10 minutes
)
```

---

## `sync_files(mode, src, dest, ...)` → `dict`

Sync files or directories from the local machine to a destination.
Uses `rsync` for directories and `cp`/`scp` for single files.

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `mode` | `str` | **Yes** | `"local"` — copy locally. `"ssh"` — copy to a remote host. | `"ssh"` |
| `src` | `str` | **Yes** | Source path on the **local** machine. Can be a file or directory. | `"/root/my-module/test/datasets/data_set_01/input"` |
| `dest` | `str` | **Yes** | Destination path. If `mode="ssh"`, this is a path on the remote host. | `"/opt/omnia/ibm/input/project_default"` |
| `ip` | `str` | **Required for SSH** | Target host IP address. Only needed when `mode="ssh"`. | `"100.10.0.84"` |
| `user` | `str` | No | SSH username. Default: `"root"`. | `"root"` |
| `password` | `str` | No | SSH password. If provided, `sshpass` is used. | `"my_password"` |
| `ssh_opts` | `str` | No | SSH options string. Default: `"-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"`. | `"-o StrictHostKeyChecking=no"` |
| `timeout` | `int` | No | Maximum seconds to wait. Default: `120` (2 minutes). | `300` |
| `mkdir` | `bool` | No | If `True`, creates the destination directory before syncing. Default: `True`. | `False` |

### Returns

A `dict` with these keys:

| Key | Type | Description |
|-----|------|-------------|
| `success` | `bool` | `True` if sync succeeded |
| `details` | `str` | Message like `"Synced /local/path -> root@10.0.0.1:/remote/path"` |
| `error` | `str` | Error message if something went wrong |

### Error conditions (returns `success: False`)

- `mode` is not `"local"` or `"ssh"`
- `src` or `dest` is empty
- `src` path does not exist on the local machine
- `mode="ssh"` but `ip` is not provided
- rsync/scp command fails
- Timeout exceeded

### How it decides rsync vs cp/scp

| Source type | Local mode | SSH mode |
|-------------|-----------|----------|
| Directory | `rsync -avz src/ dest/` | `rsync -avz -e "ssh ..." src/ user@ip:dest/` |
| Single file | `cp src dest` | `scp src user@ip:dest` |

### Prerequisite

None — standalone function.  But you'll typically get connection details
from `connection_params()`.

### Example — sync a dataset directory over SSH

```python
from omnia_auto import sync_files, connection_params

conn = connection_params()

result = sync_files(
    mode=conn["mode"],
    src="/root/my-module/test/datasets/data_set_01/input",
    dest="/opt/omnia/image_build_manager/input/project_default",
    ip=conn["ip"],
    user=conn["user"],
    password=conn["password"],
    ssh_opts=conn["ssh_opts"],
)

assert result["success"], result["error"]
# [OK] Synced /root/.../input -> root@100.10.0.84:/opt/omnia/.../project_default
```

### Example — sync locally

```python
from omnia_auto import sync_files

result = sync_files(
    mode="local",
    src="/root/datasets/input",
    dest="/opt/omnia/input/project_default",
)
assert result["success"], result["error"]
```

---

## Typical usage pattern in `conftest.py`

```python
from omnia_auto import (
    connection_params, sync_files, clone_repo,
    load_test_config, log,
)

def pytest_sessionstart(session):
    config = load_test_config()
    conn = connection_params()

    # 1. Clone/pull the repo on the target
    result = clone_repo(
        mode=conn["mode"],
        url=config["clone_url"],
        dest=config.get("clone_path", "/root/omnia"),
        ip=conn["ip"],
        user=conn["user"],
        password=conn["password"],
        ssh_opts=conn["ssh_opts"],
    )
    assert result["success"], result["error"]
    log(result["details"], "OK")

    # 2. Sync input dataset files
    local_input = os.path.join(_TEST_DIR, "datasets", config["dataset"], "input")
    result = sync_files(
        mode=conn["mode"],
        src=local_input,
        dest="/opt/omnia/ibm/input/project_default",
        ip=conn["ip"],
        user=conn["user"],
        password=conn["password"],
        ssh_opts=conn["ssh_opts"],
    )
    assert result["success"], result["error"]
    log(result["details"], "OK")
```

---

## Prerequisite summary

| Function | What you need first |
|----------|-------------------|
| `clone_repo()` | Nothing (standalone). But `connection_params()` makes it easier. |
| `sync_files()` | Nothing (standalone). But `connection_params()` makes it easier. |
