# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
User Registry — Negative Test Suite.

Tests that verify error handling and failure scenarios for user registry
configuration and validation.

Tests:
- RM_FVT_USER_REGISTRY_NEG_001: Validation fails with missing repo_manager_config.yml
- RM_FVT_USER_REGISTRY_NEG_002: Validation detects invalid base_url values
- RM_FVT_USER_REGISTRY_NEG_003: Validation detects incomplete TLS cert/key pairs
- RM_FVT_USER_REGISTRY_NEG_004: Validation detects unsupported auth types
- RM_FVT_USER_REGISTRY_NEG_005: Validation detects missing cert paths on disk
- RM_FVT_USER_REGISTRY_NEG_006: Validation detects missing vault_path for basic auth
"""
