# Orchestrator FVT registry

The maintained registry, layout, ID convention, and runnable commands are in
[`../docs/TEST_CASES.md`](../docs/TEST_CASES.md).

Pytest collection is the authoritative inventory:

```bash
cd test/orchestrator
python3 -m pytest fvt --collect-only -q
```

The framework unit suite rejects missing, duplicate, malformed, or gapful
test-case IDs.
