# catalog-generation

## Purpose

Generates Omnia catalogs from operator-described roles, OS families/versions, architectures, and packages. Use when creating single-platform, hybrid-OS, or mixed-stack catalogs from verified catalog and consumer support.

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
| Selection Interview | Resolves seven configuration domains (platform, stack, compute, storage, network, packages and sources, output), asking only for missing answers |
| Hybrid OS | Maps each role to its own OS version/architecture (e.g. controller and login on RHEL 10.2, compute on RHEL 10.0) |
| repo_manager Contract Review | Checks layer naming, single OS type, and per-layer source coverage, which schema validation does not cover |
| Catalog Naming | Offers configuration-specific names or accepts the operator's own name |
| Hardware Prompts | GPU: NVIDIA or None (CPU-only software); InfiniBand: Yes or No |
| Stack-Storage Filtering | Validates storage compatibility with selected software stack |
| Architecture Constraints | Enforces architecture-specific limitations (e.g., Kubernetes x86_64-only) |
| Functional Layer Expansion | Generates role-by-architecture functional layers with appropriate groups |
| Custom Roles/Packages | Supports operator-defined functional roles and additional packages |
| Package Resolution | Resolves package versions and sources via online/offline connectivity layer |
| Schema Validation | Validates generated catalogs against official schema before output |
| Channel-Agnostic | Works in coding agent or browser-based AI assistant environments |

## Workflow

The skill has seven steps (see `SKILL.md`):

1. **Normalize the request**: extract supplied answers and ask only the missing ones, including catalog identity
2. **Storage**: resolve storage by environment and purpose
3. **Preflight and confirmation**: dependency review, Source Overrides checkpoint, cross-domain checks, single confirmation
4. **Layer expansion and group resolution**: one layer per approved (role, OS, version, architecture), groups from shipped catalogs
5. **Package resolution**: sources and versions for every consuming platform
6. **Assemble and validate**: schema validation plus the model-performed review, including the repo_manager contract
7. **Completion summary**: output path, validation status, unresolved items, repository mappings needed before sync

## References

- `src/build_stream/ai_skills/catalog-selection-gate/references/master_reference_file.md` — Appendix A tables (Selection Catalogue, Node-Role, Functional-Layer Composition, etc.)
- `src/build_stream/ai_skills/catalog-selection-gate/SKILL.md` — Shared support_status Selection Catalogue gate
- `src/build_stream/ai_skills/shared/connectivity_layer.md` — Online/offline package resolution fallback procedure
- `src/repo_manager/schemas/catalog_schema.json` — Official Omnia catalog JSON schema
- `src/build_stream/ai_skills/shared/working_directory.md` — Working directory conventions for draft catalogs

## Limitations

This skill does **not**:
- Edit existing catalogs (see `catalog-editing` skill)
- Produce a deployable catalog for an OS family other than RHEL: only the `rhel` profile is enabled in repo_manager, so such output stays a blocked draft
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
Missing `jsonschema` or an unreadable/missing schema blocks validation.
Without shell access, output is explicitly an unvalidated draft.

Companion skills are resolved only within this checkout's `ai_skills`
bundle; see `../shared/skill_scope.md`. Previously loaded or installed
skills from another directory are not substitutes.
