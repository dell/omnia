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

"""Read-only helpers for Orchestrator precheck verification."""

import csv
import io
import ipaddress
import posixpath
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from omnia_auto import read_remote_env, resolve_domain_data_path, run_on_host

from ..vars.precheck_vars import (
    ENV_IMAGE_BUILD_MANAGER_DATA_PATH,
    ENV_OMNIA_DATA_PATH,
    ENV_REPO_MANAGER_DATA_PATH,
    ENV_SYSTEM_ADMIN_IPV4,
    ENV_SYSTEM_DOMAIN_NAME,
    ENV_SYSTEM_HOSTNAME,
    HTTP_CONNECT_TIMEOUT_SECONDS,
    HTTP_REQUEST_TIMEOUT_SECONDS,
    NFS_PING_COUNT,
    NFS_PING_TIMEOUT_SECONDS,
    PRECHECK_COMMANDS,
    REQUIRED_PROJECT_INPUTS,
)
from ._prepare_helpers import prepare_result, read_yaml_mapping
from .project_func import (
    resolve_target_input_project_path,
    resolve_target_project_name,
)

_SAFE_ENDPOINT = re.compile(
    r"^(?:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?|"
    r"\[[0-9A-Fa-f:]+\])$"
)
_IPV4_CIDR = re.compile(r"\binet\s+([0-9.]+)/[0-9]+\b")


def _safe_absolute_path(path: object, label: str) -> str:
    """Return one normalized, absolute, non-root path."""
    value = str(path or "").strip()
    normalized = posixpath.normpath(value)
    if not value or not normalized.startswith("/") or normalized == "/":
        raise ValueError(f"{label} must be a safe absolute path")
    return normalized


def _remote_file_state(host, path: str) -> tuple[bool, int]:
    """Return regular-file existence and size without reading file content."""
    remote = host.file(path)
    if not remote.is_file:
        return False, 0
    return True, int(remote.size or 0)


def check_precheck_hostname_domain(host) -> dict[str, Any]:
    """Compare the configured OIM hostname and domain with the host."""
    try:
        configured_hostname = read_remote_env(host, ENV_SYSTEM_HOSTNAME)
        configured_domain = read_remote_env(host, ENV_SYSTEM_DOMAIN_NAME)
        hostname = run_on_host(host, PRECHECK_COMMANDS["hostname_short"])
        domain = run_on_host(host, PRECHECK_COMMANDS["hostname_domain"])
    except (OSError, RuntimeError, ValueError) as exc:
        return prepare_result(False, "Unable to resolve OIM identity", [], str(exc))

    actual_hostname = hostname.stdout.strip() if hostname.rc == 0 else ""
    actual_domain = domain.stdout.strip() if domain.rc == 0 else ""
    hostname_ok = actual_hostname == configured_hostname
    domain_ok = actual_domain == configured_domain
    fields = [
        ("SYSTEM_HOSTNAME", configured_hostname),
        ("Actual short hostname", actual_hostname or "unavailable"),
        ("Hostname match", "yes" if hostname_ok else "NO"),
        ("SYSTEM_DOMAIN_NAME", configured_domain),
        ("Actual domain", actual_domain or "unavailable"),
        ("Domain match", "yes" if domain_ok else "NO"),
        ("Expected FQDN", f"{configured_hostname}.{configured_domain}"),
    ]
    failures = []
    if not hostname_ok:
        failures.append(
            f"SYSTEM_HOSTNAME={configured_hostname!r} does not match "
            f"hostname -s={actual_hostname!r}"
        )
    if not domain_ok:
        failures.append(
            f"SYSTEM_DOMAIN_NAME={configured_domain!r} does not match "
            f"hostname -d={actual_domain!r}"
        )
    return prepare_result(
        not failures,
        "OIM hostname and domain compared with omnia.env",
        fields,
        "; ".join(failures),
    )


def check_precheck_admin_ipv4(host) -> dict[str, Any]:
    """Verify SYSTEM_ADMIN_NIC_IPV4 is assigned to a global local address."""
    try:
        configured = read_remote_env(host, ENV_SYSTEM_ADMIN_IPV4)
        expected = str(ipaddress.IPv4Address(configured))
        result = run_on_host(host, PRECHECK_COMMANDS["local_ipv4"])
    except (ipaddress.AddressValueError, OSError, RuntimeError, ValueError) as exc:
        return prepare_result(False, "Unable to resolve OIM IPv4 state", [], str(exc))

    local_addresses = sorted(set(_IPV4_CIDR.findall(result.stdout)))
    assigned = result.rc == 0 and expected in local_addresses
    fields = [
        ("SYSTEM_ADMIN_NIC_IPV4", expected),
        ("Global local IPv4 addresses", ", ".join(local_addresses) or "none"),
        ("Administrative IPv4 assigned", "yes" if assigned else "NO"),
    ]
    error = ""
    if not assigned:
        error = (
            f"SYSTEM_ADMIN_NIC_IPV4 {expected} is not assigned to a global "
            "IPv4 interface on the OIM"
        )
    return prepare_result(
        assigned,
        "OIM administrative IPv4 assignment checked",
        fields,
        error,
    )


def _nfs_server(source: str) -> str:
    """Extract and validate the server portion of one NFS source."""
    if source.startswith("["):
        closing = source.find("]")
        if closing < 1 or source[closing + 1 : closing + 2] != ":":
            raise ValueError(f"Invalid NFS source: {source!r}")
        server = source[: closing + 1]
    elif ":" in source:
        server = source.split(":", 1)[0]
    else:
        raise ValueError(f"NFS source has no server/export separator: {source!r}")
    if not _SAFE_ENDPOINT.fullmatch(server):
        raise ValueError(f"Unsafe NFS server endpoint in source: {source!r}")
    return server[1:-1] if server.startswith("[") else server


def _target_values(value: object, label: str) -> list[str]:
    """Return one validated storage-target list."""
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    targets = []
    for item in value:
        target = str(item or "").strip()
        if not target:
            raise ValueError(f"{label} contains an empty target")
        targets.append(target)
    return targets


def _configured_vast_storage_name(omnia: Mapping[str, Any]) -> str:
    """Return the stock VAST selection used by the mount_config role."""
    clusters = omnia.get("slurm_cluster", []) or []
    if not isinstance(clusters, list):
        raise TypeError("omnia_config.yml slurm_cluster must be a list")
    if not clusters:
        return ""
    if not isinstance(clusters[0], dict):
        raise TypeError("omnia_config.yml slurm_cluster[0] must be a mapping")
    return str(clusters[0].get("vast_storage_name") or "").strip()


def _configured_nfs_mounts(
    storage: Mapping[str, Any],
    mapped_functional_groups: set[str],
    mapped_groups: set[str],
    configured_vast_name: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return applicable and ignored NFS mounts using production targeting."""
    mounts = storage.get("mounts", []) or []
    profiles = storage.get("mount_params", {}) or {}
    if not isinstance(mounts, list) or not isinstance(profiles, dict):
        raise TypeError("storage_config.yml mounts/profile data is malformed")

    applicable = []
    ignored = []
    for index, entry in enumerate(mounts, start=1):
        if not isinstance(entry, dict):
            raise TypeError(f"storage mount entry {index} must be a mapping")
        source = str(entry.get("source") or "").strip()
        profile_name = str(entry.get("mount_params") or "").strip()
        profile = profiles.get(profile_name, {}) if profile_name else {}
        if profile and not isinstance(profile, dict):
            raise TypeError(f"mount_params profile {profile_name!r} is malformed")
        fs_type = str(entry.get("fs_type") or profile.get("fs_type") or "")
        looks_nfs = fs_type.lower() in {"nfs", "nfs4"} or (
            bool(source) and ":" in source and not source.startswith("//")
        )
        if not looks_nfs:
            continue
        name = str(entry.get("name") or f"mount_{index}")
        prefixes_defined = "functional_group_prefix" in entry
        groups_defined = "groups" in entry
        if prefixes_defined == groups_defined:
            raise ValueError(
                f"NFS mount {name!r} must define exactly one of "
                "functional_group_prefix or groups"
            )

        record = {
            "name": name,
            "source": source,
            "server": _nfs_server(source),
            "selection": "",
        }
        if name == "vast_storage" and configured_vast_name != name:
            record["selection"] = (
                "ignored: not selected by "
                "omnia_config.yml slurm_cluster[0].vast_storage_name"
            )
            ignored.append(record)
            continue

        if prefixes_defined:
            prefixes = _target_values(
                entry.get("functional_group_prefix"),
                f"NFS mount {name!r} functional_group_prefix",
            )
            matches = sorted(
                group
                for group in mapped_functional_groups
                if any(group.startswith(prefix) for prefix in prefixes)
            )
            record["selection"] = (
                "functional groups=" + ", ".join(matches)
                if matches
                else "ignored: no mapped functional group matches prefixes "
                + ", ".join(prefixes)
            )
        else:
            target_groups = _target_values(
                entry.get("groups"), f"NFS mount {name!r} groups"
            )
            matches = sorted(mapped_groups.intersection(target_groups))
            record["selection"] = (
                "PXE groups=" + ", ".join(matches)
                if matches
                else "ignored: no mapped GROUP_NAME matches " + ", ".join(target_groups)
            )

        (applicable if matches else ignored).append(record)
    return applicable, ignored


def check_precheck_nfs_servers(host) -> dict[str, Any]:
    """Ping NFS endpoints selected for at least one mapped node."""
    input_dir = resolve_target_input_project_path(host)
    storage_path = posixpath.join(input_dir, "storage_config.yml")
    if not host.file(storage_path).is_file:
        return prepare_result(
            True,
            "No storage_config.yml is present; no NFS endpoints to check",
            [("Configured NFS mounts", 0), ("NFS reachability", "not applicable")],
        )
    try:
        config = read_yaml_mapping(
            host, posixpath.join(input_dir, "orchestrator_config.yml")
        )
        omnia = read_yaml_mapping(host, posixpath.join(input_dir, "omnia_config.yml"))
        mapping_path = _safe_absolute_path(
            config.get("pxe_mapping_file_path")
            or posixpath.join(input_dir, "pxe_mapping_file.csv"),
            "pxe_mapping_file_path",
        )
        mapped_functional_groups, mapped_groups = _mapping_targets(host, mapping_path)
        mounts, ignored_mounts = _configured_nfs_mounts(
            read_yaml_mapping(host, storage_path),
            mapped_functional_groups,
            mapped_groups,
            _configured_vast_storage_name(omnia),
        )
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, "Unable to resolve NFS endpoints", [], str(exc))

    fields: list[tuple[str, object]] = [
        ("PXE mapping", mapping_path),
        ("Mapped functional groups", ", ".join(sorted(mapped_functional_groups))),
        ("Mapped PXE groups", ", ".join(sorted(mapped_groups))),
        ("Configured NFS mounts", len(mounts) + len(ignored_mounts)),
        ("Applicable NFS mounts", len(mounts)),
        ("Ignored NFS mounts", len(ignored_mounts)),
    ]
    for mount in ignored_mounts:
        fields.append((f"NFS mount [{mount['name']}]", mount["selection"]))
    failures = []
    results: dict[str, bool] = {}
    for mount in mounts:
        server = mount["server"]
        if server not in results:
            probe = run_on_host(
                host,
                PRECHECK_COMMANDS["ping"],
                str(NFS_PING_COUNT),
                str(NFS_PING_TIMEOUT_SECONDS),
                server,
            )
            results[server] = probe.rc == 0
        reachable = results[server]
        status = "reachable" if reachable else "UNREACHABLE"
        details = " | ".join(
            (
                status,
                f"server={server}",
                f"source={mount['source']}",
                f"selected by {mount['selection']}",
            )
        )
        fields.append(
            (
                f"NFS mount [{mount['name']}]",
                details,
            )
        )
        if not reachable:
            failures.append(f"{mount['name']} ({server})")

    return prepare_result(
        not failures,
        "Configured NFS server reachability checked",
        fields,
        "Unreachable NFS servers: " + ", ".join(failures) if failures else "",
    )


def _default_dependency_path(
    host,
    domain: str,
    domain_path_var: str,
    filename: str,
) -> str:
    """Resolve a dependency output using the production path precedence."""
    root = resolve_domain_data_path(
        host,
        domain,
        ENV_OMNIA_DATA_PATH,
        domain_data_path_var=domain_path_var,
    )
    return posixpath.join(root, "output", resolve_target_project_name(host), filename)


def _dependency_paths(host) -> tuple[str, str]:
    """Return configured/default build and repository status paths."""
    input_dir = resolve_target_input_project_path(host)
    config = read_yaml_mapping(
        host, posixpath.join(input_dir, "orchestrator_config.yml")
    )
    build_default = _default_dependency_path(
        host,
        "image_build_manager",
        ENV_IMAGE_BUILD_MANAGER_DATA_PATH,
        "build_status.yml",
    )
    repo_default = _default_dependency_path(
        host,
        "repo_manager",
        ENV_REPO_MANAGER_DATA_PATH,
        "repo_status.yml",
    )
    build_path = _safe_absolute_path(
        config.get("image_build_manager_output_path") or build_default,
        "image_build_manager_output_path",
    )
    repo_path = _safe_absolute_path(
        config.get("repo_manager_output_path") or repo_default,
        "repo_manager_output_path",
    )
    return build_path, repo_path


def check_precheck_dependencies(host) -> dict[str, Any]:
    """Verify configured/default Image Builder and Repo Manager outputs."""
    try:
        build_path, repo_path = _dependency_paths(host)
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, "Unable to resolve dependency paths", [], str(exc))

    fields = []
    failures = []
    for label, path in (
        ("Image Build Manager build_status.yml", build_path),
        ("Repo Manager repo_status.yml", repo_path),
    ):
        exists, size = _remote_file_state(host, path)
        usable = exists and size > 0
        fields.extend(
            [
                (f"{label} path", path),
                (label, f"present ({size} bytes)" if usable else "MISSING OR EMPTY"),
            ]
        )
        if not usable:
            failures.append(path)

    return prepare_result(
        not failures,
        "Orchestrator dependency status files checked",
        fields,
        "Missing or empty dependency files: " + ", ".join(failures) if failures else "",
    )


def _mapping_functional_groups(host, path: str) -> set[str]:
    """Read functional-group values needed for conditional file checks."""
    remote = host.file(path)
    if not remote.is_file:
        return set()
    reader = csv.DictReader(io.StringIO(remote.content_string))
    if not reader.fieldnames or "FUNCTIONAL_GROUP_NAME" not in reader.fieldnames:
        return set()
    return {
        str(row.get("FUNCTIONAL_GROUP_NAME") or "").strip()
        for row in reader
        if str(row.get("FUNCTIONAL_GROUP_NAME") or "").strip()
    }


def _mapping_targets(host, path: str) -> tuple[set[str], set[str]]:
    """Read functional and logical group targets from the active PXE mapping."""
    remote = host.file(path)
    if not remote.is_file:
        raise ValueError(f"PXE mapping file is missing: {path}")
    reader = csv.DictReader(io.StringIO(remote.content_string))
    required = {"FUNCTIONAL_GROUP_NAME", "GROUP_NAME"}
    missing = required.difference(reader.fieldnames or [])
    if missing:
        raise ValueError(
            "PXE mapping is missing storage-target columns: "
            + ", ".join(sorted(missing))
        )
    functional_groups: set[str] = set()
    groups: set[str] = set()
    for row in reader:
        functional_group = str(row.get("FUNCTIONAL_GROUP_NAME") or "").strip()
        group = str(row.get("GROUP_NAME") or "").strip()
        if functional_group:
            functional_groups.add(functional_group)
        if group:
            groups.add(group)
    return functional_groups, groups


def _has_storage_reference(value: object, key: str = "") -> bool:
    """Return whether omnia_config contains a non-empty storage-name field."""
    if isinstance(value, dict):
        return any(
            _has_storage_reference(item, str(name)) for name, item in value.items()
        )
    if isinstance(value, list):
        return any(_has_storage_reference(item, key) for item in value)
    return key.endswith("storage_name") and bool(str(value or "").strip())


def check_precheck_inputs(host) -> dict[str, Any]:
    """Verify source-required project inputs and configured auxiliary files."""
    try:
        input_dir = resolve_target_input_project_path(host)
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(
            False, "Unable to resolve Orchestrator inputs", [], str(exc)
        )

    fields: list[tuple[str, object]] = [("Project input directory", input_dir)]
    failures = []
    base_paths = [posixpath.join(input_dir, item) for item in REQUIRED_PROJECT_INPUTS]
    for path in base_paths:
        exists, size = _remote_file_state(host, path)
        usable = exists and size > 0
        fields.append(
            (path, f"present ({size} bytes)" if usable else "MISSING OR EMPTY")
        )
        if not usable:
            failures.append(path)
    if failures:
        return prepare_result(
            False,
            "Required Orchestrator project inputs checked",
            fields,
            "Missing or empty Orchestrator inputs: " + ", ".join(failures),
        )

    try:
        orchestrator_path = base_paths[0]
        config = read_yaml_mapping(host, orchestrator_path)
        omnia = read_yaml_mapping(host, base_paths[1])
        mapping_path = _safe_absolute_path(
            config.get("pxe_mapping_file_path")
            or posixpath.join(input_dir, "pxe_mapping_file.csv"),
            "pxe_mapping_file_path",
        )
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(
            False, "Unable to resolve Orchestrator inputs", fields, str(exc)
        )

    required = [mapping_path]
    groups = _mapping_functional_groups(host, mapping_path)
    if any(group.startswith("service_kube_") for group in groups):
        required.append(posixpath.join(input_dir, "high_availability_config.yml"))
    if _has_storage_reference(omnia):
        required.append(posixpath.join(input_dir, "storage_config.yml"))
    additional = str(config.get("additional_cloud_init_config_file") or "").strip()
    if additional:
        try:
            required.append(
                _safe_absolute_path(additional, "additional_cloud_init_config_file")
            )
        except ValueError as exc:
            return prepare_result(
                False, "Invalid configured auxiliary input", fields, str(exc)
            )

    for path in dict.fromkeys(required):
        exists, size = _remote_file_state(host, path)
        usable = exists and size > 0
        fields.append(
            (path, f"present ({size} bytes)" if usable else "MISSING OR EMPTY")
        )
        if not usable:
            failures.append(path)

    return prepare_result(
        not failures,
        "Required and conditionally selected Orchestrator inputs checked",
        fields,
        "Missing or empty Orchestrator inputs: " + ", ".join(failures)
        if failures
        else "",
    )


def _validated_url(value: object, label: str) -> str:
    """Return a safe HTTP(S) URL suitable for a quoted curl argument."""
    url = str(value or "").strip()
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(f"{label} is not a valid credential-free HTTP(S) URL")
    return url.rstrip("/")


def _http_probe(host, command: str, url: str) -> tuple[bool, str]:
    """Probe one URL and return reachability plus the final HTTP status."""
    result = run_on_host(
        host,
        PRECHECK_COMMANDS[command],
        str(HTTP_CONNECT_TIMEOUT_SECONDS),
        str(HTTP_REQUEST_TIMEOUT_SECONDS),
        url,
    )
    status = result.stdout.strip()
    reachable = result.rc == 0 and len(status) == 3 and status.startswith("2")
    if not status:
        status = f"transport failure (curl rc={result.rc})"
    return reachable, status


def _build_artifacts(build_status: Mapping[str, Any]) -> list[dict[str, str]]:
    """Normalize nested and flat functional-group image manifests."""
    raw_images = build_status.get("functional_group_images", []) or []
    if not isinstance(raw_images, list):
        raise TypeError("functional_group_images must be a list")
    entries: list[dict[str, str]] = []
    for block in raw_images:
        if not isinstance(block, dict):
            raise TypeError("functional_group_images entries must be mappings")
        if "functional_group" in block:
            candidates = [block]
        else:
            candidates = []
            for arch_entries in block.values():
                if not isinstance(arch_entries, list):
                    raise TypeError("architecture image entries must be lists")
                candidates.extend(arch_entries)
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise TypeError("functional-group image entry must be a mapping")
            group = str(candidate.get("functional_group") or "").strip()
            if not group:
                raise ValueError("functional-group image entry has no name")
            for source_key, artifact in (
                ("kernel", "kernel"),
                ("initrd", "initrd"),
                ("image", "rootfs"),
            ):
                path = str(candidate.get(source_key) or "").strip()
                if not path:
                    raise ValueError(f"{group} has no {artifact} path")
                entries.append({"group": group, "artifact": artifact, "path": path})
    if not entries:
        raise ValueError("build_status.yml contains no boot artifacts")
    return entries


def check_precheck_s3_artifacts(host) -> dict[str, Any]:
    """Require every boot artifact in build_status.yml to return HTTP 2xx."""
    try:
        build_path, _repo_path = _dependency_paths(host)
        build_status = read_yaml_mapping(host, build_path)
        if build_status.get("overall_status") != "success":
            raise ValueError("build_status.yml overall_status is not success")
        s3_config = build_status.get("s3_configurations", {})
        if not isinstance(s3_config, dict):
            raise TypeError("s3_configurations must be a mapping")
        endpoint = _validated_url(s3_config.get("endpoint_url"), "S3 endpoint_url")
        artifacts = _build_artifacts(build_status)
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, "Unable to resolve S3 artifacts", [], str(exc))

    fields: list[tuple[str, object]] = [
        ("Build status", build_path),
        ("S3 endpoint", endpoint),
        ("Boot artifacts", len(artifacts)),
    ]
    failures = []
    for entry in artifacts:
        url = f"{endpoint}/{entry['path'].lstrip('/')}"
        reachable, status = _http_probe(host, "http_head", url)
        state = "reachable" if reachable else "UNREACHABLE"
        fields.append(
            (
                f"[{entry['group']}] {entry['artifact']}",
                f"{state} | HTTP {status} | {url}",
            )
        )
        if not reachable:
            failures.append(f"{entry['group']}/{entry['artifact']} (HTTP {status})")
    return prepare_result(
        not failures,
        "All published boot artifacts checked through the S3 endpoint",
        fields,
        "Inaccessible S3 boot artifacts: " + ", ".join(failures) if failures else "",
    )


def _published_repositories(repo_status: Mapping[str, Any]) -> list[dict[str, str]]:
    """Normalize RPM and file repository URLs published by Repo Manager."""
    published: list[dict[str, str]] = []
    rpm_versions = repo_status.get("repositories", {}) or {}
    if not isinstance(rpm_versions, dict):
        raise TypeError("repositories must be a mapping")
    for version, architectures in rpm_versions.items():
        if not isinstance(architectures, dict):
            raise TypeError(f"repositories[{version!r}] must be a mapping")
        for architecture, repositories in architectures.items():
            if not isinstance(repositories, dict):
                raise TypeError(
                    f"repositories[{version!r}][{architecture!r}] must be a mapping"
                )
            for name, config in repositories.items():
                if not isinstance(config, dict):
                    raise TypeError(f"RPM repository {name!r} must be a mapping")
                base_url = _validated_url(
                    config.get("url"), f"RPM repository {name!r} URL"
                )
                published.append(
                    {
                        "label": f"RPM [{version}/{architecture}/{name}]",
                        "url": f"{base_url}/repodata/repomd.xml",
                    }
                )

    file_architectures = repo_status.get("file_repos", {}) or {}
    if not isinstance(file_architectures, dict):
        raise TypeError("file_repos must be a mapping")
    for architecture, repo_types in file_architectures.items():
        if not isinstance(repo_types, dict):
            raise TypeError(f"file_repos[{architecture!r}] must be a mapping")
        for repo_type, repositories in repo_types.items():
            if not isinstance(repositories, dict):
                raise TypeError(
                    f"file_repos[{architecture!r}][{repo_type!r}] must be a mapping"
                )
            for name, url in repositories.items():
                published.append(
                    {
                        "label": f"File [{architecture}/{repo_type}/{name}]",
                        "url": _validated_url(url, f"file repository {name!r} URL")
                        + "/",
                    }
                )
    if not published:
        raise ValueError("repo_status.yml contains no published repositories")
    return published


def check_precheck_repositories(host) -> dict[str, Any]:
    """Require every repository in repo_status.yml to return HTTP 2xx."""
    try:
        _build_path, repo_path = _dependency_paths(host)
        repo_status = read_yaml_mapping(host, repo_path)
        if repo_status.get("overall_status") != "success":
            raise ValueError("repo_status.yml overall_status is not success")
        repositories = _published_repositories(repo_status)
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(
            False, "Unable to resolve published repositories", [], str(exc)
        )

    fields: list[tuple[str, object]] = [
        ("Repo status", repo_path),
        ("Published repositories", len(repositories)),
    ]
    failures = []
    for repository in repositories:
        reachable, status = _http_probe(host, "http_get", repository["url"])
        state = "reachable" if reachable else "UNREACHABLE"
        fields.append(
            (
                repository["label"],
                f"{state} | HTTP {status} | {repository['url']}",
            )
        )
        if not reachable:
            failures.append(f"{repository['label']} (HTTP {status})")
    return prepare_result(
        not failures,
        "All repositories published by Repo Manager checked",
        fields,
        "Inaccessible published repositories: " + ", ".join(failures)
        if failures
        else "",
    )
