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

"""Focused unit contracts for PXE parsers, features, and safety gates."""

import json
from types import SimpleNamespace

import pytest
from library.functions import _apptainer_helpers as apptainer
from library.functions import _pxeboot_helpers as helpers
from library.functions import _workload_helpers as workload
from library.functions import kubernetes_runtime_pxeboot_func as kubernetes_runtime
from library.functions import slurm_auth_pxeboot_func as slurm_auth
from library.functions import slurm_configuration_pxeboot_func as slurm_config
from library.functions import slurm_pxeboot_func as slurm


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("v1.31.4", "1.31"),
        ("Kubernetes v1.30.9+vendor", "1.30"),
        ("4.9", "4.9"),
        ("not-a-version", ""),
    ],
)
def test_version_parser_extracts_major_minor(value, expected):
    """ORCH_UT_001: Version parsing accepts product output and rejects noise."""
    assert kubernetes_runtime._major_minor(value) == expected


def test_version_skew_policy_is_directional():
    """ORCH_UT_002: Kubernetes version skew honors older/newer bounds."""
    server = (1, 31)
    assert kubernetes_runtime._within_minor_skew((1, 30), server, older=1, newer=0)
    assert not kubernetes_runtime._within_minor_skew((1, 32), server, older=1, newer=0)
    assert not kubernetes_runtime._within_minor_skew((2, 31), server, older=1, newer=0)


def test_slurm_node_and_config_hash_parsers_ignore_malformed_records():
    """ORCH_UT_003: Slurm parsers accept only complete, valid records."""
    nodes = slurm._parse_slurm_nodes(
        "NodeName=nid001 State=IDLE CPUTot=64 RealMemory=128000\n"
        "malformed line\n"
        "NodeName=nid002 State=ALLOCATED CPUTot=32 RealMemory=64000\n"
    )
    hashes = slurm_config._parse_config_hashes(
        "slurm|/etc/slurm/slurm.conf|"
        + ("a" * 64)
        + "\nbad|1234\ncgroup|/etc/slurm/cgroup.conf|"
        + ("b" * 64)
        + "\n"
    )
    assert set(nodes) == {"nid001", "nid002"}
    assert nodes["nid001"]["State"] == "IDLE"
    assert hashes == {
        "slurm": ("/etc/slurm/slurm.conf", "a" * 64),
        "cgroup": ("/etc/slurm/cgroup.conf", "b" * 64),
    }


def test_catalog_features_are_limited_to_mapped_functional_layers():
    """ORCH_UT_004: Unmapped catalog features cannot enable PXE checks."""
    catalog = {
        "functionallayer": [
            {
                "name": "slurm_node_rhel_10_0_x86_64",
                "components": ["slurm_runtime"],
            },
            {
                "name": "service_kube_node_rhel_10_0_x86_64",
                "components": ["gpu_runtime"],
            },
        ],
        "groups": {
            "slurm_runtime": {
                "name": "openmpi_ucx",
                "components": ["openmpi", "ucx"],
            },
            "gpu_runtime": {
                "name": "nvidia_cuda",
                "components": ["cuda"],
            },
        },
    }
    rows = [{"EXPECTED_FUNCTIONAL_GROUP": "slurm_node_rhel_10_0_x86_64"}]
    tokens = helpers._catalog_feature_tokens(catalog, rows)
    assert {"slurm_runtime", "openmpi_ucx", "openmpi", "ucx"} <= tokens
    assert "gpu_runtime" not in tokens
    assert "cuda" not in tokens


def test_first_control_plane_alias_selects_normal_control_plane_catalog_layer():
    """ORCH_UT_005: Generated first-control-plane roles resolve features."""
    catalog = {
        "functionallayer": [
            {
                "name": "service_kube_control_plane_rhel_10_0_x86_64",
                "components": ["kubernetes_runtime"],
            }
        ],
        "groups": {
            "kubernetes_runtime": {
                "name": "kubernetes_runtime",
                "components": ["crio"],
            }
        },
    }
    rows = [
        {
            "EXPECTED_FUNCTIONAL_GROUP": "service_kube_control_plane_first_rhel_10_0_x86_64"
        }
    ]
    assert "crio" in helpers._catalog_feature_tokens(catalog, rows)


def test_marker_authorization_requires_exact_explicit_selection(monkeypatch):
    """ORCH_UT_006: Mutation helpers trust only exact authorized markers."""
    monkeypatch.setenv(
        "OMNIA_FVT_AUTHORIZED_MARKERS",
        "functional,disruptive",
    )
    assert helpers.marker_is_authorized("functional")
    assert helpers.marker_is_authorized("disruptive")
    assert not helpers.marker_is_authorized("reboot")
    monkeypatch.delenv("OMNIA_FVT_AUTHORIZED_MARKERS")
    assert not helpers.marker_is_authorized("functional")


@pytest.mark.parametrize(
    ("payload", "expected", "detail"),
    [
        (
            {"status": "done", "extended_status": "done", "errors": []},
            True,
            "cloud-init done",
        ),
        (
            {
                "status": "done",
                "extended_status": "degraded done",
                "errors": [],
                "recoverable_errors": {"WARNING": ["Empty cloud config was provided"]},
            },
            True,
            "known empty-cloud-config warning",
        ),
        (
            {
                "status": "done",
                "extended_status": "degraded done",
                "errors": [],
                "recoverable_errors": {"WARNING": ["scripts_user failed"]},
            },
            False,
            "extended_status",
        ),
        (
            {
                "status": "error",
                "extended_status": "error",
                "errors": ["scripts_user failed"],
            },
            False,
            "status=error",
        ),
    ],
)
def test_cloud_init_interpretation(monkeypatch, payload, expected, detail):
    """ORCH_UT_007: Cloud-init accepts only the documented terminal states."""
    output = "status: done\nextended_status: done\n---JSON---\n" + json.dumps(payload)
    monkeypatch.setattr(
        helpers,
        "remote_command",
        lambda _host, _row, _command: SimpleNamespace(
            rc=0,
            stdout=output,
            stderr="",
        ),
    )
    success, message = helpers.direct_cloud_init_probe(
        object(),
        {"HOSTNAME": "nid001", "ADMIN_IP": "192.0.2.10"},
    )
    assert success is expected
    assert detail in message


def test_cloud_init_rejects_unstructured_output(monkeypatch):
    """ORCH_UT_008: Missing cloud-init JSON is a hard verification failure."""
    monkeypatch.setattr(
        helpers,
        "remote_command",
        lambda _host, _row, _command: SimpleNamespace(
            rc=0,
            stdout="status: done",
            stderr="",
        ),
    )
    success, detail = helpers.direct_cloud_init_probe(
        object(),
        {"HOSTNAME": "nid001", "ADMIN_IP": "192.0.2.10"},
    )
    assert not success
    assert "structured status" in detail


def test_slurm_shared_storage_resolves_authoritative_mount():
    """ORCH_UT_009: Slurm jobs use the storage selected by Omnia config."""
    context = {
        "storage_config": {
            "mounts": [
                {
                    "name": "nfs_slurm",
                    "source": "192.0.2.10:/exports/slurm",
                    "mount_point": "/mnt/slurm-shared",
                },
                {
                    "name": "nfs_k8s",
                    "source": "192.0.2.10:/exports/k8s",
                    "mount_point": "/mnt/k8s-shared",
                },
            ]
        }
    }
    resolved = workload.slurm_shared_storage(
        context,
        {"nfs_storage_name": "nfs_slurm"},
    )
    assert resolved == {
        "name": "nfs_slurm",
        "source": "192.0.2.10:/exports/slurm",
        "mount_point": "/mnt/slurm-shared",
    }


@pytest.mark.parametrize(
    "mounts",
    [
        [],
        [
            {
                "name": "nfs_slurm",
                "source": "192.0.2.10:/exports/a",
                "mount_point": "/mnt/a",
            },
            {
                "name": "nfs_slurm",
                "source": "192.0.2.10:/exports/b",
                "mount_point": "/mnt/b",
            },
        ],
    ],
)
def test_slurm_shared_storage_rejects_missing_or_duplicate_mounts(mounts):
    """ORCH_UT_010: Ambiguous Slurm storage fails before job submission."""
    with pytest.raises(ValueError, match="exactly one mount entry"):
        workload.slurm_shared_storage(
            {"storage_config": {"mounts": mounts}},
            {"nfs_storage_name": "nfs_slurm"},
        )


def test_apptainer_inventory_accepts_only_supported_sif_paths(monkeypatch):
    """ORCH_UT_011: SIF inventory rejects paths outside shared image storage."""
    monkeypatch.setattr(
        apptainer,
        "remote_command",
        lambda _host, _row, _command: SimpleNamespace(
            rc=0,
            stdout=(
                "/hpc_tools/container_images/valid.sif|644|4096|100.0\n"
                "/tmp/escape.sif|644|4096|100.0\n"
            ),
            stderr="",
        ),
    )
    assert apptainer.image_inventory(object(), {}) == [
        {
            "path": "/hpc_tools/container_images/valid.sif",
            "name": "valid.sif",
            "mode": "644",
            "size": 4096,
            "modified": 100.0,
        }
    ]


@pytest.mark.parametrize(
    "value",
    [
        # Unsafe-path rejection fixture.
        "/tmp/image.sif",  # nosec B108
        "/hpc_tools/container_images/../escape.sif",
        "/hpc_tools/container_images/image.sif;id",
    ],
)
def test_apptainer_image_path_validation_rejects_unsafe_values(value):
    """ORCH_UT_012: Container commands accept only fixed shared SIF paths."""
    with pytest.raises(ValueError, match="outside the supported directory"):
        apptainer.quoted_image(value)


def test_apptainer_primary_image_requires_one_nonempty_sif(monkeypatch):
    """ORCH_UT_013: Image-dependent checks cannot select an empty SIF."""
    monkeypatch.setattr(
        apptainer,
        "image_inventory",
        lambda _host, _row: [
            {
                "path": "/hpc_tools/container_images/empty.sif",
                "name": "empty.sif",
                "mode": "644",
                "size": 0,
                "modified": 100.0,
            }
        ],
    )
    with pytest.raises(FileNotFoundError, match="No usable SIF image"):
        apptainer.primary_image(object(), {})


@pytest.mark.parametrize(
    "checker",
    [
        slurm_auth.check_slurm_login_ldap_jobs,
        slurm_auth.check_slurm_login_pam_job_access,
        slurm_auth.check_slurm_compiler_ldap_jobs,
        slurm_auth.check_slurm_compiler_pam_job_access,
    ],
)
def test_unmapped_slurm_submission_roles_skip_before_credentials(monkeypatch, checker):
    """ORCH_UT_024: Unmapped optional Slurm roles never require credentials."""
    rows = [
        {
            "HOSTNAME": "control-01",
            "ADMIN_IP": "192.0.2.10",
            "EXPECTED_FUNCTIONAL_GROUP": "slurm_control_node_rhel_10_0_x86_64",
        },
        {
            "HOSTNAME": "compute-01",
            "ADMIN_IP": "192.0.2.11",
            "EXPECTED_FUNCTIONAL_GROUP": "slurm_node_rhel_10_0_x86_64",
        },
    ]
    monkeypatch.setattr(
        slurm_auth,
        "_context",
        lambda _host: (
            {"features": {"openldap": True}},
            rows,
            rows[0],
            {},
        ),
    )
    monkeypatch.setattr(slurm_auth, "_require_functional", lambda _summary: None)
    monkeypatch.setattr(slurm_auth, "marker_is_authorized", lambda _marker: True)

    def unexpected_credentials():
        raise AssertionError("credentials were loaded before role applicability")

    monkeypatch.setattr(slurm_auth, "_ldap_username", unexpected_credentials)
    monkeypatch.setattr(slurm_auth, "_ldap_credentials", unexpected_credentials)

    result = checker(object())

    assert result["success"]
    assert result["skipped"]
    assert "nodes are mapped" in dict(result["details"]["fields"])["Reason"]


def test_mapped_node_host_key_policy_is_limited_to_one_target():
    """ORCH_UT_025: First-seen SSH keys are accepted only for the mapped node."""
    client = slurm_auth.paramiko.SSHClient()
    key = SimpleNamespace(
        get_name=lambda: "ssh-ed25519",
        get_base64=lambda: "A" * 68,
    )
    policy = slurm_auth._MappedNodeHostKeyPolicy("192.0.2.10")

    policy.missing_host_key(client, "192.0.2.10", key)

    assert client.get_host_keys().lookup("192.0.2.10")["ssh-ed25519"] is key
    with pytest.raises(slurm_auth.paramiko.SSHException, match="mapped node target"):
        policy.missing_host_key(client, "192.0.2.11", key)
