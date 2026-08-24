# Utils Domain — Dataset Generator

Generates test datasets from Jinja2 templates and YAML variable profiles.

## Usage

```bash
# Generate from template with default profile
python generate_dataset.py data_set_01 defaults

# Generate from template with custom profile
python generate_dataset.py data_set_02 custom_profile

# Copy from src/utils/input/
python generate_dataset.py data_set_03 --from-src

# Override variables
python generate_dataset.py data_set_04 defaults --var enable_phone_home=false
```

## Directory Structure

```
generator/
├── generate_dataset.py      # CLI tool
├── profiles/                # Variable profiles (YAML)
│   └── defaults.yml         # Base profile
└── templates/               # Jinja2 templates
    └── input/
        ├── collect_pxe.yml.j2
        ├── set_pxe_boot_config.yml.j2
        ├── set_pxe_boot.ini.j2
        └── set_pxe_boot_credentials.yml.j2
```

## Profiles

Profiles are YAML files that define variables for template rendering.

- `defaults.yml` — Always loaded first
- Custom profiles override defaults

## Templates

Templates use Jinja2 syntax with `StrictUndefined` — missing variables cause errors.

## Generated Output

```
datasets/<name>/
├── input/
│   ├── collect_pxe.yml
│   ├── set_pxe_boot_config.yml
│   ├── set_pxe_boot.ini
│   └── set_pxe_boot_credentials.yml
└── README.md
```
