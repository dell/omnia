#!/usr/bin/env python3
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Reconcile the external OpenLDAP user and Omnia slapd proxy.

This is the Orchestrator-framework equivalent of
``omnia-containers/utility/create_ldap_user.py``.  Non-sensitive deployment
settings come from ``test_config.yml`` and secrets come only from the encrypted
``test_creds.yml`` store.
"""

import argparse
import os
import sys


TEST_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if TEST_ROOT not in sys.path:
    sys.path.insert(0, TEST_ROOT)

import omnia_auto  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create/update the configured POSIX LDAP test user and install "
            "the validated omnia_auth meta-proxy slapd.conf"
        )
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help=(
            "Remove only the configured external LDAP container and volume "
            "before deployment. This deletes that test directory's data."
        ),
    )
    return parser


def main() -> int:
    """Run explicit external LDAP test-environment reconciliation."""
    args = _parser().parse_args()
    omnia_auto.configure(
        module_root=TEST_ROOT,
        config_file="test_config.yml",
        credentials_file="test_creds.yml",
        credentials_key=".test_creds.key",
    )
    from library.functions.external_ldap_func import (  # noqa: E402
        reconcile_external_ldap,
    )

    host = omnia_auto.get_testinfra_host()
    try:
        result = reconcile_external_ldap(host, recreate=args.recreate)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    action = (
        "created " + str(len(result["created_entries"])) + " entries"
        if result["created_entries"]
        else "all entries already existed"
    )
    print("External LDAP test environment is ready")
    print(f"  User:  {result['username']}")
    print(f"  DN:    {result['user_dn']}")
    print(f"  State: {action}; password reconciled")
    if result["proxy_config_path"]:
        print(f"  Proxy: {result['proxy_config_path']} (validated and active)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
