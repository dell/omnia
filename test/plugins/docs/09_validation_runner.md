# Validation runner

**Source file:** `omnia_auto/functions/validation_runner.py`

`ValidationRunner` provides a common command dispatcher for an Omnia test
domain. It discovers or accepts FVT tags, runs pytest for FVT/NFT/UT
categories, supports execution and verification phases, and returns a process
exit code suitable for a shell wrapper.

## Minimal domain entry point

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

from omnia_auto import ValidationRunner


def main() -> int:
    test_dir = Path(__file__).resolve().parent
    runner = ValidationRunner(
        domain="example",
        script_dir=str(test_dir),
        domain_config={
            "tags": ["precheck", "deploy", "cleanup"],
            "markers": ["sanity", "source", "sink"],
            "suites": {
                "deploy": ["sources", "sinks"],
            },
            "exclude_tags": ["cleanup"],
            "enable_ut": True,
        },
    )
    return runner.main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
```

## Domain configuration

| Key | Type | Purpose |
|-----|------|---------|
| `tags` | list of strings | Allowed FVT directories; directories are discovered when omitted |
| `markers` | list of strings | Allowed domain-specific pytest markers |
| `suites` | mapping | Allowed suite directories for each FVT tag |
| `exclude_tags` | list of strings | FVT tags omitted from an unqualified all-tag verification |
| `all_exec_tags` | list of strings | Ordered tags for an unqualified lifecycle execution |
| `all_exec_marker` | string | Default marker for that lifecycle execution |
| `enable_ut` | bool | Enable the `ut_<domain>` category; defaults to `True` |

## Command shape

Given `domain="example"`, typical calls are:

```bash
python _run.py fvt_example list
python _run.py fvt_example deploy exec
python _run.py fvt_example deploy verify --marker sanity
python _run.py fvt_example deploy test --suite sources
python _run.py nft_example test
python _run.py ut_example test
python _run.py --config
```

FVT commands are `exec`, `verify`, and `test` (`exec` followed by `verify`).
Options include `--marker`, `--suite`, `--verbose`, and `--debug`. Unsupported
options, markers, and suites return a nonzero exit code and must not broaden
the selected test scope.

`--config` reads `test_run_config.yml` from `script_dir` for batch execution.
Use `runner.main(...)` as the only dispatch point so its exit code propagates
to the calling shell.

The batch file uses category keys derived from the configured domain:

```yaml
skip_on_failure: false
sync_input_override: false

fvt_example:
  deploy:
    run: true
    command: "test"
    marker: "sanity"
    suite: "sources"
    dataset: ""
    sync_output: false

nft_example:
  run: false
  command: "test"
  marker: ""
```

`run`, `skip_on_failure`, and synchronization controls must be YAML booleans
(`true` or `false`, without quotes). A malformed category, unknown marker,
missing suite, or empty eligible FVT selection returns a nonzero status without
starting pytest. This prevents a configuration typo from broadening a run.
