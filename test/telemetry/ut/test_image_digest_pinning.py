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

_DIGEST = "sha256:" + "a" * 64


def test_shipped_manifest_images_are_digest_pinned():
    """Every image shipped in telemetry_packages.yml carries an @sha256 digest."""
    with open(_MANIFEST, "r", encoding="utf-8") as manifest:
        images = yaml.safe_load(manifest)["images"]
    refs = [ref for group in images.values() for ref in group.values()]
    assert refs, "manifest must declare images"
    assert telemetry_validation._image_digest_errors(images) == []  # pylint: disable=protected-access


@pytest.mark.parametrize(
    "ref",
    [
        "docker.io/victoriametrics/vmagent:v1.153.0",
        "docker.io/library/busybox:latest@" + _DIGEST,
        "docker.io/victoriametrics/vmagent@" + _DIGEST,
        "docker.io/victoriametrics/vmagent:v1.153.0@sha256:abc123",
        "docker.io/victoriametrics/vmagent:v1.153.0@sha256:" + "A" * 64,
        "docker.io/victoriametrics/vmagent:v1.153.0@sha512:" + "a" * 128,
        "busybox:1.38@" + _DIGEST,
        "docker.io/victoriametrics/vmagent:v1.153.0@" + _DIGEST + " ",
    ],
)
def test_unpinned_or_malformed_images_are_rejected(ref):
    """Tag-only, :latest, digest-only, short/uppercase/non-sha256 digests are rejected."""
    images = {"victoria_metrics": {"vmagent": ref}}
    errors = telemetry_validation._image_digest_errors(images)  # pylint: disable=protected-access
    assert errors == [("images.victoria_metrics.vmagent", ref)]


@pytest.mark.parametrize(
    "ref",
    [
        "docker.io/victoriametrics/vmstorage:v1.153.0-cluster@" + _DIGEST,
        "quay.io/dell/container-storage-modules/csm-metrics-powerscale:v1.13.0@" + _DIGEST,
        "myregistry.local:5000/strimzi/kafka:1.2.0-kafka-4.3.1@" + _DIGEST,
        "ghcr.io/open-telemetry/opentelemetry-collector-releases/"
        "opentelemetry-collector:0.160.0@" + _DIGEST,
    ],
)
def test_pinned_images_are_accepted(ref):
    """Registry host:port, nested repository paths and suffixed tags are accepted."""
    images = {"group": {"image": ref}, "empty": {"unset": ""}}
    assert telemetry_validation._image_digest_errors(images) == []  # pylint: disable=protected-access


def test_validate_telemetry_packages_reports_unpinned_image(tmp_path):
    """L2 validation of telemetry_packages.yml returns an error for an unpinned image."""
    data = {
        "k8s_cluster_mount": "/opt/omnia/k8s_mount",
        "slurm_cluster_mount": "/share_omnia",
        "install_mode": "online",
        "images": {
            "support": {
                "busybox": "docker.io/library/busybox:1.38@" + _DIGEST,
                "kubectl": "docker.io/alpine/kubectl:1.35.1",
            }
        },
    }
    errors = telemetry_validation.validate_telemetry_packages(
        str(tmp_path / "telemetry_packages.yml"), data,
        logging.getLogger("test"), None, str(tmp_path), _MODULE_UTILS, "project_default",
    )
    messages = [str(error) for error in errors]
    assert any("images.support.kubectl" in message for message in messages), messages
    assert not any("images.support.busybox" in message for message in messages), messages
