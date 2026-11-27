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

"""Unit tests for container image digest pinning in telemetry_packages.yml.

Every image in the package manifest must be ``<name>:<tag>@sha256:<64 hex>``
so a moved tag or a compromised registry cannot change what is deployed.
"""

import copy
import importlib
import logging
import os

import ansible.module_utils
import pytest
import yaml

_MODULE_UTILS = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..",
        "src", "telemetry", "plugins", "module_utils",
    )
)
_MANIFEST = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..",
        "src", "telemetry", "input", "telemetry_packages.yml",
    )
)
# The validator imports collection module_utils as ansible.module_utils.*;
# extend that package path (same approach as test_vault_in_memory_read.py).
if _MODULE_UTILS not in ansible.module_utils.__path__:
    ansible.module_utils.__path__.insert(0, _MODULE_UTILS)

telemetry_validation = importlib.import_module(
    "ansible.module_utils.input_validation.validators.telemetry_validation"
)

with open(_MANIFEST, "r", encoding="utf-8") as _manifest:
    _PACKAGES = yaml.safe_load(_manifest)
_IMAGES = _PACKAGES["images"]
_ALL_REFS = {
    f"images.{group}.{key}": ref
    for group, entries in _IMAGES.items()
    for key, ref in entries.items()
}


def _split(ref):
    """'<name>:<tag>@sha256:<hex>' -> (name, tag, hex)."""
    name_tag, digest = ref.split("@sha256:")
    name, tag = name_tag.rsplit(":", 1)
    return name, tag, digest


def _unpinned_variants(ref):
    """Tag-only, :latest, digest-only, short/uppercase/non-sha256 digest, no registry, trailing space."""
    name, tag, digest = _split(ref)
    return [
        f"{name}:{tag}",
        f"{name}:latest@sha256:{digest}",
        f"{name}@sha256:{digest}",
        f"{name}:{tag}@sha256:{digest[:6]}",
        f"{name}:{tag}@sha256:{digest.upper()}",
        f"{name}:{tag}@sha512:{digest * 2}",
        f"{name.split('/')[-1]}:{tag}@sha256:{digest}",
        f"{ref} ",
    ]


def test_shipped_manifest_images_are_digest_pinned():
    """Every image shipped in telemetry_packages.yml carries an @sha256 digest."""
    assert _ALL_REFS, "manifest must declare images"
    assert telemetry_validation._image_digest_errors(_IMAGES) == []  # pylint: disable=protected-access


@pytest.mark.parametrize("ref", _unpinned_variants(_IMAGES["victoria_metrics"]["vmagent"]))
def test_unpinned_or_malformed_images_are_rejected(ref):
    """Unpinned or malformed variants of a shipped image are rejected."""
    images = {"victoria_metrics": {"vmagent": ref}}
    errors = telemetry_validation._image_digest_errors(images)  # pylint: disable=protected-access
    assert errors == [("images.victoria_metrics.vmagent", ref)]


@pytest.mark.parametrize("path", sorted(_ALL_REFS))
def test_pinned_images_are_accepted(path):
    """Shipped images stay valid after container_registry (host:port) is applied to them."""
    name, tag, digest = _split(_ALL_REFS[path])
    repository = name.split("/", 1)[1] if "." in name.split("/")[0] else name
    mirrored = f"registry.example:5000/{repository}:{tag}@sha256:{digest}"
    images = {"group": {"image": mirrored}, "empty": {"unset": ""}}
    assert telemetry_validation._image_digest_errors(images) == []  # pylint: disable=protected-access


def test_validate_telemetry_packages_reports_unpinned_image(tmp_path):
    """L2 validation of the shipped telemetry_packages.yml flags only the image that loses its digest."""
    data = copy.deepcopy(_PACKAGES)
    group, key = next((g, k) for g, entries in data["images"].items() for k in entries)
    data["images"][group][key] = data["images"][group][key].split("@")[0]
    errors = telemetry_validation.validate_telemetry_packages(
        str(tmp_path / "telemetry_packages.yml"), data,
        logging.getLogger("test"), None, str(tmp_path), _MODULE_UTILS, "project_default",
    )
    messages = [str(error) for error in errors]
    assert any(f"images.{group}.{key}" in message for message in messages), messages
    untouched = [path for path in _ALL_REFS if path != f"images.{group}.{key}"]
    assert not any(path in message for path in untouched for message in messages), messages
