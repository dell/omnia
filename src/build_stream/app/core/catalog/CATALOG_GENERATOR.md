# Catalog generator

This directory contains utility tools for catalog generation and validation.

## Catalog Files

Catalog files are now located in `src/main/samples/` directory instead of the removed `examples/catalog/` directory.

**Available catalogs:**
- `catalog_rhel_10_0_aarch64.json`
- `catalog_rhel_10_0_x86_64.json`
- `catalog_rhel_10_0_x86_aarch64.json`
- `catalog_rhel_10_2_x86_aarch64.json`
- `catalog_rhel.json`
- `catalog_rhel_x86_64.json`

## Tools

### 1. generate_catalog_examples.py

**DEPRECATED:** Catalog example files have been removed from the repository and moved to `src/main/samples/`.

Generates example catalog JSON files from input configuration by cycling through different mapping/software_config combinations.

**Location:** `build_stream/generate_catalog_examples.py`

**Usage:**
```bash
cd /omnia/build_stream
python3 generate_catalog_examples.py --base-dir /omnia/input/project_default/
```

**What it does:**
- Copies mapping files from mapping configuration to the input directory
- Generates catalogs for each mapping variant (slurm-only, nfs-provisioner, etc.)
- Outputs generated catalogs to a specified directory
- Provides a summary of packages and layers generated

**Note:** The example catalog files and mapping_file_software_config directory have been removed from the repository. Catalog files are now available in `src/main/samples/`. This tool can still be used to generate custom catalogs, but the pre-built examples are no longer available in the examples directory.
