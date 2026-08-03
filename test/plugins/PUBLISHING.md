# Publishing omnia-auto to PyPI

Step-by-step guide for building and publishing the `omnia-auto` package.

---

## Prerequisites

```bash
pip install build twine
```

| Tool | Purpose |
|------|---------|
| `build` | Creates wheel (`.whl`) and source distribution (`.tar.gz`) |
| `twine` | Uploads packages to PyPI / TestPyPI |

---

## 1. Update Version

Before every release, update the version in **two** places:

| File | Field |
|------|-------|
| `pyproject.toml` | `version = "X.Y.Z"` |
| `src/omnia_auto/__init__.py` | `__version__ = "X.Y.Z"` |

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (1.0.0 → 2.0.0) — breaking API changes
- **MINOR** (1.0.0 → 1.1.0) — new features, backward-compatible
- **PATCH** (1.0.0 → 1.0.1) — bug fixes only

Update `CHANGELOG.md` with the new version entry.

---

## 2. Clean Previous Builds

```bash
rm -rf dist/ build/ src/*.egg-info
```

---

## 3. Build the Package

```bash
python -m build
```

This creates two files in `dist/`:

```
dist/
├── omnia_auto-1.0.0-py3-none-any.whl     # Wheel (binary distribution)
└── omnia_auto-1.0.0.tar.gz               # Source distribution (sdist)
```

---

## 4. Verify the Build

### Check the wheel contents

```bash
unzip -l dist/omnia_auto-1.0.0-py3-none-any.whl
```

Expected contents:
```
omnia_auto/__init__.py
omnia_auto/py.typed
omnia_auto/functions/__init__.py
omnia_auto/functions/formatting_func.py
omnia_auto/functions/host_func.py
omnia_auto/functions/report_func.py
omnia_auto/functions/runner_func.py
omnia_auto/functions/sync_func.py
omnia_auto/vars/__init__.py
omnia_auto/vars/common_vars.py
omnia_auto/messages/__init__.py
omnia_auto/messages/runner_msgs.py
omnia_auto-1.0.0.dist-info/...
```

### Check the metadata

```bash
python -m twine check dist/*
```

Expected output:
```
Checking dist/omnia_auto-1.0.0-py3-none-any.whl: PASSED
Checking dist/omnia_auto-1.0.0.tar.gz: PASSED
```

### Test install in a clean venv

```bash
python -m venv /tmp/test-omnia-auto
source /tmp/test-omnia-auto/bin/activate
pip install dist/omnia_auto-1.0.0-py3-none-any.whl
python -c "import omnia_auto; print(omnia_auto.__version__)"
# Should print: 1.0.0
deactivate
rm -rf /tmp/test-omnia-auto
```

---

## 5. Upload to TestPyPI (Dry Run)

TestPyPI is a separate PyPI instance for testing uploads without affecting
the real index.

### Create a TestPyPI account

1. Go to https://test.pypi.org/account/register/
2. Create an account and verify your email
3. Go to https://test.pypi.org/manage/account/#api-tokens
4. Create an API token (scope: entire account or project-specific)

### Upload

```bash
python -m twine upload --repository testpypi dist/*
```

When prompted:
- **Username:** `__token__`
- **Password:** your TestPyPI API token (starts with `pypi-`)

### Verify on TestPyPI

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ omnia-auto
```

---

## 6. Upload to PyPI (Production)

### Create a PyPI account

1. Go to https://pypi.org/account/register/
2. Create an account and verify your email
3. Enable 2FA (required for new projects)
4. Go to https://pypi.org/manage/account/#api-tokens
5. Create an API token

### Upload

```bash
python -m twine upload dist/*
```

When prompted:
- **Username:** `__token__`
- **Password:** your PyPI API token (starts with `pypi-`)

### Verify

```bash
pip install omnia-auto
python -c "import omnia_auto; print(omnia_auto.__version__)"
```

---

## 7. Using a `.pypirc` File (Optional)

To avoid entering credentials every time, create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_PRODUCTION_TOKEN

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_TOKEN
```

Set permissions:
```bash
chmod 600 ~/.pypirc
```

Then upload with:
```bash
python -m twine upload dist/*                          # → PyPI
python -m twine upload --repository testpypi dist/*    # → TestPyPI
```

---

## 8. Internal Distribution (Without PyPI)

For internal use without publishing to PyPI, distribute the wheel file
directly:

```bash
# Build
python -m build --wheel

# Copy wheel to consumer
cp dist/omnia_auto-1.0.0-py3-none-any.whl /path/to/consumer/

# Install in consumer
pip install /path/to/consumer/omnia_auto-1.0.0-py3-none-any.whl

# Or force-reinstall after a rebuild
pip install --force-reinstall /path/to/omnia_auto-1.0.0-py3-none-any.whl
```

### From a private Git repository

```bash
pip install git+https://github.com/balajikumaran-c-s/omnia-auto.git@main
```

### From a requirements.txt

```
# Local wheel
omnia-auto @ file:///path/to/omnia_auto-1.0.0-py3-none-any.whl

# Git source
omnia-auto @ git+https://github.com/balajikumaran-c-s/omnia-auto.git@v1.0.0
```

---

## Release Checklist

```
[ ] Version updated in pyproject.toml and __init__.py
[ ] CHANGELOG.md updated with new version entry
[ ] All tests pass: pytest -s (in a consumer module)
[ ] Clean build: rm -rf dist/ build/ src/*.egg-info && python -m build
[ ] twine check passes: python -m twine check dist/*
[ ] Test install works in a clean venv
[ ] Upload to TestPyPI and verify (optional for internal)
[ ] Upload to PyPI (or distribute wheel internally)
[ ] Git tag created: git tag v1.0.0 && git push origin v1.0.0
```
