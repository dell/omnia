# Files Migrated from src/common/

The following files were copied from `src/common/` to `src/image_build_manager/library/`
as part of the image_build_manager domain isolation.

## Modules (copied to library/modules/)

| Source | Target | Status |
|--------|--------|--------|
| `common/library/modules/base_image_package_collector.py` | `library/modules/base_image_package_collector.py` | **MOVED** — removed from common |
| `common/library/modules/image_package_collector.py` | `library/modules/image_package_collector.py` | **MOVED** — removed from common |
| `common/library/modules/functional_group_parser.py` | `library/modules/functional_group_parser.py` | **MOVED** — removed from common |

## Module Utils (copied to library/module_utils/build_image/)

| Source | Target | Status |
|--------|--------|--------|
| `common/library/module_utils/build_image/__init__.py` | `library/module_utils/build_image/__init__.py` | **COPIED** — common copy kept for orchestrator |
| `common/library/module_utils/build_image/common_functions.py` | `library/module_utils/build_image/common_functions.py` | **COPIED** — common copy kept for orchestrator |
| `common/library/module_utils/build_image/config.py` | `library/module_utils/build_image/config.py` | **COPIED** + `FUNCTIONAL_GROUP_LAYER_MAP` inlined from `input_validation/common_utils/config.py` |

## Additional Modules (copied to library/modules/)

| Source | Target | Status |
|--------|--------|--------|
| `common/library/modules/generate_functional_groups.py` | `library/modules/generate_functional_groups.py` | **COPIED** — import updated to use local `build_image.config` |

## Callback Plugins (copied to callback_plugins/)

| Source | Target | Status |
|--------|--------|--------|
| `common/callback_plugins/omnia_default.py` | `callback_plugins/omnia_default.py` | **COPIED** — common copy kept for other domains |

## Schemas (copied to library/module_utils/image_build_validation/schema/)

| Source | Target | Status |
|--------|--------|--------|
| `common/library/module_utils/input_validation/schema/image_build_config.json` | `library/module_utils/image_build_validation/schema/image_build_config.json` | Copied — keep in common for central validate_input.py |
| `common/library/module_utils/input_validation/schema/image_build_credentials.json` | `library/module_utils/image_build_validation/schema/image_build_credentials.json` | Copied — keep in common for central validate_input.py |
| `common/library/module_utils/input_validation/schema/functional_groups_config.json` | `library/module_utils/image_build_validation/schema/functional_groups_config.json` | Copied — keep in common for central validate_input.py |

## New Files (created in library/)

| File | Purpose |
|------|---------|
| `library/modules/validate_image_build_config.py` | Image build-specific L1+L2 validation module |
| `library/module_utils/image_build_validation/__init__.py` | Package init |
| `library/module_utils/image_build_validation/image_build_validation_flow.py` | L2 validation rules |
| `library/module_utils/image_build_validation/schema/__init__.py` | Package init |

## Removal Status

The following files have been **removed** from `src/common/`:

1. ~~`src/common/library/modules/base_image_package_collector.py`~~ — **REMOVED**
2. ~~`src/common/library/modules/image_package_collector.py`~~ — **REMOVED**
3. ~~`src/common/library/modules/functional_group_parser.py`~~ — **REMOVED**

**DO NOT remove** from common (still used by other domains):
- `module_utils/build_image/` — shared with orchestrator via `additional_images_collector.py`
- `module_utils/input_validation/` — used by central `validate_input.py`
- `callback_plugins/omnia_default.py` — used by all other domains
- `modules/generate_functional_groups.py` — used by orchestrator
