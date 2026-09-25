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

"""Live FVT for the standalone catalog RPM exact-mirror playbook."""

import json
import re
import shlex

import pytest
import yaml

from library.functions import run_playbook
from library.vars.common_vars import (
    _get_catalog_path,
    _get_input_path,
    _get_output_path,
    _get_pulp_certs_dir,
)


PULP = "/usr/local/bin/pulp"
POLICY_CACHING_MAP = {
    ("always", False): "immediate",
    ("always", True): "on_demand",
    ("partial", False): "streamed",
    ("partial", True): "on_demand",
    ("never", False): "streamed",
    ("never", True): "streamed",
}


def _pulp_json(host, *arguments):
    """Run one structured Pulp query and return its JSON response."""
    command = " ".join(shlex.quote(value) for value in (PULP, *arguments))
    result = host.run(command)
    assert result.rc == 0, result.stderr
    value = json.loads(result.stdout or "[]")
    return value.get("results", []) if isinstance(value, dict) and "results" in value else value


def _read_yaml(host, path):
    """Read one YAML mapping from the target host."""
    target = host.file(path)
    assert target.exists, f"Required file does not exist: {path}"
    value = yaml.safe_load(target.content_string)
    assert isinstance(value, dict), f"Expected YAML mapping: {path}"
    return value


def _read_catalog(host):
    """Read the active catalog selected by the Omnia environment."""
    target = host.file(_get_catalog_path())
    assert target.exists, f"Active catalog does not exist: {_get_catalog_path()}"
    value = json.loads(target.content_string)
    catalog = value.get("catalog", value)
    assert isinstance(catalog, dict), "Active catalog root must be a mapping"
    return catalog


def _catalog_repository_identities(host):
    """Resolve RPM repository identities referenced by active functional layers."""
    catalog = _read_catalog(host)
    groups = catalog.get("groups", {})
    packages = catalog.get("packages", {})
    referenced_packages = set()
    for functional_layer in catalog.get("functionallayer", []):
        for group_name in functional_layer.get("components", []):
            referenced_packages.update(
                groups.get(group_name, {}).get("components", [])
            )

    identities = set()
    for package_name in referenced_packages:
        package = packages.get(package_name, {})
        package_type = package.get("type", package.get("packagetype", "rpm"))
        if package_type not in {"rpm", "rpm_list", "rpm_repo"}:
            continue
        for source in package.get("sources", []):
            repository = str(source.get("reponame", "")).strip()
            architecture = str(source.get("architecture", "")).strip()
            versions = source.get("version", [])
            if isinstance(versions, str):
                versions = [versions]
            if not repository or architecture not in {"x86_64", "aarch64"}:
                continue
            for version in versions:
                identities.add(
                    f"{architecture}_rhel_{version}_{repository}"
                )
    assert identities, "Active catalog resolved no RPM repositories"
    return identities


def _repository_snapshot(host):
    """Return stable state for every current Pulp RPM repository."""
    repositories = _pulp_json(host, "rpm", "repository", "list", "--limit", "1000")
    return {
        repository["name"]: {
            "latest_version_href": repository.get("latest_version_href"),
            "pulp_last_updated": repository.get("pulp_last_updated"),
        }
        for repository in repositories
    }


def _status(host):
    """Return the exact-mirror result contract."""
    return _read_yaml(host, f"{_get_output_path()}/repo_resync_status.yml")


@pytest.mark.deploy
@pytest.mark.repo_resync
@pytest.mark.order(0)
def test_repo_sync_playbook_reconciles_only_catalog_repositories(host):
    """RM_FVT_REPO_SYNC_E001: Execute standalone exact-mirror reconciliation."""
    selected = _catalog_repository_identities(host)
    before = _repository_snapshot(host)
    result = run_playbook(
        playbook="repo_sync.yml",
        playbook_workdir="src/repo_manager/playbooks/repo_operations",
        timeout=10800,
    )
    assert result["success"], result.get("error", "repo_sync.yml failed")

    after = _repository_snapshot(host)
    unreferenced = set(before) - selected
    assert unreferenced, "Boundary test requires at least one unreferenced repository"
    changed = {
        name: {"before": before[name], "after": after.get(name)}
        for name in unreferenced
        if before[name] != after.get(name)
    }
    assert not changed, (
        "repo_sync.yml changed or deleted unreferenced repositories: "
        f"{changed}"
    )


@pytest.mark.repo_resync
@pytest.mark.positive
@pytest.mark.order(1)
def test_repo_sync_status_is_successful(host):
    """RM_FVT_REPO_SYNC_V001: Verify aggregate sync and orphan cleanup success."""
    status = _status(host)
    assert status.get("overall_status") == "success", status
    assert status.get("orphan_cleanup") == "success", status


@pytest.mark.repo_resync
@pytest.mark.positive
@pytest.mark.order(2)
def test_repo_sync_result_matches_catalog_scope(host):
    """RM_FVT_REPO_SYNC_V002: Verify result contains only catalog RPM repos."""
    expected = _catalog_repository_identities(host)
    actual = set(_status(host).get("repositories", {}))
    assert actual == expected, {"expected": sorted(expected), "actual": sorted(actual)}


@pytest.mark.repo_resync
@pytest.mark.positive
@pytest.mark.order(3)
def test_repo_sync_repositories_have_zero_stale_packages(host):
    """RM_FVT_REPO_SYNC_V003: Verify every selected repository was reconciled."""
    repositories = _status(host).get("repositories", {})
    assert repositories, "No per-repository exact-mirror results were written"
    failures = {
        name: result
        for name, result in repositories.items()
        if result.get("sync_status") != "success"
        or result.get("cleanup_status") != "success"
        or result.get("stale_packages_remaining") != 0
    }
    assert not failures, failures


@pytest.mark.repo_resync
@pytest.mark.positive
@pytest.mark.order(4)
def test_repo_sync_package_deltas_are_valid(host):
    """RM_FVT_REPO_SYNC_V004: Verify deterministic version and package metrics."""
    for name, result in _status(host)["repositories"].items():
        assert isinstance(result.get("old_version"), int), name
        assert isinstance(result.get("new_version"), int), name
        assert result["new_version"] >= result["old_version"], name
        assert isinstance(result.get("packages_added"), int), name
        assert isinstance(result.get("packages_removed"), int), name
        assert result["packages_added"] >= 0, name
        assert result["packages_removed"] >= 0, name


@pytest.mark.repo_resync
@pytest.mark.positive
@pytest.mark.order(5)
def test_repo_sync_keeps_one_current_publication_and_version(host):
    """RM_FVT_REPO_SYNC_V005: Verify superseded publications and versions are gone."""
    for name in _status(host)["repositories"]:
        versions = _pulp_json(
            host,
            "rpm",
            "repository",
            "version",
            "list",
            "--repository",
            name,
            "--limit",
            "1000",
        )
        nonzero_versions = [item for item in versions if int(item["number"]) > 0]
        publications = _pulp_json(
            host,
            "rpm",
            "publication",
            "list",
            "--repository",
            name,
            "--limit",
            "1000",
        )
        assert len(nonzero_versions) == 1, {name: nonzero_versions}
        assert len(publications) == 1, {name: publications}


@pytest.mark.repo_resync
@pytest.mark.positive
@pytest.mark.order(6)
def test_repo_sync_distributions_publish_valid_metadata(host):
    """RM_FVT_REPO_SYNC_V006: Verify publication binding and served repomd.xml."""
    ca_certificate = f"{_get_pulp_certs_dir()}/pulp_webserver.crt"
    assert host.file(ca_certificate).exists, ca_certificate
    for name in _status(host)["repositories"]:
        distribution = _pulp_json(host, "rpm", "distribution", "show", "--name", name)
        assert isinstance(distribution, dict), name
        publication = distribution.get("publication")
        assert publication, f"Distribution is not publication-backed: {name}"
        metadata_url = f"{distribution['base_url'].rstrip('/')}/repodata/repomd.xml"
        command = "curl --fail --silent --show-error --cacert {} {}".format(
            shlex.quote(ca_certificate), shlex.quote(metadata_url)
        )
        response = host.run(command)
        assert response.rc == 0, f"{name}: {response.stderr}"
        assert "repomd" in response.stdout, name


@pytest.mark.repo_resync
@pytest.mark.positive
@pytest.mark.order(7)
def test_repo_sync_slurm_user_repository_matches_input(host):
    """RM_FVT_REPO_SYNC_V007: Verify Slurm user-repo URL and policy are preserved."""
    status = _status(host)
    slurm_names = [name for name in status["repositories"] if name.endswith("_slurm_custom")]
    if not slurm_names:
        pytest.skip("Active catalog does not reference slurm_custom")
    assert len(slurm_names) == 1, slurm_names
    name = slurm_names[0]
    identity = re.fullmatch(
        r"(x86_64|aarch64)_rhel_([^_]+)_slurm_custom", name
    )
    assert identity, name
    architecture, version = identity.groups()
    config = _read_yaml(host, f"{_get_input_path()}/repo_manager_config.yml")
    expected = config["repositories"][version][architecture]["user_repos"][
        "slurm_custom"
    ]
    configured_policy = expected.get("policy", config.get("repo_config", "partial"))
    configured_caching = expected.get(
        "caching", config.get("caching_policy", True)
    )
    expected_policy = POLICY_CACHING_MAP.get(
        (configured_policy, configured_caching), configured_policy
    )
    remote = _pulp_json(host, "rpm", "remote", "show", "--name", name)
    assert remote["url"].rstrip("/") == expected["url"].rstrip("/")
    assert remote["policy"] == expected_policy
