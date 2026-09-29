# catalog-generation

## Purpose

Generates schema-valid Omnia catalogs from operator-described functional groups, base OS, and package lists. Use when creating new catalogs for cluster configurations (Slurm, Kubernetes, or mixed-stack deployments).

## When to Use

Use this skill when you need to:
- Create a new Omnia catalog from scratch
- Generate catalogs for Slurm-only, Kubernetes-only, or mixed-stack clusters
- Ensure catalog output conforms to the Omnia catalog schema
- Resolve package sources, versions, and dependencies from master reference data

## Prerequisites

- Access to `src/build_stream/ai_skills/catalog-selection-gate/references/master_reference_file.md`
- Access to `src/repo_manager/schemas/catalog_schema.json`
- Understanding of target cluster configuration (OS, stack, roles, storage, network)

## Usage

### Basic Invocation

```
Generate a catalog for a minimal Slurm-only cluster on RHEL 10.2
```

### With Specific Requirements

```
Generate a catalog for:
- RHEL 10.2, x86_64 and aarch64
- Slurm stack
- Roles: os, slurm_control_node, slurm_node, login_node
- GPU: NVIDIA
- Storage: VAST
- Network: InfiniBand
```

## Capabilities

| Capability | Description |
|------------|-------------|
| Selection Interview | Guides operator through 9-step dependency-ordered configuration selection |
| Stack-Storage Filtering | Validates storage compatibility with selected software stack |
| Architecture Constraints | Enforces architecture-specific limitations (e.g., Kubernetes x86_64-only) |
| Functional Layer Expansion | Generates role-by-architecture functional layers with appropriate groups |
| Custom Roles/Packages | Supports operator-defined functional roles and additional packages |
| Package Resolution | Resolves package versions and sources via online/offline connectivity layer |
| Schema Validation | Validates generated catalogs against official schema before output |
| Channel-Agnostic | Works in coding agent or browser-based AI assistant environments |

## Workflow

1. **Selection Interview** (Steps 1-9): Collect OS, architecture, stack, roles, GPU, storage, network, source overrides, and additional packages
2. **Confirmation**: Present complete configuration for operator approval
3. **Functional Layer Expansion**: Generate layers per role and architecture
4. **Group Resolution**: Resolve group package composition from shipped catalogs
5. **Package Resolution**: Resolve versions and sources via connectivity layer
6. **Assembly**: Build complete catalog JSON structure
7. **Validation**: Run schema validation (when shell access available)
8. **Output**: Deliver validated catalog with repository-name consistency reminder

## References

- `src/build_stream/ai_skills/catalog-selection-gate/references/master_reference_file.md` — Appendix A tables (Selection Catalogue, Node-Role, Functional-Layer Composition, etc.)
- `src/build_stream/ai_skills/catalog-selection-gate/SKILL.md` — Shared support_status Selection Catalogue gate
- `src/build_stream/ai_skills/shared/connectivity_layer.md` — Online/offline package resolution fallback procedure
- `src/repo_manager/schemas/catalog_schema.json` — Official Omnia catalog JSON schema
- `src/build_stream/ai_skills/shared/working_directory.md` — Working directory conventions for draft catalogs

## Limitations

This skill does **not**:
- Edit existing catalogs (see `edit-catalog` skill)
- Perform bulk catalog edits (see `bulk-edit-catalog` skill)
- Analyze catalog impact or compatibility (see analysis skills)
- Update master reference data (manual process)

## Validation

Generated catalogs are validated using:

```bash
python3 src/repo_manager/plugins/module_utils/catalog/catalog_manager.py \
  validate --catalog <path> \
  --schema src/repo_manager/schemas/catalog_schema.json
```

Exit code 0 with no `[ERROR]` lines indicates schema-valid output.
