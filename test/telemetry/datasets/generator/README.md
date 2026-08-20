# Telemetry Dataset Generator

Generates test datasets from Jinja2 templates and variable profiles.

## Usage

```bash
cd datasets/generator/

# Generate from a profile
python generate_dataset.py data_set_01 defaults

# Generate with variable overrides
python generate_dataset.py idrac_test idrac_only --var kube_vip=10.0.0.200

# Copy from src/ (quick bootstrap)
python generate_dataset.py data_set_01 --from-src

# List available profiles
python generate_dataset.py --list-profiles
```

## Profiles

| Profile | Description |
|---------|-------------|
| `defaults` | All sources and sinks enabled |
| `idrac_only` | Only iDRAC source (minimal) |
| `sinks_only` | Only sinks, no sources |
| `minimal` | Everything disabled (validation-only) |
