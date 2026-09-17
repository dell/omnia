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
"""Unit tests for discovery_config_validator (L2 semantic validation).

The discovery validation modules use relative imports, so we bootstrap
the entire ``discovery_validation`` package hierarchy before importing
the validator and engine under test.
"""

# pylint: disable=missing-function-docstring,redefined-outer-name

import importlib
import logging
import sys
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
VALIDATION_ROOT = (
    REPO_ROOT
    / "src/discovery/plugins/module_utils/discovery_validation"
)
LOGGER = logging.getLogger(__name__)


def _bootstrap_validation_package():
    """Register the discovery_validation package tree in sys.modules.

    This lets the validator and engine resolve their relative imports
    (``from ..messages.discovery_messages import ...``) without
    installing the package.
    """
    pkg_name = "discovery_validation"
    if pkg_name in sys.modules:
        return

    # Root package
    root_pkg = types.ModuleType(pkg_name)
    root_pkg.__path__ = [str(VALIDATION_ROOT)]
    root_pkg.__package__ = pkg_name
    sys.modules[pkg_name] = root_pkg

    # Sub-packages
    for sub in ("core", "messages", "validators"):
        sub_path = VALIDATION_ROOT / sub
        sub_full = f"{pkg_name}.{sub}"
        sub_pkg = types.ModuleType(sub_full)
        sub_pkg.__path__ = [str(sub_path)]
        sub_pkg.__package__ = sub_full
        sys.modules[sub_full] = sub_pkg
        setattr(root_pkg, sub, sub_pkg)

    # Load messages module
    msgs_spec = importlib.util.spec_from_file_location(
        f"{pkg_name}.messages.discovery_messages",
        VALIDATION_ROOT / "messages" / "discovery_messages.py",
    )
    msgs_mod = importlib.util.module_from_spec(msgs_spec)
    msgs_mod.__package__ = f"{pkg_name}.messages"
    sys.modules[f"{pkg_name}.messages.discovery_messages"] = msgs_mod
    msgs_spec.loader.exec_module(msgs_mod)

    # Load engine module
    engine_spec = importlib.util.spec_from_file_location(
        f"{pkg_name}.core.validation_engine",
        VALIDATION_ROOT / "core" / "validation_engine.py",
    )
    engine_mod = importlib.util.module_from_spec(engine_spec)
    engine_mod.__package__ = f"{pkg_name}.core"
    sys.modules[f"{pkg_name}.core.validation_engine"] = engine_mod
    engine_spec.loader.exec_module(engine_mod)

    # Load validator module
    val_spec = importlib.util.spec_from_file_location(
        f"{pkg_name}.validators.discovery_config_validator",
        VALIDATION_ROOT / "validators" / "discovery_config_validator.py",
    )
    val_mod = importlib.util.module_from_spec(val_spec)
    val_mod.__package__ = f"{pkg_name}.validators"
    sys.modules[f"{pkg_name}.validators.discovery_config_validator"] = val_mod
    val_spec.loader.exec_module(val_mod)


_bootstrap_validation_package()

# Now safe to import the modules under test
from discovery_validation.core.validation_engine import (  # noqa: E402
    run_validation,
    is_valid_ipv4,
    load_yaml_file,
)
from discovery_validation.validators.discovery_config_validator import (  # noqa: E402
    validate,
)


# ─── L2 Semantic Validator Tests ─────────────────────────────────────────────


@pytest.fixture
def valid_config():
    """Return a valid discovery config for L2 validation."""
    return {"ome_ip": "192.168.1.100"}


def test_valid_config_passes_l2(valid_config):
    errors = []
    validate(valid_config, errors, LOGGER)
    assert not errors


def test_missing_ome_ip_fails():
    errors = []
    validate({}, errors, LOGGER)
    assert errors
    assert any("ome_ip" in e for e in errors)


def test_empty_ome_ip_fails():
    errors = []
    validate({"ome_ip": ""}, errors, LOGGER)
    assert errors


def test_loopback_ip_fails():
    errors = []
    validate({"ome_ip": "127.0.0.1"}, errors, LOGGER)
    assert errors
    assert any("loopback" in e.lower() for e in errors)


def test_non_ipv4_string_fails():
    errors = []
    validate({"ome_ip": "not-an-ip"}, errors, LOGGER)
    assert errors
    assert any("not a valid" in e.lower() for e in errors)


@pytest.mark.parametrize(
    "ip",
    ["10.0.0.1", "172.16.0.1", "192.168.100.50"],
)
def test_valid_private_ips_pass(ip):
    errors = []
    validate({"ome_ip": ip}, errors, LOGGER)
    assert not errors


def test_non_string_ome_ip_fails():
    errors = []
    validate({"ome_ip": 12345}, errors, LOGGER)
    assert errors


def test_ipv6_address_fails():
    errors = []
    validate({"ome_ip": "::1"}, errors, LOGGER)
    assert errors


# ─── Engine Utility Tests ────────────────────────────────────────────────────


def test_engine_run_validation_collects_errors():
    """Verify the engine dispatches validator and collects errors."""
    errors = run_validation(
        config_file="discovery_config.yml",
        config_data={"ome_ip": ""},
        validators=[validate],
        logger=LOGGER,
    )
    assert errors


def test_engine_run_validation_passes_valid():
    """Verify the engine returns no errors for valid config."""
    errors = run_validation(
        config_file="discovery_config.yml",
        config_data={"ome_ip": "10.0.0.1"},
        validators=[validate],
        logger=LOGGER,
    )
    assert not errors


def test_is_valid_ipv4_accepts_valid():
    assert is_valid_ipv4("192.168.1.1")


def test_is_valid_ipv4_rejects_invalid():
    assert not is_valid_ipv4("not-an-ip")


def test_is_valid_ipv4_rejects_ipv6():
    assert not is_valid_ipv4("::1")
