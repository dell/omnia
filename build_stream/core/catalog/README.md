| Code | Name                      | When it happens                                                                 |
|------|---------------------------|---------------------------------------------------------------------------------|
| 0    | SUCCESS                   | All processing completed successfully.                                         |
| 2    | ERROR_CODE_INPUT_NOT_FOUND | Required input file is missing (catalog, schema, or a file needed during processing). |
| 3    | ERROR_CODE_PROCESSING_ERROR | Any other unexpected runtime error while parsing or generating outputs.       |

## Usage

### Catalog Parser CLI (`generator.py`)

Generates per-arch/OS/version feature-list JSONs (functional layer, infra, drivers, base OS, miscellaneous).

From the `poc/milestone-1` directory, run the generator as a module:

```bash
python -m catalog_parser.generator \
  --catalog <path-to-catalog.json> \
  [--schema <path-to-schema.json>] \
  [--log-file <path-to-log-file>]
```

- `--catalog` (required): Path to input catalog JSON file.
- `--schema` (optional, default: `resources/CatalogSchema.json`): Path to catalog schema JSON file.
- `--log-file` (optional): Path to log file; if set, the directory is auto-created, otherwise logs go to stderr.

Outputs are written under:

```text
out/main/<arch>/<os_name>/<version>/
  functional_layer.json
  infrastructure.json
  drivers.json
  base_os.json
  miscellaneous.json
```

### Adapter Config Generator (`adapter.py`)

Generates adapter-style config JSONs from the catalog.

From the `poc/milestone-1` directory, run the adapter as a module:

```bash
python -m catalog_parser.adapter \
  --catalog <path-to-catalog.json> \
  [--schema <path-to-schema.json>] \
  [--log-file <path-to-log-file>]
```

- `--catalog` (required): Path to input catalog JSON file.
- `--schema` (optional, default: `resources/CatalogSchema.json`): Path to catalog schema JSON file.
- `--log-file` (optional): Path to log file; if set, the directory is auto-created, otherwise logs go to stderr.

Outputs are written under:

```text
out/adapter/input/config/<arch>/<os_name>/<version>/
  default_packages.json
  nfs.json / openldap.json / openmpi.json (if data)
  service_k8s.json
  slurm_custom.json
  <infra-feature>.json ...
```

### Programmatic usage

You can also call both components directly from Python without going through the CLI.

#### Catalog Parser API (`generator.py`)

Programmatic entry points:

- `generate_root_json_from_catalog(catalog_path, schema_path="resources/CatalogSchema.json", output_root="out/generator", *, log_file=None, configure_logging=False, log_level=logging.INFO)`
- `get_functional_layer_roles_from_file(functional_layer_json_path, *, configure_logging=False, log_file=None, log_level=logging.INFO)`
- `get_package_list(functional_layer_json_path, role=None, *, configure_logging=False, log_file=None, log_level=logging.INFO)`

Behavior:

- Optionally configures logging when `configure_logging=True` (and will create the log directory if needed).
- `generate_root_json_from_catalog` writes per-arch/OS/version feature-list JSONs under `output_root/<arch>/<os>/<version>/`.
- `get_functional_layer_roles_from_file` reads a `functional_layer.json` file, validates it, and returns a list of role names (feature names) present in the functional layer.
- `get_package_list` reads a `functional_layer.json` file and returns a list of role objects with their packages, suitable for use by REST APIs or other callers.

Example usage:

```python
from catalog_parser.generator import (
    get_functional_layer_roles_from_file,
    get_package_list,
)

functional_layer_path = "out/main/x86_64/rhel/10/functional_layer.json"

# Get all functional layer roles
roles = get_functional_layer_roles_from_file(functional_layer_path)

# roles might look like: ["Compiler", "K8S Controller", "K8S Worker", ...]

# Get packages for a specific role (case-insensitive role name)
compiler_packages = get_package_list(functional_layer_path, role="compiler")

# Get packages for all roles
all_role_packages = get_package_list(functional_layer_path)
```

Notes:

- Role matching is case-insensitive (for example, `"k8s controller"` matches `"K8S Controller"`).
- Passing `role=None` returns all roles.
- Passing an empty string for `role` is treated as invalid input and raises `ValueError`.

#### Adapter Config API (`adapter.py`)

Programmatic entry point:

- `generate_omnia_json_from_catalog(catalog_path, schema_path="resources/CatalogSchema.json", output_root="out/adapter/input/config", *, log_file=None, configure_logging=False, log_level=logging.INFO)`

Behavior:

- Optionally configures logging when `configure_logging=True` (and will create the log directory if needed).
- Writes adapter-style config JSONs under `output_root/<arch>/<os>/<version>/`.

#### Sample code

Example Python code showing how to call these APIs programmatically is available in:

- `tests/sample.py`
