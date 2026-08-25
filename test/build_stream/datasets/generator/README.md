# Dataset Generator — Build Stream

Renders Jinja2 templates into test dataset directories.

## Quick Start

```bash
# Generate from a profile
python generate_dataset.py my_ds defaults

# Copy directly from src/build_stream/input/
python generate_dataset.py my_ds --from-src

# List available profiles
python generate_dataset.py --list-profiles

# Regenerate with overrides
python generate_dataset.py my_ds defaults --var gitlab_host=10.5.0.100 --force
```

## Profiles

| Profile | Description |
|---------|-------------|
| `defaults` | Base profile with placeholder values |

Override any key with `--var KEY=VALUE` (repeatable).

## Generated Files

```
datasets/<name>/
  input/
    build_stream_config.yml      # BSM + GitLab settings
    build_stream_credentials.yml # Placeholder credentials
  README.md                      # Auto-generated summary
```

## Adding New Profiles

1. Create `profiles/<name>.yml` with overrides
2. `defaults.yml` is always loaded first as the base
3. Profile values override defaults (deep-merge)

Example `profiles/my_env.yml`:
```yaml
gitlab_host: "10.5.0.100"
build_stream_host_ip: "10.5.0.28"
build_stream_port: 8010
```
