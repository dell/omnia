# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Orchestrator-suite variables exposed to tests and report hooks."""

from .openldap_vars import (
    LDAP_DEFAULT_PORT,
    LDAP_PROXY_CONTAINER,
    LDAP_PROXY_SERVICE,
    LDAP_READY_DELAY_SECONDS,
    LDAP_READY_RETRIES,
)
from .test_case_vars import (
    CLEANUP_TEST_CASES,
    NFT_TEST_CASES,
    PRECHECK_TEST_CASES,
    PREPARE_TEST_CASES,
    PROVISION_TEST_CASES,
    PXEBOOT_TEST_CASES,
    TEST_CASES,
)

__all__ = [
    "CLEANUP_TEST_CASES",
    "LDAP_DEFAULT_PORT",
    "LDAP_PROXY_CONTAINER",
    "LDAP_PROXY_SERVICE",
    "LDAP_READY_DELAY_SECONDS",
    "LDAP_READY_RETRIES",
    "NFT_TEST_CASES",
    "PRECHECK_TEST_CASES",
    "PREPARE_TEST_CASES",
    "PROVISION_TEST_CASES",
    "PXEBOOT_TEST_CASES",
    "TEST_CASES",
]
