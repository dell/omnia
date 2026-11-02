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

"""Unit tests for Build Image value objects."""

import pytest

from core.build_image.value_objects import (
    Architecture,
    ImageKey,
    FunctionalGroups,
    InventoryHost,
)


class TestArchitecture:
    """Test cases for Architecture value object."""

    def test_valid_x86_64(self):
        """Test creating valid x86_64 architecture."""
        arch = Architecture("x86_64")
        assert str(arch) == "x86_64"
        assert arch.is_x86_64
        assert not arch.is_aarch64

    def test_valid_aarch64(self):
        """Test creating valid aarch64 architecture."""
        arch = Architecture("aarch64")
        assert str(arch) == "aarch64"
        assert arch.is_aarch64
        assert not arch.is_x86_64

    def test_invalid_empty(self):
        """Test that empty architecture raises ValueError."""
        with pytest.raises(ValueError, match="Architecture cannot be empty"):
            Architecture("")

    def test_invalid_whitespace(self):
        """Test that whitespace-only architecture raises ValueError."""
        with pytest.raises(ValueError, match="Architecture cannot be empty"):
            Architecture("   ")

    def test_unsupported_architecture(self):
        """Test that unsupported architecture raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported architecture: arm64"):
            Architecture("arm64")

    def test_case_sensitive(self):
        """Test that architecture is case sensitive."""
        with pytest.raises(ValueError, match="Unsupported architecture: X86_64"):
            Architecture("X86_64")


class TestImageKey:
    """Test cases for ImageKey value object."""

    def test_valid_simple_key(self):
        """Test creating valid simple image key."""
        key = ImageKey("my-image")
        assert str(key) == "my-image"

    def test_valid_complex_key(self):
        """Test creating valid complex image key."""
        key = ImageKey("test_image_123-v2")
        assert str(key) == "test_image_123-v2"

    def test_valid_max_length(self):
        """Test creating image key with maximum allowed length."""
        key = ImageKey("a" * 128)
        assert len(str(key)) == 128

    def test_invalid_empty(self):
        """Test that empty image key raises ValueError."""
        with pytest.raises(ValueError, match="Image key cannot be empty"):
            ImageKey("")

    def test_invalid_too_long(self):
        """Test that too long image key raises ValueError."""
        with pytest.raises(ValueError, match="Image key length cannot exceed 128"):
            ImageKey("a" * 129)

    def test_invalid_characters(self):
        """Test that invalid characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid image key format"):
            ImageKey("my@image")

    def test_invalid_space(self):
        """Test that space in image key raises ValueError."""
        with pytest.raises(ValueError, match="Invalid image key format"):
            ImageKey("my image")


class TestFunctionalGroups:
    """Test cases for FunctionalGroups value object."""

    def test_valid_single_group(self):
        """Test creating valid single functional group."""
        groups = FunctionalGroups(["slurm_control_node"])
        assert groups.to_list() == ["slurm_control_node"]

    def test_valid_multiple_groups(self):
        """Test creating valid multiple functional groups."""
        groups = FunctionalGroups(["slurm_control_node", "slurm_node", "login_node"])
        assert groups.to_list() == ["slurm_control_node", "slurm_node", "login_node"]

    def test_valid_max_groups(self):
        """Test creating maximum allowed functional groups."""
        groups = FunctionalGroups([f"group_{i}" for i in range(50)])
        assert len(groups.to_list()) == 50

    def test_invalid_empty(self):
        """Test that empty functional groups raises ValueError."""
        with pytest.raises(ValueError, match="Functional groups cannot be empty"):
            FunctionalGroups([])

    def test_invalid_too_many(self):
        """Test that too many functional groups raises ValueError."""
        with pytest.raises(ValueError, match="Functional groups cannot exceed 50"):
            FunctionalGroups([f"group_{i}" for i in range(51)])

    def test_invalid_empty_group(self):
        """Test that empty group name raises ValueError."""
        with pytest.raises(ValueError, match="Functional group name cannot be empty"):
            FunctionalGroups(["valid_group", ""])

    def test_invalid_group_characters(self):
        """Test that invalid group characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid functional group name"):
            FunctionalGroups(["valid_group", "invalid@group"])

    def test_immutable_list(self):
        """Test that returned list is a copy."""
        groups = FunctionalGroups(["group1", "group2"])
        list_copy = groups.to_list()
        list_copy.append("group3")
        assert len(groups.to_list()) == 2


class TestInventoryHost:
    """Test cases for InventoryHost value object."""

    def test_valid_ip_address(self):
        """Test creating valid IP address."""
        host = InventoryHost("192.168.1.100")
        assert str(host) == "192.168.1.100"

    def test_valid_hostname(self):
        """Test creating valid hostname."""
        host = InventoryHost("node-01.example.com")
        assert str(host) == "node-01.example.com"

    def test_valid_max_length(self):
        """Test creating host with maximum allowed length."""
        host = InventoryHost("a" * 255)
        assert len(str(host)) == 255

    def test_invalid_empty(self):
        """Test that empty host raises ValueError."""
        with pytest.raises(ValueError, match="Inventory host cannot be empty"):
            InventoryHost("")

    def test_invalid_too_long(self):
        """Test that too long host raises ValueError."""
        with pytest.raises(ValueError, match="Inventory host length cannot exceed 255"):
            InventoryHost("a" * 256)

    def test_invalid_characters(self):
        """Test that invalid characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid inventory host format"):
            InventoryHost("192.168.1.100/24")

    def test_invalid_underscore(self):
        """Test that underscore in host raises ValueError."""
        with pytest.raises(ValueError, match="Invalid inventory host format"):
            InventoryHost("node_01.example.com")
