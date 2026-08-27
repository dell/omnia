# Dataset Generator Tool

CLI tool for generating test datasets for the utils domain.

## Structure

```
generator/
├── generate_dataset.py      # CLI tool
├── profiles/                # Variable profiles (YAML)
│   ├── defaults.yml         # Base profile
│   └── example_install_os.yml  # Example install_os profile
└── templates/               # Jinja2 templates
    └── input/
        ├── collect_pxe.yml.j2
        └── install_os_config.yml.j2
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
│   └── install_os_config.yml
└── README.md
```

## Usage

```bash
# Generate dataset with default profile
python generate_dataset.py --name my_dataset

# Generate dataset with custom profile
python generate_dataset.py --name my_dataset --profile example_install_os.yml
```

## Profile Variables

See `../README.md` for complete list of available variables.
