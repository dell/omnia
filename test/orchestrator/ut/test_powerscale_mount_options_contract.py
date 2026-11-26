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

"""Contracts for csi_powerscale_mount_options validation and nfsmount.conf rendering."""

import json
import logging
import sys
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from jsonschema import Draft7Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_ROOT = REPO_ROOT / "src" / "orchestrator"
SOURCE_PLUGIN_ROOT = ORCHESTRATOR_ROOT / "plugins"
if str(SOURCE_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_PLUGIN_ROOT))

from module_utils.orchestrator_validation.validators import (  # noqa: E402
    omnia_config_validator as validator,
)

SCHEMA_PATH = (
    ORCHESTRATOR_ROOT
    / "plugins/module_utils/orchestrator_validation/schema/omnia_config.json"
)
K8S_CONFIG_ROLE = ORCHESTRATOR_ROOT / "roles" / "k8s_config"
TEMPLATE_NAME = "ps_nfsmount_conf.j2"
HEADER = "[ NFSMount_Global_Options ]"
LOGGER = logging.getLogger("powerscale-mount-options-test")
BASE_CLUSTER = {
    "cluster_name": "service",
    "deployment": True,
    "etcd_on_local_disk": False,
    "k8s_cni": "calico",
    "pod_external_ip_range": "192.0.2.0/24",
    "k8s_service_addresses": "10.96.0.0/12",
    "k8s_pod_network_cidr": "10.244.0.0/16",
    "nfs_storage_name": "nfs",
    "k8s_crio_storage_size": "100G",
}


def _default_mount_options():
    """Return csi_powerscale_default_mount_options from the k8s_config role vars."""
    role_vars = yaml.safe_load(
        (K8S_CONFIG_ROLE / "vars" / "main.yml").read_text(encoding="utf-8")
    )
    return role_vars["csi_powerscale_default_mount_options"]


def _validate(mount_options):
    """Run the L2 rsize/wsize check and return the recorded errors."""
    errors = []
    validator._validate_powerscale_mount_options(
        "service", mount_options, errors, LOGGER
    )
    return errors


def _schema_errors(mount_options):
    """Validate a cluster entry carrying mount_options against the schema."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    cluster_schema = {
        "$ref": "#/definitions/serviceK8sCluster",
        "definitions": schema["definitions"],
    }
    checker = Draft7Validator(cluster_schema, format_checker=FormatChecker())
    return list(
        checker.iter_errors(
            {**BASE_CLUSTER, "csi_powerscale_mount_options": mount_options}
        )
    )


def _render(mount_options):
    """Render ps_nfsmount_conf.j2 the way create_k8s_config_nfs.yml feeds it."""
    env = Environment(
        loader=FileSystemLoader(str(K8S_CONFIG_ROLE / "templates")),
        trim_blocks=True,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    options = [option for option in mount_options.split(",") if option]
    rendered = env.get_template(TEMPLATE_NAME).render(
        csi_powerscale_mount_options=options
    )
    lines = [
        line for line in rendered.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    return lines


@pytest.mark.parametrize(
    "mount_options",
    [
        "rsize=1044480,wsize=1044480,nosharecache",
        "rsize=524288,wsize=524288",
        "rsize=1,wsize=1048575",
        " rsize = 1044480 , wsize = 1044480 ",
        "nosharecache,hard",
        "",
        None,
    ],
)
def test_valid_transfer_sizes_pass(mount_options):
    """ORCH_UT_180: Whole-number rsize/wsize in (0, 1 MiB) or no size passes."""
    assert not _validate(mount_options)


@pytest.mark.parametrize(
    ("mount_options", "option", "value"),
    [
        ("rsize=0,wsize=1044480", "rsize", "0"),
        ("rsize=1044480,wsize=0", "wsize", "0"),
        ("rsize=1048576,wsize=1044480", "rsize", "1048576"),
        ("rsize=1044480,wsize=2097152", "wsize", "2097152"),
        ("rsize=abc,wsize=1044480", "rsize", "abc"),
        ("rsize=1044480,wsize=-1", "wsize", "-1"),
        ("rsize=1.5,wsize=1044480", "rsize", "1.5"),
        ("rsize=,wsize=1044480", "rsize", ""),
        ("rsize,wsize=1044480", "rsize", ""),
    ],
)
def test_invalid_transfer_sizes_are_rejected(mount_options, option, value):
    """ORCH_UT_181: Zero, >= 1 MiB, non-numeric and empty sizes are rejected."""
    errors = _validate(mount_options)
    assert len(errors) == 1
    assert f"{option}='{value}' is invalid" in errors[0]
    assert "1048576" in errors[0]


def test_both_invalid_sizes_are_reported():
    """ORCH_UT_182: Each invalid size is reported in a single pass."""
    errors = _validate("rsize=0,wsize=1048576")
    assert len(errors) == 2
    assert "rsize='0'" in errors[0]
    assert "wsize='1048576'" in errors[1]


@pytest.mark.parametrize(
    ("mount_options", "is_valid"),
    [
        ("rsize=1044480,wsize=1044480,nosharecache", True),
        ("nosharecache", True),
        ("", True),
        ("rsize=1044480", False),
        ("wsize=1044480,nosharecache", False),
        ("rsize=1044480,wsize=1044480 nosharecache", False),
        ("rsize=1044480;wsize=1044480", False),
    ],
)
def test_schema_requires_rsize_wsize_pair(mount_options, is_valid):
    """ORCH_UT_183: The schema rejects rsize without wsize, the reverse, and bad characters."""
    assert (not _schema_errors(mount_options)) is is_valid


def test_shipped_defaults_are_valid():
    """ORCH_UT_184: Role default and omnia_config.yml sample pass schema and L2 checks."""
    omnia_config = yaml.safe_load(
        (ORCHESTRATOR_ROOT / "input" / "omnia_config.yml").read_text(encoding="utf-8")
    )
    sample = omnia_config["service_k8s_cluster"][0]["csi_powerscale_mount_options"]
    default = _default_mount_options()
    assert sample == default
    for mount_options in (default, sample):
        assert not _schema_errors(mount_options)
        assert not _validate(mount_options)


def test_template_renders_default_mount_options():
    """ORCH_UT_185: The role default renders to nfsmount.conf global options."""
    assert _render(_default_mount_options()) == [
        HEADER,
        "rsize=1044480",
        "wsize=1044480",
        "Sharecache=False",
    ]


@pytest.mark.parametrize(
    ("mount_options", "expected"),
    [
        ("rsize=524288,wsize=524288", ["rsize=524288", "wsize=524288"]),
        ("hard,noac", ["Hard=True", "Ac=False"]),
        ("vers=4.1,,nosharecache", ["vers=4.1", "Sharecache=False"]),
        ("", []),
    ],
)
def test_template_renders_option_forms(mount_options, expected):
    """ORCH_UT_186: key=value is kept, flags become True, no-flags become False."""
    assert _render(mount_options) == [HEADER, *expected]
