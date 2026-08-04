# Runner — `run_playbook()`

**Source file:** `src/omnia_auto/functions/runner_func.py`

## What is this?

Runs an Ansible playbook via `ansible-playbook` with live output streaming.
If the target is a remote host, the command is automatically wrapped in SSH.
A background timer enforces the timeout — if the playbook takes too long,
the process is killed.

---

## `run_playbook(playbook, tag, ...) -> dict`

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `playbook` | `str` | **Yes** | The playbook **filename** (not a full path — just the file name). | `"image_build_manager.yml"` |
| `playbook_workdir` | `str` | **Yes** | The subdirectory **under `clone_path`** where the playbook file lives. The full path becomes `<clone_path>/<playbook_workdir>/<playbook>`. | `"src/image_build_manager/playbooks"` |
| `tag` | `str` or `list` or `None` | No | Ansible tag(s) to run. Pass a single string for one tag, a list for multiple tags, or `None` to run all tasks. | `"prepare"` or `["prepare", "build"]` |
| `extra_vars` | `dict` | No | Extra variables passed as `ansible-playbook -e key=value`. | `{"target_arch": "x86_64"}` |
| `verbosity` | `int` | No | Ansible verbosity level (0-4). `0` = quiet, `4` = maximum debug. If not given, uses `configure(default_verbosity=...)` or `1`. | `2` |
| `timeout` | `int` | No | Maximum seconds to wait for the playbook to finish. If not given, uses `configure(default_timeout=...)` or `7200`. | `1800` |
| `limit` | `str` | No | Ansible `--limit` pattern to target specific hosts. | `"compute_nodes"` |

### How the full playbook path is built

```
clone_path (from test_config.yml, default: /root/omnia)
  └── playbook_workdir (you pass this)
        └── playbook (you pass this)

Example:
  /root/omnia / src/image_build_manager/playbooks / image_build_manager.yml
```

### Returns

A `dict` with these keys:

| Key | Type | Description |
|-----|------|-------------|
| `success` | `bool` | `True` if ansible-playbook exited with code 0 |
| `rc` | `int` | The exit code of the process (0 = success) |
| `output` | `str` | The full stdout output from the playbook run |
| `duration` | `float` | How long the run took, in seconds |
| `error` | `str` or `None` | Error message if something went wrong, `None` on success |
| `playbook` | `str` | The playbook filename that was used |

### Error conditions (returns `success: False`)

| Condition | Error message |
|-----------|---------------|
| `playbook` not provided | `'playbook' argument is required` |
| `playbook_workdir` not provided | `'playbook_workdir' argument is required` |
| `sshpass` not installed but password needed | `sshpass is required for password-based SSH` |
| Playbook exits with non-zero code | Detailed error with rc, tag, log path |
| Timeout exceeded | `Playbook timed out after N seconds` |
| Process killed by user (Ctrl+C) | `Cancelled by user` |

### Prerequisite

1. `configure()` — for module root, config, credentials.
2. Your `test_config.yml` must have `oim_server_ip` (and optionally `clone_path`).
3. Your `test_creds.yml` must have `oim_password` (if SSH with password).
4. `ansible-playbook` must be installed on the machine running the tests (or the target).

### How it works internally

1. Reads config and credentials from `configure()` settings.
2. Builds the `ansible-playbook` command with tags, extra vars, verbosity.
3. If remote: wraps the command in `ssh` (or `sshpass + ssh`).
4. Runs via `subprocess.Popen` with live line-by-line output streaming.
5. A `threading.Timer` enforces the timeout.
6. Returns a result dict.

### Recommended pattern: consumer wrapper

Since `playbook` and `playbook_workdir` are specific to your module and
don't change between tests, the recommended pattern is to create a thin
wrapper in your module's `functions/__init__.py` so your test files don't
have to repeat these values:

**Step 1 — Define your constants** in `library/vars/common_vars.py`:

```python
PLAYBOOK_ENTRY_POINT = "image_build_manager.yml"
PLAYBOOK_WORKDIR = "src/image_build_manager/playbooks"
```

**Step 2 — Create the wrapper** in `library/functions/__init__.py`:

```python
from omnia_auto import run_playbook as _run_playbook
from ..vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR

def run_playbook(tag=None, **kwargs):
    """Wrapper that injects this module's playbook and workdir."""
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag,
        **kwargs,
    )
```

**Step 3 — Call from test files** (clean, no playbook args needed):

```python
from library.functions import run_playbook

def test_prepare_phase():
    result = run_playbook(tag="prepare", timeout=1800)
    assert result["success"], result["error"]
```

### Example — direct call (without wrapper)

```python
from omnia_auto import run_playbook

result = run_playbook(
    playbook="image_build_manager.yml",
    playbook_workdir="src/image_build_manager/playbooks",
    tag="build",
    timeout=3600,
    verbosity=2,
    extra_vars={"target_arch": "x86_64"},
)

if result["success"]:
    print(f"Playbook completed in {result['duration']:.1f}s")
else:
    print(f"FAILED (rc={result['rc']}): {result['error']}")
```

### Example — multiple tags

```python
result = run_playbook(
    playbook="image_build_manager.yml",
    playbook_workdir="src/image_build_manager/playbooks",
    tag=["validate", "prepare"],
)
```

### Example — run all tasks (no tag filter)

```python
result = run_playbook(
    playbook="image_build_manager.yml",
    playbook_workdir="src/image_build_manager/playbooks",
    tag=None,  # or just omit the tag parameter
)
```

---

## Prerequisite summary

| Function | What you need first |
|----------|-------------------|
| `run_playbook()` | `configure()` with config and credentials. `ansible-playbook` installed. |
