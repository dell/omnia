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
"""Security helpers shared by Repo Manager command and logging boundaries."""

import ipaddress
import re
import shlex
from urllib.parse import parse_qsl, unquote, urlsplit, urlunsplit


SENSITIVE_COMMAND_OPTIONS = frozenset({
    "--ca-cert",
    "--client-cert",
    "--client-key",
    "--password",
    "--token",
    "--username",
})

_URL_USERINFO_PATTERN = re.compile(
    r"(?i)\b(https?://)([^\s/?#]*@)"
)
_SAFE_REPOSITORY_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
_SAFE_PYTHON_PACKAGE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_SAFE_PYTHON_VERSION_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9.!+_*-]*$"
)
_SAFE_ARTIFACT_IDENTIFIER_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.+=-]*$"
)
_SAFE_CONTAINER_SEGMENT_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
)
_SAFE_CONTAINER_AUTHORITY_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(?::[0-9]{1,5})?$"
)
_BRACKETED_IPV6_AUTHORITY_PATTERN = re.compile(
    r"^\[([0-9A-Fa-f:.]+)\](?::([0-9]{1,5}))?$"
)
_SAFE_CONTAINER_TAG_PATTERN = re.compile(
    r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$"
)
_SAFE_CONTAINER_DIGEST_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z0-9]*(?:[+._-][A-Za-z][A-Za-z0-9]*)*:"
    r"[A-Za-z0-9=_-]{32,}$"
)
_CONTROL_OR_WHITESPACE_PATTERN = re.compile(r"[\x00-\x20\x7f]")
_MALFORMED_PERCENT_ESCAPE_PATTERN = re.compile(r"%(?![0-9A-Fa-f]{2})")
_SENSITIVE_QUERY_KEYS = frozenset({
    "accesstoken",
    "apikey",
    "auth",
    "authorization",
    "credential",
    "credentials",
    "password",
    "passwd",
    "secret",
    "sig",
    "signature",
    "token",
    "xamzcredential",
    "xamzsecuritytoken",
    "xamzsignature",
    "xgoogcredential",
    "xgoogsignature",
})


class ArtifactUrlValidationError(ValueError):
    """Raised when a catalog artifact URL violates the public URL contract."""


def url_contains_credentials(url):
    """Return whether an HTTP(S) URL contains authority user information."""
    if not isinstance(url, str):
        return False
    try:
        parsed = urlsplit(url)
        return parsed.username is not None or parsed.password is not None
    except ValueError:
        # Malformed ports/IPv6 are handled by normal URL validation. Do not
        # classify them as credential-bearing unless userinfo is parseable.
        return False


def validate_repository_url(url):
    """Return a repository URL after rejecting malformed or credentialed input."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("Repository URL must be a non-empty string")
    if url != url.strip() or _CONTROL_OR_WHITESPACE_PATTERN.search(url):
        raise ValueError("Repository URL is malformed")
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except ValueError as error:
        raise ValueError("Repository URL is malformed") from error
    if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
        raise ValueError("Repository URL must use HTTP or HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Repository URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("Repository URL must not contain a query or fragment")
    return url


def validate_artifact_url(url):
    """Return a safe HTTP(S) artifact URL, preserving benign query values.

    Download endpoints sometimes select a public artifact through a query
    parameter, for example ``download.php?version=1.7.7``. Repository remotes
    use a stricter contract because their URL is persisted by Pulp; artifact
    URLs may retain a query only when it contains no credential-like keys.
    """
    if not isinstance(url, str) or not url.strip():
        raise ArtifactUrlValidationError(
            "Artifact URL must be a non-empty string"
        )
    if (
            url != url.strip()
            or _CONTROL_OR_WHITESPACE_PATTERN.search(url)
            or _MALFORMED_PERCENT_ESCAPE_PATTERN.search(url)
    ):
        raise ArtifactUrlValidationError("Artifact URL is malformed")

    try:
        parsed = urlsplit(url)
        _ = parsed.port
        query_items = parse_qsl(
            parsed.query, keep_blank_values=True, strict_parsing=False
        )
    except ValueError as error:
        raise ArtifactUrlValidationError("Artifact URL is malformed") from error

    if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
        raise ArtifactUrlValidationError(
            "Artifact URL must use HTTP or HTTPS"
        )
    if parsed.username is not None or parsed.password is not None:
        raise ArtifactUrlValidationError(
            "Artifact URL must not contain credentials"
        )
    if parsed.fragment:
        raise ArtifactUrlValidationError(
            "Artifact URL must not contain a fragment"
        )

    for query_key, _query_value in query_items:
        normalized_key = re.sub(r"[^a-z0-9]", "", query_key.casefold())
        if (
                normalized_key in _SENSITIVE_QUERY_KEYS
                or normalized_key.endswith("password")
                or normalized_key.endswith("secret")
                or normalized_key.endswith("token")
                or normalized_key.endswith("signature")
        ):
            raise ArtifactUrlValidationError(
                "Artifact URL query must not contain credentials"
            )

    return url


def normalize_pulp_distribution_url(  # pylint: disable=too-many-branches
        base_url, trusted_origin):
    """Return a Pulp distribution URL bound to the configured HTTPS origin.

    Pulp versions may return either an absolute URL or a root-relative content
    path. Only the path is accepted from Pulp; the scheme and authority always
    come from the locally configured Pulp endpoint. This prevents a malformed
    or compromised API response from redirecting DNF or artifact downloads to
    another host.
    """
    if not isinstance(base_url, str) or not base_url:
        raise ValueError("Pulp distribution URL is missing")
    if not isinstance(trusted_origin, str) or not trusted_origin:
        raise ValueError("Trusted Pulp origin is missing")
    if (
            _CONTROL_OR_WHITESPACE_PATTERN.search(base_url)
            or _CONTROL_OR_WHITESPACE_PATTERN.search(trusted_origin)
    ):
        raise ValueError("Pulp distribution URL is malformed")

    try:
        origin = urlsplit(trusted_origin)
        distribution = urlsplit(base_url)
        # Accessing port forces urllib to validate malformed port values.
        _ = origin.port
        _ = distribution.port
    except ValueError as error:
        raise ValueError("Pulp distribution URL is malformed") from error

    if origin.scheme.lower() != "https" or not origin.hostname:
        raise ValueError("Trusted Pulp origin must be an HTTPS origin")
    if origin.username is not None or origin.password is not None:
        raise ValueError("Trusted Pulp origin must be an HTTPS origin")
    if origin.query or origin.fragment or origin.path not in ("", "/"):
        raise ValueError("Trusted Pulp origin must be an HTTPS origin")

    if distribution.username is not None or distribution.password is not None:
        raise ValueError("Pulp distribution URL is not permitted")
    if distribution.query or distribution.fragment:
        raise ValueError("Pulp distribution URL is not permitted")
    if distribution.scheme and distribution.scheme.lower() not in ("http", "https"):
        raise ValueError("Pulp distribution URL is not HTTP(S)")
    if not distribution.scheme and distribution.netloc:
        raise ValueError("Scheme-relative Pulp distribution URLs are not permitted")
    if distribution.scheme:
        distribution_port = distribution.port or (
            443 if distribution.scheme.lower() == "https" else 80
        )
        origin_port = origin.port or 443
        if (
                distribution.scheme.lower() != "https"
                or not distribution.hostname
                or distribution.hostname.lower() != origin.hostname.lower()
                or distribution_port != origin_port
        ):
            raise ValueError("Pulp distribution URL authority is not permitted")

    path = distribution.path
    if not path:
        raise ValueError("Pulp distribution URL path is missing")
    if len(path) > 4096:
        raise ValueError("Pulp distribution URL path is malformed")
    decoded_path = path
    for _ in range(len(path) + 1):
        next_path = unquote(decoded_path)
        if next_path == decoded_path:
            break
        decoded_path = next_path
    else:
        raise ValueError("Pulp distribution URL path is malformed")
    if (
            _CONTROL_OR_WHITESPACE_PATTERN.search(decoded_path)
            or "\\" in decoded_path
            or any(segment in (".", "..") for segment in decoded_path.split("/"))
    ):
        raise ValueError("Pulp distribution URL path is malformed")
    if not path.startswith("/"):
        path = f"/{path}"

    canonical_path = f"{path.rstrip('/')}/"
    return urlunsplit(("https", origin.netloc, canonical_path, "", ""))


def normalize_managed_python_distribution_url(
        base_url, base_path, trusted_origin):
    """Normalize a Pulp Python URL without trusting its internal authority.

    ``pulp_python`` can report its container-internal content authority as
    ``https://pulp``.  Accept that one managed service identity only when its
    path exactly matches the distribution's validated ``base_path``.  The
    public scheme and authority still come exclusively from ``trusted_origin``.
    All other absolute authorities continue through the strict generic check.
    """
    if not isinstance(base_path, str) or not base_path:
        raise ValueError("Pulp Python distribution base path is missing")

    try:
        distribution = urlsplit(base_url)
        distribution_port = distribution.port
    except (TypeError, ValueError) as error:
        raise ValueError("Pulp distribution URL is malformed") from error

    expected_path = f"/pypi/{base_path.strip('/')}"
    if distribution.scheme and distribution.hostname == "pulp":
        if (
                distribution.scheme.lower() != "https"
                or distribution_port not in (None, 443)
        ):
            raise ValueError("Pulp distribution URL is not permitted")
        if (
                distribution.username is not None
                or distribution.password is not None
                or distribution.query
                or distribution.fragment
        ):
            raise ValueError("Pulp distribution URL is not permitted")

        if distribution.path.rstrip('/') != expected_path:
            raise ValueError("Pulp Python distribution path is not permitted")
        normalized_url = normalize_pulp_distribution_url(
            f"{expected_path}/", trusted_origin
        )
    else:
        normalized_url = normalize_pulp_distribution_url(
            base_url, trusted_origin
        )

    if urlsplit(normalized_url).path.rstrip('/') != expected_path:
        raise ValueError("Pulp Python distribution path is not permitted")
    return normalized_url


def validate_repository_id(repository_id):
    """Return a repository identifier safe for an INI section header."""
    if (
            not isinstance(repository_id, str)
            or not repository_id
            or not _SAFE_REPOSITORY_ID_PATTERN.fullmatch(repository_id)
    ):
        raise ValueError("Repository identifier contains unsupported characters")
    return repository_id


def validate_python_package_name(package_name):
    """Return a Python package name safe for paths and requirement argv."""
    if (
            not isinstance(package_name, str)
            or not _SAFE_PYTHON_PACKAGE_PATTERN.fullmatch(package_name)
    ):
        raise ValueError("Python package name contains unsupported characters")
    return package_name


def validate_python_package_version(version):
    """Return a pinned Python package version safe for a requirement argv."""
    if (
            not isinstance(version, str)
            or not _SAFE_PYTHON_VERSION_PATTERN.fullmatch(version)
    ):
        raise ValueError("Python package version contains unsupported characters")
    return version


def parse_python_requirement(package_name, configured_version=None):
    """Return validated Python package, version and canonical requirement.

    Repo Manager catalogs historically represent Python packages either as an
    embedded requirement (``cffi==1.17.1``) or as a package plus a separate
    version value.  Resolve both forms through one validation path so task
    naming, download processing and cleanup use the same logical identity.

    An unversioned package remains supported.  When both forms provide a
    version, they must agree.

    Returns:
        tuple[str, Optional[str], str]: Package name, optional version and the
        canonical requirement used by pip, Pulp naming and local state.
    """
    if not isinstance(package_name, str) or not package_name:
        raise ValueError("Python package requirement must be a non-empty string")

    if package_name.count("==") > 1:
        raise ValueError("Python package requirement is malformed")

    requirement_name = package_name
    embedded_version = None
    if "==" in package_name:
        requirement_name, embedded_version = package_name.split("==", 1)
        if not requirement_name or not embedded_version:
            raise ValueError("Python package requirement is malformed")

    requirement_name = validate_python_package_name(requirement_name)
    if embedded_version is not None:
        embedded_version = validate_python_package_version(embedded_version)

    separate_version = None
    if configured_version not in (None, ""):
        separate_version = validate_python_package_version(configured_version)

    if (
            embedded_version is not None
            and separate_version is not None
            and embedded_version != separate_version
    ):
        raise ValueError("Python package versions conflict")

    version = embedded_version or separate_version
    canonical_requirement = (
        f"{requirement_name}=={version}" if version else requirement_name
    )
    return requirement_name, version, canonical_requirement


def validate_python_repository_id(repository_id):
    """Return a safe Pulp Python repository/distribution identifier.

    Generic Repo Manager repository identifiers intentionally exclude ``=``.
    Python repositories preserve the established
    ``..._pip_module<package>==<version>`` identity, so only the validated
    requirement portion receives this narrow exception.  Unversioned and
    legacy generic identifiers continue through the strict common validator.
    """
    if not isinstance(repository_id, str) or not repository_id:
        raise ValueError("Python repository identifier is malformed")

    if "==" not in repository_id:
        return validate_repository_id(repository_id)

    marker = "_pip_module"
    context_prefix, separator, requirement = repository_id.partition(marker)
    if not separator or not context_prefix or not requirement:
        raise ValueError("Python repository identifier is malformed")

    validate_repository_id(context_prefix)
    _name, _version, canonical_requirement = parse_python_requirement(
        requirement
    )
    if canonical_requirement != requirement:
        raise ValueError("Python repository identifier is malformed")
    return repository_id


def validate_artifact_identifier(identifier):
    """Return a non-image artifact identifier safe for paths and logs."""
    if (
            not isinstance(identifier, str)
            or not _SAFE_ARTIFACT_IDENTIFIER_PATTERN.fullmatch(identifier)
    ):
        raise ValueError("Artifact identifier contains unsupported characters")
    return identifier


def validate_container_reference(reference):
    """Return a registry/image path without option or path injection syntax."""
    if not isinstance(reference, str) or _CONTROL_OR_WHITESPACE_PATTERN.search(
            reference):
        raise ValueError("Container image reference contains unsupported characters")

    segments = reference.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise ValueError("Container image reference contains unsupported characters")

    authority = segments[0]
    ipv6_match = _BRACKETED_IPV6_AUTHORITY_PATTERN.fullmatch(authority)
    if ipv6_match:
        try:
            ipaddress.IPv6Address(ipv6_match.group(1))
        except ipaddress.AddressValueError as error:
            raise ValueError(
                "Container image reference contains unsupported characters"
            ) from error
        port = ipv6_match.group(2)
        if port and not 1 <= int(port) <= 65535:
            raise ValueError("Container registry port is invalid")
    else:
        if not _SAFE_CONTAINER_AUTHORITY_PATTERN.fullmatch(authority):
            raise ValueError(
                "Container image reference contains unsupported characters"
            )
        if ":" in authority:
            port = authority.rsplit(":", maxsplit=1)[1]
            if not 1 <= int(port) <= 65535:
                raise ValueError("Container registry port is invalid")

    if not all(
            _SAFE_CONTAINER_SEGMENT_PATTERN.fullmatch(segment)
            for segment in segments[1:]
    ):
        raise ValueError("Container image reference contains unsupported characters")
    return reference


def validate_container_tag(tag):
    """Return an OCI/Docker tag safe for Pulp CLI and status output."""
    if not isinstance(tag, str) or not _SAFE_CONTAINER_TAG_PATTERN.fullmatch(tag):
        raise ValueError("Container image tag contains unsupported characters")
    return tag


def validate_container_digest(digest):
    """Return an OCI digest safe for use as one Pulp CLI argument."""
    if (
            not isinstance(digest, str)
            or not _SAFE_CONTAINER_DIGEST_PATTERN.fullmatch(digest)
    ):
        raise ValueError("Container image digest contains unsupported characters")
    return digest


def validate_pulp_policy(policy):
    """Return a Pulp download policy from the supported allowlist."""
    if policy not in ("immediate", "on_demand", "streamed"):
        raise ValueError("Pulp remote policy is unsupported")
    return policy


def validate_container_policy(policy):
    """Return a Pulp container policy from the shared policy allowlist."""
    return validate_pulp_policy(policy)


def redact_url_credentials(value):
    """Redact HTTP(S) authority user information from arbitrary text."""
    return _URL_USERINFO_PATTERN.sub(r"\1******@", str(value))


def validate_no_url_credentials(value):
    """Reject credential-bearing HTTP(S) URLs nested in structured data."""
    if isinstance(value, dict):
        for nested_value in value.values():
            validate_no_url_credentials(nested_value)
    elif isinstance(value, (list, tuple, set)):
        for nested_value in value:
            validate_no_url_credentials(nested_value)
    elif isinstance(value, str) and value.lstrip().lower().startswith(
            ("http://", "https://")):
        if url_contains_credentials(value.strip()):
            raise ValueError("URLs must not contain credentials")


def redact_sensitive_value(value, key_name=""):
    """Return a log-safe copy of nested command/task data."""
    sensitive_keys = {
        "ca_cert",
        "ca_path",
        "client_cert",
        "client_cert_path",
        "client_key",
        "client_key_path",
        "password",
        "sslcacert",
        "sslclientcert",
        "sslclientkey",
        "token",
        "username",
    }
    if str(key_name).lower() in sensitive_keys:
        return "******" if value else value
    if isinstance(value, dict):
        return {
            key: redact_sensitive_value(nested_value, key)
            for key, nested_value in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive_value(item) for item in value)
    if isinstance(value, str):
        return redact_url_credentials(value)
    return value


def _as_command_args(command):
    """Return command arguments when they can be parsed without execution."""
    if isinstance(command, (list, tuple)):
        return [str(value) for value in command]
    try:
        return shlex.split(str(command))
    except ValueError:
        return None


def mask_sensitive_data(command):
    """Return a log-safe rendering of a string or argv command."""
    command_args = _as_command_args(command)
    if command_args is None:
        # Never return an unredacted URL from a malformed command. Sensitive
        # option values cannot be safely identified when quoting is invalid.
        command_text = str(command)
        if any(option in command_text for option in SENSITIVE_COMMAND_OPTIONS):
            return "<command omitted: invalid sensitive argument quoting>"
        return redact_url_credentials(command_text)

    safe_args = [redact_url_credentials(value) for value in command_args]
    for index, value in enumerate(command_args):
        option, separator, _option_value = value.partition("=")
        if separator and option in SENSITIVE_COMMAND_OPTIONS:
            safe_args[index] = f"{option}=******"
    for index, value in enumerate(command_args[:-1]):
        if value in SENSITIVE_COMMAND_OPTIONS:
            safe_args[index + 1] = "******"
    return shlex.join(safe_args)


def redact_sensitive_output(output, command):
    """Remove command secrets and URL userinfo echoed by subprocess output."""
    if not output:
        return output

    redacted = redact_url_credentials(output)
    command_args = _as_command_args(command)
    if command_args is None:
        return redacted

    for index, value in enumerate(command_args[:-1]):
        if value in SENSITIVE_COMMAND_OPTIONS:
            secret = command_args[index + 1]
            if secret:
                redacted = redacted.replace(secret, "******")
                if secret.startswith("@"):
                    redacted = redacted.replace(secret[1:], "******")

    for value in command_args:
        option, separator, secret = value.partition("=")
        if separator and option in SENSITIVE_COMMAND_OPTIONS and secret:
            redacted = redacted.replace(secret, "******")

    for value in command_args:
        try:
            parsed = urlsplit(value)
        except ValueError:
            continue
        if parsed.username is not None or parsed.password is not None:
            userinfo = parsed.netloc.rsplit("@", 1)[0]
            if userinfo:
                redacted = redacted.replace(userinfo, "******")
    return redacted
