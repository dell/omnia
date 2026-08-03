# Contributing to omnia-auto

Rules and standards for developing and maintaining the `omnia-auto` pip package.

---

## 1. Code Quality Requirements

### Pylint Score

**Minimum pylint score: 8.8 / 10**

Run before every commit:

```bash
python -m pylint src/omnia_auto/ --max-line-length=120
```

Accepted suppressions (with `# pylint: disable=` inline):
- `too-many-arguments` — functions like `clone_repo` and `sync_files` need many params by design
- `too-many-instance-attributes` — `TestReport` requires many fields
- `too-many-locals` — HTML template generation (`report_func.py`) requires many variables
- `global-statement` — module-level singleton for `_current_report`

All other pylint warnings must be resolved.

### Code Style

| Rule | Standard |
|------|----------|
| Line length | 120 characters max |
| Naming | `snake_case` for functions and variables, `PascalCase` for classes |
| Imports | stdlib → third-party → local, separated by blank lines |
| Docstrings | Google style or reStructuredText (rst). Required for all public functions |
| Type hints | Required for all public function signatures |
| String formatting | f-strings preferred |

### Black Formatting (Optional)

```bash
python -m black src/omnia_auto/ --line-length 120 --check
```

---

## 2. Security Rules

### Mandatory Before Every Commit

Run the security scan:

```bash
# No hardcoded IPs
grep -rn -iE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' src/omnia_auto/ \
    --include="*.py" | grep -v '127\.0\.0\.1'

# No hardcoded passwords/secrets
grep -rn -iE '(password|passwd|secret|token|api.?key)\s*=\s*["'"'"']' \
    src/omnia_auto/ --include="*.py"

# Both must return empty (no matches)
```

### Absolute Prohibitions

| Forbidden | Why |
|-----------|-----|
| Hardcoded IP addresses | Consumer passes all IPs via `connection_params()` or explicit args |
| Hardcoded passwords or tokens | Consumer provides via `test_creds.yml` (Ansible Vault encrypted) |
| Hardcoded file paths to user data | Consumer passes via `configure(module_root=...)` |
| Reading config inside sync/runner | Consumer passes ALL params — package is pure execution |
| Writing to `/etc/`, `/root/`, or system dirs | Package only writes to paths the consumer provides |

### Docstring Examples

In docstrings, use placeholder variables instead of real values:

```python
# WRONG
clone_repo(mode="ssh", ip="10.0.0.1", password="secret")

# CORRECT
clone_repo(mode=conn["mode"], ip=conn["ip"], password=conn["password"])
```

---

## 3. Architecture Rules

### Plug-and-Play Design

The package must remain **fully consumer-driven**:

1. **No hardcoded defaults for consumer-specific values** — IP, user, password, paths
2. **All config via `configure()`** — consumer calls once in `conftest.py`
3. **Sync functions take explicit params** — `mode`, `ip`, `user`, `password`, `ssh_opts`
4. **Runner takes explicit `playbook` and `playbook_workdir`** — consumer wraps with defaults

### Function Categories

| Category | File | Rules |
|----------|------|-------|
| Configuration | `vars/common_vars.py` | Only `_settings` dict, no file I/O |
| Formatting | `functions/formatting_func.py` | Pure output, no external deps |
| Host/Config | `functions/host_func.py` | May read YAML files from `module_root` |
| Sync | `functions/sync_func.py` | Pure execution — consumer passes ALL params |
| Runner | `functions/runner_func.py` | Pure execution — consumer passes playbook/workdir |
| Report | `functions/report_func.py` | Generates JSON + HTML, no hardcoded paths |
| Messages | `messages/runner_msgs.py` | String templates only, no logic |

### Adding a New Function

1. Put it in the correct category file
2. Add to the file's module-level docstring
3. Export from `functions/__init__.py`
4. Export from `src/omnia_auto/__init__.py` (add to `__all__`)
5. Add type hints for all parameters
6. Add docstring with Args, Returns, Raises
7. Add to `USAGE.md` quick reference table
8. Create or update the relevant `docs/` guide
9. Run pylint — score must stay ≥ 8.8

### Adding a New Module File

1. Create in the correct subdirectory (`functions/`, `vars/`, or `messages/`)
2. Add Apache 2.0 license header
3. Add module-level docstring
4. Export from subdirectory `__init__.py`
5. Export public symbols from top-level `__init__.py`

---

## 4. Testing Requirements

### Before Every PR

```bash
# 1. Lint check
python -m pylint src/omnia_auto/ --max-line-length=120
# Score must be ≥ 8.8

# 2. Security scan
grep -rn -iE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' src/omnia_auto/ --include="*.py" | grep -v '127\.0\.0\.1'
grep -rn -iE '(password|secret|token)\s*=\s*["'"'"']' src/omnia_auto/ --include="*.py"
# Both must return empty

# 3. Build check
rm -rf dist/ build/ src/*.egg-info
python -m build
python -m twine check dist/*
# Must show PASSED for both wheel and sdist

# 4. Import check
python -c "import omnia_auto; print(f'v{omnia_auto.__version__}: {len(omnia_auto.__all__)} exports')"

# 5. Consumer test (in a consumer module like image_build_manager)
pip install --force-reinstall dist/omnia_auto-*.whl
pytest fvt/ -s --tb=short -m "sanity and not deploy"
```

### Test Checklist

```
[ ] pylint score ≥ 8.8
[ ] No hardcoded IPs or passwords
[ ] twine check PASSED
[ ] Clean import (no ImportError)
[ ] Consumer sanity tests pass
[ ] Version updated in pyproject.toml AND __init__.py
[ ] CHANGELOG.md updated
```

---

## 5. Omnia Integration Rules

### Consumer Module Pattern

Every Omnia automation module that uses `omnia-auto` must follow this pattern:

```
my_module/
├── conftest.py                 # Calls omnia_auto.configure()
├── test_config.yml             # Module-specific config
├── test_creds.yml              # Credentials (auto-encrypted)
├── library/
│   ├── __init__.py             # Re-exports from omnia_auto + local
│   ├── functions/
│   │   ├── __init__.py         # run_playbook wrapper + re-exports
│   │   ├── host_func.py        # Module-specific sync wrappers
│   │   └── <domain>_func.py    # Module-specific verification
│   ├── vars/
│   │   └── common_vars.py      # PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR, CMDS
│   └── messages/
│       └── <domain>_msgs.py    # Test names, assertion messages
└── fvt/
    └── <scenario>/
        └── test_*.py           # Test files
```

### Required conftest.py Setup

```python
import omnia_auto
omnia_auto.configure(
    module_root=os.path.dirname(os.path.abspath(__file__)),
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
)
```

### Required run_playbook Wrapper

Every consumer MUST wrap `run_playbook` with module defaults:

```python
from omnia_auto import run_playbook as _run_playbook
from ..vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR

def run_playbook(tag=None, **kwargs):
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag, **kwargs,
    )
```

---

## 6. Versioning

Follow [Semantic Versioning](https://semver.org/):

| Change Type | Version Bump | Example |
|-------------|-------------|---------|
| Bug fix | PATCH | 1.0.0 → 1.0.1 |
| New function (backward-compatible) | MINOR | 1.0.0 → 1.1.0 |
| Breaking API change | MAJOR | 1.0.0 → 2.0.0 |

Update version in **two** files:
1. `pyproject.toml` → `version = "X.Y.Z"`
2. `src/omnia_auto/__init__.py` → `__version__ = "X.Y.Z"`

---

## 7. Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new function for remote file validation
fix: handle timeout in run_playbook when process hangs
docs: update USAGE.md with new function reference
chore: bump version to 1.1.0
refactor: extract SSH command builder into helper
test: add consumer integration test for sync_files
```

Always sign-off: `git commit -s -m "type: description"`

---

## 8. PR Checklist

```
[ ] Code follows the architecture rules (no hardcoded values)
[ ] pylint score ≥ 8.8
[ ] Security scan passes (no IPs, passwords, tokens)
[ ] New functions have type hints and docstrings
[ ] New functions exported in __init__.py and __all__
[ ] USAGE.md and docs/ updated for new functions
[ ] CHANGELOG.md updated
[ ] Version bumped (if releasing)
[ ] twine check PASSED
[ ] Consumer tests pass
[ ] Signed-off commit
```
