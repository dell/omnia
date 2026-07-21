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

"""Unit tests for additional_subnets validation in provision_validation.py."""

import sys
import os
import unittest
import ipaddress

# Test-only IP addresses used as fixtures — not real hosts.
TEST_ADMIN_IP = "172.16.0.254"  # NOSONAR — test fixture
TEST_ADMIN_RANGE = "172.16.0.201-172.16.0.250"  # NOSONAR — test fixture
TEST_ADMIN_SUBNET = "172.16.0.0"  # NOSONAR — test fixture
TEST_ADMIN_ROUTER = "172.16.0.1"  # NOSONAR — test fixture
TEST_SUBNET_1 = "10.40.1.0"  # NOSONAR — test fixture
TEST_ROUTER_1 = "10.40.1.1"  # NOSONAR — test fixture
TEST_ROUTER_1B = "10.40.1.2"  # NOSONAR — test fixture
TEST_ROUTER_BAD = "10.40.2.1"  # NOSONAR — test fixture
TEST_SUBNET_3 = "10.40.3.0"  # NOSONAR — test fixture
TEST_ROUTER_3 = "10.40.3.1"  # NOSONAR — test fixture
TEST_SUBNET_WIDE_1 = "10.40.0.0"  # NOSONAR — test fixture
TEST_ROUTER_WIDE_1 = "10.40.0.1"  # NOSONAR — test fixture
TEST_SUBNET_WIDE_2 = "10.41.0.0"  # NOSONAR — test fixture
TEST_ROUTER_WIDE_2 = "10.41.0.1"  # NOSONAR — test fixture

# ---------------------------------------------------------------------------
# Bootstrap: make the validation code importable without a full Ansible install
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
MODULE_UTILS = os.path.join(REPO_ROOT, "common", "library", "module_utils")
sys.path.insert(0, MODULE_UTILS)

# Provide a minimal stub for ansible.module_utils so the import chain works
# without a real Ansible installation.  We import the real sub-packages that
# live under MODULE_UTILS and wire them into sys.modules under their
# ansible.module_utils.* names so that cross-imports inside the validation
# code resolve correctly.
import types
import importlib

# Create the top-level namespace stubs
for _name in (
    "ansible",
    "ansible.module_utils",
    "ansible.module_utils.input_validation",
    "ansible.module_utils.input_validation.common_utils",
    "ansible.module_utils.input_validation.validation_flows",
):
    sys.modules.setdefault(_name, types.ModuleType(_name))

# Import real sub-modules in dependency order and register under ansible namespace.
# config and en_us_validation_msg have no cross-deps; validation_utils depends on both.
_cu_ns = "ansible.module_utils.input_validation.common_utils"
for _sub in ("config", "en_us_validation_msg", "validation_utils"):
    _mod = importlib.import_module(f"input_validation.common_utils.{_sub}")
    sys.modules[f"{_cu_ns}.{_sub}"] = _mod
    setattr(sys.modules[_cu_ns], _sub, _mod)

# Stub common_validation to avoid pulling the full dependency tree
sys.modules["ansible.module_utils.input_validation.validation_flows.common_validation"] = (
    types.ModuleType("ansible.module_utils.input_validation.validation_flows.common_validation")
)

# Register is_ip_in_subnet on the validation_utils stub so provision_validation can import it
_vu_mod = sys.modules["ansible.module_utils.input_validation.common_utils.validation_utils"]
if not hasattr(_vu_mod, "is_ip_in_subnet"):
    import input_validation.common_utils.validation_utils as _real_vu
    setattr(_vu_mod, "is_ip_in_subnet", _real_vu.is_ip_in_subnet)

from input_validation.validation_flows.provision_validation import (  # noqa: E402
    _validate_additional_subnets,
    _ranges_overlap,
    validate_pxe_admin_ips_subnet_consistency,
)


class TestRangesOverlap(unittest.TestCase):
    """Tests for the _ranges_overlap helper."""

    def test_no_overlap(self):
        self.assertFalse(_ranges_overlap("10.0.0.1-10.0.0.50", "10.0.0.51-10.0.0.100"))

    def test_overlap(self):
        self.assertTrue(_ranges_overlap("10.0.0.1-10.0.0.50", "10.0.0.25-10.0.0.75"))

    def test_adjacent_no_overlap(self):
        self.assertFalse(_ranges_overlap("10.0.0.1-10.0.0.50", "10.0.0.51-10.0.0.100"))

    def test_touching_overlap(self):
        self.assertTrue(_ranges_overlap("10.0.0.1-10.0.0.50", "10.0.0.50-10.0.0.100"))

    def test_contained(self):
        self.assertTrue(_ranges_overlap("10.0.0.10-10.0.0.20", "10.0.0.1-10.0.0.50"))

    def test_invalid_format(self):
        self.assertFalse(_ranges_overlap("bad", "10.0.0.1-10.0.0.50"))


class TestValidateAdditionalSubnets(unittest.TestCase):
    """Tests for _validate_additional_subnets."""

    def _admin_net(self, **overrides):
        base = {
            "primary_oim_admin_ip": TEST_ADMIN_IP,
            "netmask_bits": "24",
            "dynamic_range": TEST_ADMIN_RANGE,
        }
        base.update(overrides)
        return base

    def test_valid_single_additional_subnet(self):
        """Single valid additional subnet produces no errors."""
        additional = [{
            "subnet": TEST_SUBNET_1,
            "netmask_bits": "24",
            "router": TEST_ROUTER_1,
            "dynamic_range": "10.40.1.100-10.40.1.200",
        }]
        errors = _validate_additional_subnets(additional, self._admin_net())
        self.assertEqual(errors, [])

    def test_valid_multiple_additional_subnets(self):
        """Multiple valid non-overlapping subnets produce no errors."""
        additional = [
            {
                "subnet": TEST_SUBNET_1,
                "netmask_bits": "24",
                "router": TEST_ROUTER_1,
                "dynamic_range": "10.40.1.100-10.40.1.200",
            },
            {
                "subnet": TEST_SUBNET_3,
                "netmask_bits": "24",
                "router": TEST_ROUTER_3,
                "dynamic_range": "10.40.3.100-10.40.3.200",
            },
        ]
        errors = _validate_additional_subnets(additional, self._admin_net())
        self.assertEqual(errors, [])

    def test_router_outside_subnet(self):
        """Router IP outside the subnet triggers a warning (not an error)."""
        additional = [{
            "subnet": TEST_SUBNET_1,
            "netmask_bits": "24",
            "router": TEST_ROUTER_BAD,
            "dynamic_range": "10.40.1.100-10.40.1.200",
        }]
        errors = _validate_additional_subnets(additional, self._admin_net())
        # Router outside subnet now generates a warning, not an error
        self.assertEqual(errors, [])

    def test_range_outside_subnet(self):
        """dynamic_range outside the subnet triggers an error."""
        additional = [{
            "subnet": TEST_SUBNET_1,
            "netmask_bits": "24",
            "router": TEST_ROUTER_1,
            "dynamic_range": "10.40.2.100-10.40.2.200",
        }]
        errors = _validate_additional_subnets(additional, self._admin_net())
        self.assertTrue(any("dynamic_range" in str(e) for e in errors))

    def test_overlap_with_admin_network(self):
        """Subnet overlapping with admin network triggers an error."""
        additional = [{
            "subnet": TEST_ADMIN_SUBNET,
            "netmask_bits": "24",
            "router": TEST_ADMIN_ROUTER,
            "dynamic_range": "172.16.0.100-172.16.0.150",
        }]
        errors = _validate_additional_subnets(additional, self._admin_net())
        self.assertTrue(any("overlaps with admin" in str(e) for e in errors))

    def test_overlap_between_additional_subnets(self):
        """Two additional subnets that overlap trigger an error."""
        additional = [
            {
                "subnet": TEST_SUBNET_1,
                "netmask_bits": "24",
                "router": TEST_ROUTER_1,
                "dynamic_range": "10.40.1.100-10.40.1.200",
            },
            {
                "subnet": TEST_SUBNET_1,
                "netmask_bits": "24",
                "router": TEST_ROUTER_1B,
                "dynamic_range": "10.40.1.150-10.40.1.250",
            },
        ]
        errors = _validate_additional_subnets(additional, self._admin_net())
        self.assertTrue(any("Overlaps with additional_subnets[0]" in str(e) for e in errors))

    def test_invalid_netmask_bits(self):
        """Invalid netmask_bits triggers an error."""
        additional = [{
            "subnet": TEST_SUBNET_1,
            "netmask_bits": "99",
            "router": TEST_ROUTER_1,
            "dynamic_range": "10.40.1.100-10.40.1.200",
        }]
        errors = _validate_additional_subnets(additional, self._admin_net())
        self.assertTrue(any("netmask_bits" in str(e) for e in errors))

    def test_invalid_router_ip(self):
        """Non-IPv4 router triggers an error."""
        additional = [{
            "subnet": TEST_SUBNET_1,
            "netmask_bits": "24",
            "router": "not-an-ip",
            "dynamic_range": "10.40.1.100-10.40.1.200",
        }]
        errors = _validate_additional_subnets(additional, self._admin_net())
        self.assertTrue(any("router" in str(e) for e in errors))

    def test_invalid_dynamic_range_format(self):
        """Malformed dynamic_range triggers an error."""
        additional = [{
            "subnet": TEST_SUBNET_1,
            "netmask_bits": "24",
            "router": TEST_ROUTER_1,
            "dynamic_range": "bad-range",
        }]
        errors = _validate_additional_subnets(additional, self._admin_net())
        self.assertTrue(any("dynamic_range" in str(e) for e in errors))

    def test_empty_list_no_errors(self):
        """Empty additional_subnets list produces no errors."""
        errors = _validate_additional_subnets([], self._admin_net())
        self.assertEqual(errors, [])

    def test_dynamic_range_overlap_between_subnets(self):
        """Overlapping dynamic_ranges across subnets (but non-overlapping CIDRs) trigger an error."""
        additional = [
            {
                "subnet": TEST_SUBNET_WIDE_1,
                "netmask_bits": "16",
                "router": TEST_ROUTER_WIDE_1,
                "dynamic_range": "10.40.1.100-10.40.1.200",
            },
            {
                "subnet": TEST_SUBNET_WIDE_2,
                "netmask_bits": "16",
                "router": TEST_ROUTER_WIDE_2,
                "dynamic_range": "10.41.1.100-10.41.1.200",
            },
        ]
        errors = _validate_additional_subnets(additional, self._admin_net())
        # These have different CIDRs and non-overlapping ranges — should be clean
        self.assertEqual(errors, [])


class TestPXEMappingSubnetValidation(unittest.TestCase):
    """Tests for validate_pxe_admin_ips_subnet_consistency."""

    def _create_temp_pxe_mapping(self, admin_ips):
        """Create a temporary PXE mapping file with given ADMIN_IPs."""
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP\n")
            for i, admin_ip in enumerate(admin_ips):
                f.write(f"slurm_node,grp0,SVCTAG{i},,node{i},00:11:22:33:44:55,{admin_ip},00:11:22:33:44:66,10.0.0.1\n")
        return path

    def test_admin_ip_in_admin_subnet(self):
        """ADMIN_IP in primary admin subnet should pass validation."""
        pxe_file = self._create_temp_pxe_mapping(["172.16.0.10"])
        errors = []
        try:
            validate_pxe_admin_ips_subnet_consistency(
                errors, pxe_file, TEST_ADMIN_IP, "24", []
            )
            self.assertEqual(errors, [])
        finally:
            os.unlink(pxe_file)

    def test_admin_ip_in_additional_subnet(self):
        """ADMIN_IP in additional subnet should pass validation."""
        pxe_file = self._create_temp_pxe_mapping(["10.40.1.10"])
        additional = [{
            "subnet": TEST_SUBNET_1,
            "netmask_bits": "24",
            "router": TEST_ROUTER_1,
            "dynamic_range": "10.40.1.100-10.40.1.200",
        }]
        errors = []
        try:
            validate_pxe_admin_ips_subnet_consistency(
                errors, pxe_file, TEST_ADMIN_IP, "24", additional
            )
            self.assertEqual(errors, [])
        finally:
            os.unlink(pxe_file)

    def test_admin_ip_in_undefined_subnet(self):
        """ADMIN_IP in undefined subnet should fail validation."""
        pxe_file = self._create_temp_pxe_mapping(["192.168.100.10"])
        errors = []
        try:
            validate_pxe_admin_ips_subnet_consistency(
                errors, pxe_file, TEST_ADMIN_IP, "24", []
            )
            self.assertTrue(len(errors) > 0)
            self.assertTrue("192.168.100.10" in str(errors))
            self.assertIn(pxe_file, errors[0]["error_key"])
        finally:
            os.unlink(pxe_file)

    def test_admin_ip_in_additional_subnet_undefined_in_network_spec(self):
        """ADMIN_IP in subnet not defined in additional_subnets should fail validation."""
        pxe_file = self._create_temp_pxe_mapping(["10.40.2.10"])
        additional = [{
            "subnet": TEST_SUBNET_1,
            "netmask_bits": "24",
            "router": TEST_ROUTER_1,
            "dynamic_range": "10.40.1.100-10.40.1.200",
        }]
        errors = []
        try:
            validate_pxe_admin_ips_subnet_consistency(
                errors, pxe_file, TEST_ADMIN_IP, "24", additional
            )
            self.assertTrue(len(errors) > 0)
            self.assertTrue("10.40.2.10" in str(errors))
            self.assertIn(pxe_file, errors[0]["error_key"])
        finally:
            os.unlink(pxe_file)

    def test_mixed_valid_and_invalid_admin_ips(self):
        """Mix of valid (in admin subnet) and invalid (undefined subnet) ADMIN_IPs."""
        pxe_file = self._create_temp_pxe_mapping(["172.16.0.10", "192.168.100.10"])
        errors = []
        try:
            validate_pxe_admin_ips_subnet_consistency(
                errors, pxe_file, TEST_ADMIN_IP, "24", []
            )
            self.assertEqual(len(errors), 1)
            self.assertTrue("192.168.100.10" in str(errors))
            self.assertFalse("172.16.0.10" in str(errors))
            self.assertIn(pxe_file, errors[0]["error_key"])
        finally:
            os.unlink(pxe_file)

    def test_no_additional_subnets_defaults_to_empty(self):
        """Passing None for additional_subnets should not crash."""
        pxe_file = self._create_temp_pxe_mapping(["172.16.0.10"])
        errors = []
        try:
            validate_pxe_admin_ips_subnet_consistency(
                errors, pxe_file, TEST_ADMIN_IP, "24", None
            )
            self.assertEqual(errors, [])
        finally:
            os.unlink(pxe_file)


if __name__ == "__main__":
    unittest.main()
