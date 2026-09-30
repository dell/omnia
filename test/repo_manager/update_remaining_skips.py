#!/usr/bin/env python3
"""
Script to update remaining pytest.skip() calls to use tl.skipped_fields()
This is a helper script to document the remaining updates needed.
"""

import re
import os

# Files and their skip patterns
UPDATES = {
    "fvt/user_registry/test_user_registry_negative.py": [
        {
            "pattern": r'pytest\.skip\("No registries configured"\)',
            "replacement": '''tl.skipped_fields(
            "No registries configured",
            {
                "Registries": 0,
                "Configuration": "user_registry",
            }
        )
        pytest.skip("No registries configured")''',
            "count": 5
        },
        {
            "pattern": r'pytest\.skip\("All configured base_url values are valid"\)',
            "replacement": '''tl.skipped_fields(
            "All configured base_url values are valid - negative case not applicable",
            {
                "Configuration": "user_registry",
                "Validation": "passed",
                "Test type": "negative",
            }
        )
        pytest.skip("All configured base_url values are valid")''',
            "count": 1
        },
        {
            "pattern": r'pytest\.skip\("All configured TLS cert/key pairs are consistent"\)',
            "replacement": '''tl.skipped_fields(
            "All configured TLS cert/key pairs are consistent - negative case not applicable",
            {
                "Configuration": "user_registry",
                "Validation": "passed",
                "Test type": "negative",
            }
        )
        pytest.skip("All configured TLS cert/key pairs are consistent")''',
            "count": 1
        },
        {
            "pattern": r'pytest\.skip\("All configured auth types are valid"\)',
            "replacement": '''tl.skipped_fields(
            "All configured auth types are valid - negative case not applicable",
            {
                "Configuration": "user_registry",
                "Validation": "passed",
                "Test type": "negative",
            }
        )
        pytest.skip("All configured auth types are valid")''',
            "count": 1
        },
        {
            "pattern": r'pytest\.skip\("All configured TLS cert paths exist"\)',
            "replacement": '''tl.skipped_fields(
            "All configured TLS cert paths exist - negative case not applicable",
            {
                "Configuration": "user_registry",
                "Validation": "passed",
                "Test type": "negative",
            }
        )
        pytest.skip("All configured TLS cert paths exist")''',
            "count": 1
        },
        {
            "pattern": r'pytest\.skip\("All basic auth registries have vault_path"\)',
            "replacement": '''tl.skipped_fields(
            "All basic auth registries have vault_path - negative case not applicable",
            {
                "Configuration": "user_registry",
                "Validation": "passed",
                "Test type": "negative",
            }
        )
        pytest.skip("All basic auth registries have vault_path")''',
            "count": 1
        },
    ],
    "fvt/user_registry/validation/test_validation.py": [
        {
            "pattern": r'pytest\.skip\("No registries configured"\)',
            "replacement": '''tl.skipped_fields(
            "No registries configured",
            {
                "Registries": 0,
                "Configuration": "user_registry",
            }
        )
        pytest.skip("No registries configured")''',
            "count": 7
        },
    ],
    "fvt/catalog_generate/test_playbook.py": [
        {
            "pattern": r'pytest\.skip\(f"Catalog generate input file not found: \{input_file\}"\)',
            "replacement": '''tl.skipped_fields(
            "Catalog generate input file not found",
            {
                "File": input_file,
                "Status": "missing",
                "Tag": "catalog_generate",
            }
        )
        pytest.skip(f"Catalog generate input file not found: {input_file}")''',
            "count": 1
        },
    ],
    "fvt/catalog_add/test_playbook.py": [
        {
            "pattern": r'pytest\.skip\(f"Input file not found: \{input_file\}"\)',
            "replacement": '''tl.skipped_fields(
            "Catalog add input file not found",
            {
                "File": input_file,
                "Status": "missing",
                "Tag": "catalog_add",
            }
        )
        pytest.skip(f"Input file not found: {input_file}")''',
            "count": 1
        },
    ],
    "fvt/catalog_delete/test_playbook.py": [
        {
            "pattern": r'pytest\.skip\(f"Input file not found: \{input_file\}"\)',
            "replacement": '''tl.skipped_fields(
            "Catalog delete input file not found",
            {
                "File": input_file,
                "Status": "missing",
                "Tag": "catalog_delete",
            }
        )
        pytest.skip(f"Input file not found: {input_file}")''',
            "count": 1
        },
    ],
}

print("=" * 80)
print("REMAINING SKIP UPDATES NEEDED")
print("=" * 80)
print()

total_updates = 0
for filepath, updates in UPDATES.items():
    print(f"\n📄 {filepath}")
    for update in updates:
        total_updates += update["count"]
        print(f"   • {update['count']} occurrence(s) of skip pattern")
        print(f"     Pattern: {update['pattern']}")

print()
print("=" * 80)
print(f"TOTAL UPDATES NEEDED: {total_updates} pytest.skip() calls")
print("=" * 80)
