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
            "dns_ttl": 300,
            "dns_reverse_enabled": True,
            "dns_fabric_suffixes": [],
            "dns_cache_ttl": 60,
            "dns_soa": {
                "refresh": 3600,
                "retry": 600,
                "expire": 86400,
            },
        }
    }
    cfg = base["dns_config"]
    for k, v in overrides.items():
        if k.startswith("soa_"):
            cfg["dns_soa"][k[4:]] = v
        else:
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


class TestDnsTtlValidation(unittest.TestCase):
    """FS-INPUT-02: dns_ttl must be in [60, 86400]."""

    def test_valid_ttl(self):
        self.assertEqual(validate_dns_config(_make_config(dns_ttl=300)), [])

    def test_ttl_minimum(self):
        self.assertEqual(validate_dns_config(_make_config(dns_ttl=60)), [])

    def test_ttl_maximum(self):
        self.assertEqual(validate_dns_config(_make_config(dns_ttl=86400)), [])

    def test_ttl_too_low(self):
        errs = validate_dns_config(_make_config(dns_ttl=59))
        self.assertTrue(_has_error(errs, "dns_ttl"))

    def test_ttl_too_high(self):
        errs = validate_dns_config(_make_config(dns_ttl=86401))
        self.assertTrue(_has_error(errs, "dns_ttl"))


class TestDnsCacheTtlValidation(unittest.TestCase):
    """FS-INPUT-03: dns_cache_ttl must be in [10, 3600] and <= dns_ttl."""

    def test_valid_cache_ttl(self):
        self.assertEqual(validate_dns_config(_make_config(dns_cache_ttl=60)), [])

    def test_cache_ttl_minimum(self):
        self.assertEqual(validate_dns_config(_make_config(dns_cache_ttl=10)), [])

    def test_cache_ttl_maximum(self):
        self.assertEqual(validate_dns_config(_make_config(dns_cache_ttl=300, dns_ttl=300)), [])

    def test_cache_ttl_too_low(self):
        errs = validate_dns_config(_make_config(dns_cache_ttl=9))
        self.assertTrue(_has_error(errs, "dns_cache_ttl"))

    def test_cache_ttl_too_high(self):
        errs = validate_dns_config(_make_config(dns_cache_ttl=3601))
        self.assertTrue(_has_error(errs, "dns_cache_ttl"))

    def test_cache_ttl_exceeds_ttl(self):
        errs = validate_dns_config(_make_config(dns_ttl=60, dns_cache_ttl=120))
        self.assertTrue(_has_error(errs, "dns_cache_ttl"))


class TestDnsFabricSuffixValidation(unittest.TestCase):
    """FS-INPUT-04: fabric suffixes must be hyphen-prefixed lowercase."""

    def test_valid_suffix(self):
        self.assertEqual(validate_dns_config(_make_config(dns_fabric_suffixes=["-ib"])), [])

    def test_valid_suffix_multi(self):
        self.assertEqual(
            validate_dns_config(_make_config(dns_fabric_suffixes=["-ib", "-stor"])), []
        )

    def test_invalid_suffix_no_hyphen(self):
        errs = validate_dns_config(_make_config(dns_fabric_suffixes=["ib"]))
        self.assertTrue(_has_error(errs, "dns_fabric_suffix"))

    def test_invalid_suffix_uppercase(self):
        errs = validate_dns_config(_make_config(dns_fabric_suffixes=["-IB"]))
        self.assertTrue(_has_error(errs, "dns_fabric_suffix"))

    def test_invalid_suffix_empty_after_hyphen(self):
        errs = validate_dns_config(_make_config(dns_fabric_suffixes=["-"]))
        self.assertTrue(_has_error(errs, "dns_fabric_suffix"))

    def test_empty_suffixes_ok(self):
        self.assertEqual(validate_dns_config(_make_config(dns_fabric_suffixes=[])), [])


class TestDnsSoaValidation(unittest.TestCase):
    """FS-SOA-01..05: SOA values must be positive integers."""

    def test_valid_soa(self):
        self.assertEqual(validate_dns_config(_make_config()), [])

    def test_soa_refresh_zero(self):
        errs = validate_dns_config(_make_config(soa_refresh=0))
        self.assertTrue(_has_error(errs, "dns_soa"))

    def test_soa_retry_negative(self):
        errs = validate_dns_config(_make_config(soa_retry=-1))
        self.assertTrue(_has_error(errs, "dns_soa"))

    def test_soa_expire_zero(self):
        errs = validate_dns_config(_make_config(soa_expire=0))
        self.assertTrue(_has_error(errs, "dns_soa"))


if __name__ == "__main__":
    unittest.main()
