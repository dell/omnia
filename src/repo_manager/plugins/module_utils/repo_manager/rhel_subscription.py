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

"""Resolve catalog repository names against RHEL subscription repositories."""
# pylint: disable=import-error,no-name-in-module,too-many-arguments
# pylint: disable=too-many-positional-arguments,too-many-locals

import configparser
import glob
import os
import re

from ansible.module_utils.repo_manager.security_utils import (
    validate_repository_id,
    validate_repository_url,
)


SUPPORTED_ARCHITECTURES = ("x86_64", "aarch64")
BUILTIN_REPOSITORIES = (
    "baseos",
    "appstream",
    "codeready-builder",
)
_VERSION_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")
_RHEL_MAJOR_PATTERN = re.compile(r"(?:^|-)rhel-([0-9]+)(?:-|$)")
_ARCH_PATTERN = re.compile(r"(?:^|-)(x86_64|aarch64)(?:-|$)")
_NON_BINARY_MARKERS = ("-debug-", "-source-")
_OTHER_LIFECYCLE_MARKERS = ("-e4s-", "-aus-", "-tus-")


class SubscriptionRepositoryError(ValueError):
    """Raised when subscription repository input cannot be resolved safely."""


def parse_redhat_repo(repo_file_path):
    """Return ``redhat.repo`` sections without applying INI interpolation."""
    parser = configparser.RawConfigParser(
        interpolation=None,
        strict=False,
        delimiters=("=",),
    )
    parser.optionxform = str.lower
    try:
        with open(repo_file_path, "r", encoding="utf-8") as repo_file:
            parser.read_file(repo_file)
    except (OSError, UnicodeError, configparser.Error) as error:
        raise SubscriptionRepositoryError(
            "RHEL subscription repository inventory could not be read"
        ) from error

    return {
        validate_repository_id(section): dict(parser.items(section))
        for section in parser.sections()
    }


def _builtin_repo_ids(repo_name, architecture, major_version):
    """Return the standard and EUS Repo IDs for a built-in logical name."""
    if repo_name in ("baseos", "appstream"):
        prefix = f"rhel-{major_version}-for-{architecture}-{repo_name}"
    elif repo_name == "codeready-builder":
        prefix = (
            f"codeready-builder-for-rhel-{major_version}-{architecture}"
        )
    else:
        return None, None
    return f"{prefix}-rpms", f"{prefix}-eus-rpms"


def _standard_repo_id(repo_id):
    """Return the standard-channel counterpart of an RPM Repo ID."""
    return repo_id.replace("-eus-rpms", "-rpms")


def _eus_repo_id(repo_id):
    """Return the EUS counterpart of a standard RPM Repo ID."""
    standard_id = _standard_repo_id(repo_id)
    if not standard_id.endswith("-rpms"):
        return None
    return f"{standard_id[:-len('-rpms')]}-eus-rpms"


def _validate_context(os_version, architecture):
    """Return the RHEL major version after validating the active context."""
    version = str(os_version)
    if not _VERSION_PATTERN.fullmatch(version):
        raise SubscriptionRepositoryError(
            "RHEL subscription repository version is invalid"
        )
    if architecture not in SUPPORTED_ARCHITECTURES:
        raise SubscriptionRepositoryError(
            "RHEL subscription repository architecture is invalid"
        )
    return version.split(".", maxsplit=1)[0]


def _is_context_repo_id(repo_id, architecture, major_version):
    """Return whether an exact Repo ID is a binary RPM source for the context."""
    if (
            not repo_id.endswith("-rpms")
            or any(marker in repo_id for marker in _NON_BINARY_MARKERS)
            or any(marker in repo_id for marker in _OTHER_LIFECYCLE_MARKERS)
    ):
        return False
    architecture_match = _ARCH_PATTERN.search(repo_id)
    major_match = _RHEL_MAJOR_PATTERN.search(repo_id)
    return bool(
        architecture_match
        and architecture_match.group(1) == architecture
        and major_match
        and major_match.group(1) == major_version
    )


def _available_section_id(repo_id, architecture, available_repo_ids):
    """Return an exact or opposite-architecture RHSM section identifier."""
    if repo_id in available_repo_ids:
        return repo_id
    other_architecture = next(
        item for item in SUPPORTED_ARCHITECTURES if item != architecture
    )
    counterpart = repo_id.replace(
        f"-{architecture}-", f"-{other_architecture}-", 1
    )
    return counterpart if counterpart in available_repo_ids else None


def subscription_repo_id_candidates(
        repo_name, architecture, os_version, available_repo_ids,
        builtin_repositories=BUILTIN_REPOSITORIES):
    """Return available standard/EUS Repo IDs for one configured repository."""
    repo_name = validate_repository_id(repo_name)
    major_version = _validate_context(os_version, architecture)
    available = set(available_repo_ids or ())

    if repo_name in set(builtin_repositories or ()):
        standard_id, eus_id = _builtin_repo_ids(
            repo_name, architecture, major_version
        )
    else:
        standard_id = _standard_repo_id(repo_name)
        eus_id = _eus_repo_id(repo_name)
        if not _is_context_repo_id(
                standard_id, architecture, major_version):
            return {"standard": None, "eus": None}

    return {
        "standard": _available_section_id(
            standard_id, architecture, available
        ),
        "eus": _available_section_id(eus_id, architecture, available),
    }


def subscription_can_supply(
        repo_name, architecture, os_version, available_repo_ids,
        builtin_repositories=BUILTIN_REPOSITORIES):
    """Return whether subscription discovery may supply a repository URL."""
    if repo_name in set(builtin_repositories or ()):
        return True
    candidates = subscription_repo_id_candidates(
        repo_name, architecture, os_version, available_repo_ids
    )
    return any(candidates.values())


def _resolve_url(raw_url, os_version, architecture):
    """Resolve RHSM URL variables for the exact version and architecture."""
    major_version = _validate_context(os_version, architecture)
    url = str(raw_url or "").strip()
    for token in ("$releasever", "${releasever}"):
        url = url.replace(token, str(os_version))
    for token in ("$basearch", "${basearch}", "$arch", "${arch}"):
        url = url.replace(token, architecture)
    for candidate_architecture in SUPPORTED_ARCHITECTURES:
        if candidate_architecture != architecture:
            url = url.replace(
                f"/{candidate_architecture}/", f"/{architecture}/"
            )
    url = re.sub(
        rf"(/rhel{re.escape(major_version)}/)[0-9]+\.[0-9]+(/)",
        rf"\g<1>{os_version}\g<2>",
        url,
    )
    url = validate_repository_url(url)
    return f"{url.rstrip('/')}/"


def _managed_path(source_path, certificate_directory, default_name=None):
    """Map an RHSM certificate path to its protected copied directory."""
    source_name = os.path.basename(str(source_path or "").strip())
    filename = source_name or default_name
    if not filename:
        return ""
    candidate = os.path.join(certificate_directory, filename)
    return candidate if os.path.isfile(candidate) else ""


def _fallback_client_pair(certificate_directory):
    """Return the first deterministic copied entitlement certificate pair."""
    for key_path in sorted(glob.glob(
            os.path.join(certificate_directory, "*-key.pem"))):
        cert_path = key_path.replace("-key.pem", ".pem")
        if os.path.isfile(cert_path):
            return cert_path, key_path
    return "", ""


def _resolve_tls(section, certificate_directory):
    """Return copied CA/client certificate paths for one RHSM section."""
    ca_cert = _managed_path(
        section.get("sslcacert"), certificate_directory, "redhat-uep.pem"
    )
    client_cert = _managed_path(
        section.get("sslclientcert"), certificate_directory
    )
    client_key = _managed_path(
        section.get("sslclientkey"), certificate_directory
    )
    if not client_cert or not client_key:
        client_cert, client_key = _fallback_client_pair(
            certificate_directory
        )
    if not ca_cert or not client_cert or not client_key:
        raise SubscriptionRepositoryError(
            "Required copied RHEL subscription certificates are unavailable"
        )
    return ca_cert, client_cert, client_key


def resolve_subscription_repositories(
        repo_sections, certificate_directory, os_version, architectures,
        repository_names_by_arch, repository_configurations_by_arch,
        global_standard=False, global_policy="partial", global_caching=True,
        builtin_repositories=BUILTIN_REPOSITORIES):
    """Resolve catalog-selected empty URLs into Pulp-ready repository records."""
    if not isinstance(global_standard, bool):
        raise SubscriptionRepositoryError("Global standard must be a boolean")
    if not isinstance(global_caching, bool):
        raise SubscriptionRepositoryError(
            "Global repository caching must be a boolean"
        )
    available_repo_ids = set(repo_sections)
    repositories_by_arch = {
        architecture: [] for architecture in SUPPORTED_ARCHITECTURES
    }
    unresolved_by_arch = {
        architecture: [] for architecture in SUPPORTED_ARCHITECTURES
    }

    for architecture in architectures:
        _validate_context(os_version, architecture)
        configured = repository_configurations_by_arch.get(
            architecture, {}
        )
        for repo_name in dict.fromkeys(
                repository_names_by_arch.get(architecture, [])):
            repo_config = configured.get(repo_name, {})
            if not isinstance(repo_config, dict):
                unresolved_by_arch[architecture].append(repo_name)
                continue
            standard = repo_config.get("standard", global_standard)
            if not isinstance(standard, bool):
                raise SubscriptionRepositoryError(
                    "Repository standard must be a boolean"
                )

            candidates = subscription_repo_id_candidates(
                repo_name, architecture, os_version, available_repo_ids,
                builtin_repositories=builtin_repositories,
            )
            selected_repo_id = (
                candidates["standard"]
                if standard
                else candidates["eus"] or candidates["standard"]
            )
            if not selected_repo_id:
                unresolved_by_arch[architecture].append(repo_name)
                continue

            section = repo_sections[selected_repo_id]
            raw_url = section.get("baseurl", "")
            if not raw_url:
                unresolved_by_arch[architecture].append(repo_name)
                continue
            url = _resolve_url(raw_url, os_version, architecture)
            ca_cert, client_cert, client_key = _resolve_tls(
                section, certificate_directory
            )
            repositories_by_arch[architecture].append({
                "architecture": architecture,
                "name": repo_name,
                "url": url,
                "gpgkey": repo_config.get("gpgkey", "") or "",
                "policy": repo_config.get("policy", global_policy),
                "caching": repo_config.get("caching", global_caching),
                "priority": repo_config.get("priority"),
                "sslcacert": ca_cert,
                "sslclientcert": client_cert,
                "sslclientkey": client_key,
            })

    return repositories_by_arch, unresolved_by_arch
