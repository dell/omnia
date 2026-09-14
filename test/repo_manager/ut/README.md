# Repo Manager deterministic tests

These tests exercise Repo Manager source and orchestration contracts without a
live Pulp service, registry, subscription or destructive cleanup.

Run with the Python standard library:

```bash
python3 -m unittest discover -s test/repo_manager/ut -p 'test_*.py' -v
```

After installing `test/repo_manager/requirements.txt`, the shared runner can
also execute them:

```bash
test/repo_manager/run_validation.sh ut_repo_manager test
```

Expected-failure tests record confirmed production gaps. They must be removed
from `expectedFailure` when the corresponding source behavior is corrected;
they are not permission to weaken the required invariant.

The `cleanup` and `cleanup_repos` FVT suites are separate, destructive and
explicitly excluded from aggregate FVT execution.
