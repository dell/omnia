# Changelog

All notable changes to `omnia-auto` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-07-31

### Added

- **Configuration** — `configure()`, `get_setting()`, `init_module_root()`, `get_module_root()`
- **Formatting** — `Colors`, `Symbols`, `TestLogger`, `log()`, `set_debug_mode()`
- **Session summary** — `add_session_result()`, `print_summary_table()`, `get_session_results()`, `clear_session_results()`
- **Host utilities** — `load_test_config()`, `load_test_credentials()`, `encrypt_test_credentials()`, `get_testinfra_host()`, `is_local_execution()`, `run_on_host()`
- **Connection helpers** — `connection_params()`, `read_remote_env()`, `ensure_remote_dir()`, `resolve_domain_input_path()`
- **Sync** — `clone_repo()`, `sync_files()` (local + SSH modes)
- **Runner** — `run_playbook()` with live output streaming and SSH wrapping
- **Report** — `TestReport` class with JSON + HTML output, `set_current_report()`, `get_current_report()`
- **Documentation** — Detailed per-category guides in `docs/`
- **Typing** — `py.typed` marker for PEP 561 compliance

### Changed

- Version bumped from `0.1.0` (alpha) to `1.0.0` (production/stable)
- `pyproject.toml` updated with full PyPI classifiers, license file, documentation URL

---

## [0.1.0] — 2026-07-28

### Added

- Initial alpha release
- Core package structure with `functions/`, `vars/`, `messages/`
- Basic formatting, host, runner, sync, and report modules
