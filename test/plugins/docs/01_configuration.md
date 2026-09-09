# Configuration — shared settings and scoped overrides

**Source file:** `omnia_auto/vars/common_vars.py`

## What is this?

Host, runner, and config-file helpers need to know where a consumer test module
lives and which files it uses. `configure()` records those supported settings
for the current execution context and is normally called near the top of
`conftest.py`. Standalone formatting and explicit-path credential helpers do
not require configuration.

Think of it as "registering" your test module with the package.

---

## `configure(**kwargs)`

### When to call

At the start of a test session, usually in `conftest.py`. Use `configured()`
for a temporary override instead of repeatedly changing session settings.

### What it does

Stores key-value settings that the rest of the package reads internally.
For example, when you later call `load_test_config()`, it looks up the
`config_file` name you registered here.

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `module_root` | `str` | **Yes** | Absolute path to your test directory. This is used to locate config files, datasets, etc. Usually `os.path.dirname(__file__)` in `conftest.py`. | `"/root/my-module/test"` |
| `repository_root` | `str` | No | Explicit Omnia repository root for consumers that need it. | `"/root/omnia"` |
| `config_file` | `str` | **Yes** | Name of the YAML config file inside `module_root`. This file holds things like server IP, dataset name, clone path, etc. | `"test_config.yml"` |
| `credentials_file` | `str` | No | Name of the credentials YAML file inside `module_root`. If provided, `load_test_credentials()` will look for this file. | `"test_creds.yml"` |
| `credentials_key` | `str` | No | Name of the Ansible Vault key file inside `module_root`. Used to encrypt/decrypt `credentials_file`. | `".test_creds.key"` |
| `env_file` | `str` | No | Path to an environment file **on the remote target host**. Used by `read_remote_env()` to source variables. If not set, defaults to `/etc/omnia/omnia.env`. | `"/etc/omnia/omnia.env"` |
| `ssh_opts` | `str` | No | SSH options used by clone and sync helpers. The default accepts a host key on first use and verifies it thereafter: `-o StrictHostKeyChecking=accept-new -o LogLevel=ERROR`. | `"-o StrictHostKeyChecking=yes"` |
| `ssh_options_list` | list/tuple of strings | No | SSH arguments used by the playbook runner. | `["-o", "StrictHostKeyChecking=yes"]` |
| `default_verbosity` | `int` | No | Default Ansible verbosity level (0 = quiet, 4 = maximum). Used by `run_playbook()` when you don't pass `verbosity=` explicitly. Default is `1`. | `2` |
| `default_timeout` | `int` | No | Default timeout in seconds for playbook runs. Used by `run_playbook()` when you don't pass `timeout=` explicitly. Default is `7200` (2 hours). | `3600` |
| `line_width` | `int` | No | Maximum terminal line width for output wrapping. Default is `160`. | `120` |
| `runner_logger_name` | `str` | No | Logger name displayed in `run_playbook()` output. Default is `"playbook_runner"`. | `"image_build_runner"` |
| `venv_env_var` | `str` | No | Name of the target environment variable holding a virtual-environment path. | `"OMNIA_VENV_PATH"` |

Unsupported setting names raise `TypeError`. Invalid values raise `ValueError`,
so a typo fails during setup instead of silently changing later execution.
SSH settings accept only `-o Name=value` entries from the package's safe
connection-option allowlist. Command-bearing directives, configuration-file
includes, and options that disable host-key verification are rejected.

### Full example

```python
import os
import omnia_auto

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))

omnia_auto.configure(
    module_root=_TEST_DIR,
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
    env_file="/etc/omnia/omnia.env",
    default_timeout=3600,
    default_verbosity=1,
)
```

### What happens if you skip it?

Most other functions (`load_test_config`, `get_testinfra_host`, `run_playbook`, etc.)
will raise a `RuntimeError` because they can't find the `module_root` or `config_file`.

---

## `get_setting(key, default=None)`

### When to use

Anytime you need to read a configured value or a built-in default such as
`ssh_opts`.

### Parameters

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `key` | `str` | **Yes** | The setting name you want to read. | `"default_timeout"` |
| `default` | any | No | Value to return if the key was never configured. | `3600` |

### Returns

The stored value, or `default` when a supported optional setting has not been
configured. Unknown setting names raise `KeyError` so spelling mistakes do not
silently fall back.

### Example

```python
from omnia_auto import get_setting

timeout = get_setting("default_timeout")       # 3600 (from configure)
repo_root = get_setting("repository_root", "/srv/omnia")
```

---

## `configured(**kwargs)` / `reset_configuration()`

`configured()` is a context manager that applies validated overrides only for
the duration of its block and restores the prior context afterward.
`reset_configuration()` resets the current execution context to package
defaults.

```python
from omnia_auto import configured, get_setting, reset_configuration

with configured(default_timeout=30):
    assert get_setting("default_timeout") == 30

reset_configuration()
```

Configuration is stored with `contextvars`, which isolates independent thread
and asynchronous execution contexts. Mutable setting values should still be
treated as configuration, not application state.

---

## `init_module_root(path)` / `get_module_root()`

### When to use

These are convenience helpers. `init_module_root()` is equivalent to calling
`configure(module_root=path)`. `get_module_root()` returns the stored path.

You usually don't need these if you already called `configure(module_root=...)`.

### Parameters — `init_module_root`

| Parameter | Type | Required? | What to give | Example |
|-----------|------|-----------|--------------|---------|
| `path` | `str` | **Yes** | Absolute path to your test module directory. | `"/root/my-module/test"` |

### Returns — `get_module_root`

`str` — the absolute path that was configured.

### Raises

`RuntimeError` if `module_root` was never configured.

### Example

```python
from omnia_auto import init_module_root, get_module_root

init_module_root("/root/my-module/test")
print(get_module_root())  # "/root/my-module/test"
```

---

## Prerequisite summary

| Function | Prerequisite |
|----------|-------------|
| `configure()` | None — call this first |
| `configured()` | None |
| `reset_configuration()` | None |
| `get_setting()` | None; built-in defaults are available before configuration |
| `init_module_root()` | None |
| `get_module_root()` | `configure(module_root=...)` or `init_module_root()` |
