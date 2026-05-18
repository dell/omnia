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

"""Unit tests for dns_config validation in provision_validation.py."""

import sys
import os
import unittest

# ---------------------------------------------------------------------------
# Bootstrap: make the validation code importable without a full Ansible install
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
MODULE_UTILS = os.path.join(REPO_ROOT, "common", "library", "module_utils")
sys.path.insert(0, MODULE_UTILS)

import types
import importlib

for _name in (
    "ansible",
    "ansible.module_utils",
    "ansible.module_utils.input_validation",
    "ansible.module_utils.input_validation.common_utils",
    "ansible.module_utils.input_validation.validation_flows",
):
    sys.modules.setdefault(_name, types.ModuleType(_name))

_cu_ns = "ansible.module_utils.input_validation.common_utils"
for _sub in ("config", "en_us_validation_msg", "validation_utils"):
    _mod = importlib.import_module(f"input_validation.common_utils.{_sub}")
    sys.modules[f"{_cu_ns}.{_sub}"] = _mod
    setattr(sys.modules[_cu_ns], _sub, _mod)

sys.modules["ansible.module_utils.input_validation.validation_flows.common_validation"] = (
    types.ModuleType("ansible.module_utils.input_validation.validation_flows.common_validation")
)

from input_validation.validation_flows.provision_validation import (  # noqa: E402
    validate_dns_config,
)


def _has_error(errors, key_substr):
    """Check if any error dict has error_key containing the substring."""
    return any(key_substr in e.get("error_key", "") for e in errors)


def _has_error_msg(errors, msg_substr):
    """Check if any error dict has error_msg containing the substring."""
    return any(msg_substr in e.get("error_msg", "") for e in errors)


def _make_config(**overrides):
    """Build a valid dns_config dict, then apply overrides."""
    base = {
        "dns_config": {
            "dns_enabled": True,
            "dns_domain": "hpc.cluster",
        }
    }
    cfg = base["dns_config"]
    for k, v in overrides.items():
        cfg[k] = v
    return base


class TestDnsConfigValidationDisabled(unittest.TestCase):
    """When dns_enabled is false, no validation should run."""

    def test_disabled_returns_no_errors(self):
        data = _make_config(dns_enabled=False)
        self.assertEqual(validate_dns_config(data), [])

    def test_missing_dns_config_key(self):
        self.assertEqual(validate_dns_config({}), [])


class TestDnsDomainValidation(unittest.TestCase):
    """FS-DOMAIN-01: dns_domain must be valid RFC 1035."""

    def test_valid_domain(self):
        self.assertEqual(validate_dns_config(_make_config(dns_domain="hpc.cluster")), [])

    def test_valid_domain_single_label(self):
        self.assertEqual(validate_dns_config(_make_config(dns_domain="hpc")), [])

    def test_valid_domain_multi_label(self):
        self.assertEqual(validate_dns_config(_make_config(dns_domain="compute.hpc.lab")), [])

    def test_invalid_domain_uppercase(self):
        errs = validate_dns_config(_make_config(dns_domain="HPC.Cluster"))
        self.assertTrue(_has_error(errs, "dns_domain"))

    def test_invalid_domain_underscore(self):
        errs = validate_dns_config(_make_config(dns_domain="hpc_cluster"))
        self.assertTrue(_has_error(errs, "dns_domain"))

    def test_invalid_domain_empty(self):
        errs = validate_dns_config(_make_config(dns_domain=""))
        self.assertTrue(_has_error(errs, "dns_domain"))

    def test_reserved_domain_cluster_local(self):
        errs = validate_dns_config(_make_config(dns_domain="cluster.local"))
        self.assertTrue(_has_error_msg(errs, "reserved"))

    def test_reserved_domain_localhost(self):
        errs = validate_dns_config(_make_config(dns_domain="localhost"))
        self.assertTrue(_has_error_msg(errs, "reserved"))

    def test_reserved_domain_com(self):
        errs = validate_dns_config(_make_config(dns_domain="com"))
        self.assertTrue(_has_error_msg(errs, "reserved"))

    def test_subdomain_of_reserved(self):
        errs = validate_dns_config(_make_config(dns_domain="hpc.cluster.local"))
        self.assertTrue(_has_error_msg(errs, "reserved"))


if __name__ == "__main__":
    unittest.main()
