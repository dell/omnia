# Catalog generator

This directory contains utility tools for catalog generation and validation.

## Tools

### 1. generate_catalog_examples.py

Generates example catalog JSON files from input configuration by cycling through different mapping/software_config combinations.

**Location:** `build_stream/generate_catalog_examples.py`

**Usage:**
```bash
cd /omnia/build_stream
python3 generate_catalog_examples.py --base-dir /omnia/input/project_default/
```

**What it does:**
- Copies mapping files from `examples/catalog/mapping_file_software_config/` to the input directory
- Generates catalogs for each mapping variant (slurm-only, nfs-provisioner, etc.)
- Outputs generated catalogs to `examples/catalog/` directory
- Provides a summary of packages and layers generated

**Generated catalogs:**
- `catalog_rhel_aarch64_with_slurm_only.json`
- `catalog_rhel_x86_64_with_slurm_only.json`
- `catalog_rhel_with_nfs_provisioner.json`
- `catalog_rhel_x86_64.json`
- `catalog_rhel.json`

---

### 2. diff_input_configs.py

Compares two input directories (expected vs actual) and reports per-file, per-cluster package differences.
This can be used independantly or after running the catalog generator to check the differences.

**Location:** `build_stream/core/catalog/tests/diff_input_configs.py`

**Usage:**
```bash
cd /omnia/build_stream/core/catalog/tests
python3 diff_input_configs.py \
    --expected /omnia/input \
    --actual   /tmp/adapter_output_test/input
```

**Optional arguments:**
- `--file-level`: Compare packages at file level (flatten all clusters) instead of per-cluster
- `--report <path>`: Write a human-readable table report to the given file
- `--pxe-mapping <path>`: Path to PXE mapping CSV file for information display
- `--catalog <path>`: Path to catalog file for information display

**What it does:**
1. Compares `software_config.json` (softwares list and versions)
2. Walks `config/<arch>/<os>/<ver>/*.json` in both directories
3. For each matching JSON, compares packages per cluster section
4. Reports missing files, extra files, and per-cluster diffs
5. Handles versioned filenames (e.g., `service_k8s_v1.35.1.json` matches `service_k8s.json`)
6. Ignores common package extraction and `_first` cluster merging artifacts

**Programmatic usage (for tests):**
```python
from diff_input_configs import run_diff_for_test

passed, issue_count, report_path = run_diff_for_test(
    expected_dir="/path/to/expected",
    actual_dir="/path/to/actual",
    report_file="/path/to/report.txt"  # optional, uses temp file if not provided
)
# Returns: (passed: bool, issue_count: int, report_path: str)
```

**Exit codes:**
- `0`: No differences found
- `1`: Differences found

---

### 3. test_catalog_diff_regression.py

Regression test suite that validates catalog generation and adapter policy output.

**Location:** `build_stream/core/catalog/tests/test_catalog_diff_regression.py`

**Core idea:**
Validates the end-to-end flow: catalog → adapter policy → input configs, ensuring the generated output matches the expected input configuration files.

**Steps:**
1. Loads example catalog (`catalog_rhel.json`)
2. Runs generator to create root JSONs (functional_layer.json, infrastructure.json, etc.)
3. Runs adapter policy to generate input configs from root JSONs
4. Uses `diff_input_configs.py` to compare generated output with expected input configs
5. Validates functional layers match PXE mapping expectations
6. Checks specific package routing and architecture constraints

**Usage:**
```bash
cd /omnia/build_stream/core/catalog/tests
python3 -m pytest test_catalog_diff_regression.py -v
```

**Test classes:**
- `TestAdapterDiffReport`: Verifies adapter output matches expected configs using diff tool
- `TestCatalogFunctionalLayers`: Validates functional layers against PXE mapping and architecture constraints
