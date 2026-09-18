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

"""Safe, transactional client for SFM Observability REST APIs."""

import copy
import math
import time

import requests

from ..messages.sfm_msgs import SFM_DETAIL_MSGS, SFM_ERROR_MSGS
from ..vars.sfm_vars import (
    SFM_ACCESS_TOKEN_KEYS,
    SFM_ACTIONS,
    SFM_API_AUTH_HEADER,
    SFM_API_BEARER_TEMPLATE,
    SFM_API_DELETE_POLL_ATTEMPTS,
    SFM_API_DELETE_POLL_INTERVAL_SECONDS,
    SFM_API_MULTIPART_FIELD,
    SFM_API_PATHS,
    SFM_API_REDACTED_PREVIEW,
    SFM_API_REQUEST_FIELDS,
    SFM_API_RESPONSE_KEYS,
    SFM_API_RESPONSE_PREVIEW_LENGTH,
    SFM_API_SCHEME,
    SFM_API_TIMEOUT_SECONDS,
    SFM_API_UNAUTHORIZED_STATUS,
    SFM_API_VERIFY_TLS,
    SFM_CA_CERTIFICATE_CONTENT_TYPE,
    SFM_CA_CERTIFICATE_FILE,
    SFM_HEALTH_POLL_ATTEMPTS,
    SFM_HEALTH_POLL_INTERVAL_SECONDS,
    SFM_HEALTH_QUERIES,
    SFM_HTTP_METHODS,
    SFM_HTTP_SUCCESS,
    SFM_MAX_FAILED_SAMPLES,
    SFM_MAX_HEALTH_SAMPLE_AGE_SECONDS,
    SFM_MAX_PENDING_GROWTH,
    SFM_QUERY_RANGE_STEP_SECONDS,
    SFM_QUERY_RANGE_WINDOW_SECONDS,
    SFM_REMOTE_WRITE_AUTHORIZATION_TYPE,
    SFM_REMOTE_WRITE_FIELDS,
    SFM_REMOTE_WRITE_MESSAGE_VERSION,
    SFM_REMOTE_WRITE_OAUTH_CONFIG,
    SFM_REMOTE_WRITE_STATE,
    SFM_REMOTE_WRITE_TARGET_NAME,
    SFM_REMOTE_WRITE_TLS_VERIFY,
    SFM_REMOTE_WRITE_URL,
    SFM_REQUIRED_HEALTH_QUERIES,
)


class SfmApiError(RuntimeError):
    """Safe error raised by SFM API operations."""


def _access_token(payload):
    """Return an access token recursively while ignoring refresh-token keys."""
    if isinstance(payload, list):
        for value in payload:
            token = _access_token(value)
            if token:
                return token
        return ""
    if not isinstance(payload, dict):
        return ""
    for key in SFM_ACCESS_TOKEN_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    for key, value in payload.items():
        if "refresh" in str(key).lower():
            continue
        if isinstance(value, (dict, list)):
            token = _access_token(value)
            if token:
                return token
    return ""


class _SfmApiClient:
    """Authenticated client for the SFM Observability endpoints."""

    def __init__(self, context):
        """Initialize an unauthenticated client from validated SFM context."""
        self.context = context
        self.base_url = (
            f"{SFM_API_SCHEME}://{context['api_ip']}:{context['api_port']}"
        )
        self.session = requests.Session()

    def __enter__(self):
        """Authenticate and return this API client."""
        self._login()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close the HTTP session when leaving the context manager."""
        self.session.close()

    def _path(self, name, **values):
        """Format one centralized SFM API path with fixed instance data."""
        return SFM_API_PATHS[name].format(
            instance_id=self.context["instance_id"], **values,
        )

    def _response_preview(self, response, path):
        """Return a bounded response preview without exposing login data."""
        if path == self._path("login"):
            return SFM_API_REDACTED_PREVIEW
        return response.text[:SFM_API_RESPONSE_PREVIEW_LENGTH]

    def _request(
        self,
        method,
        path,
        expected,
        allow_reauthentication=True,
        **kwargs,
    ):
        """Send one validated HTTP request with one authentication retry."""
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(
                method,
                url,
                timeout=SFM_API_TIMEOUT_SECONDS,
                verify=SFM_API_VERIFY_TLS,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise SfmApiError(
                SFM_ERROR_MSGS["api_request_failed"].format(
                    path=path, error=exc,
                )
            ) from exc

        if (
            response.status_code == SFM_API_UNAUTHORIZED_STATUS
            and allow_reauthentication
            and path != self._path("login")
        ):
            self._login()
            return self._request(
                method,
                path,
                expected,
                allow_reauthentication=False,
                **kwargs,
            )

        if response.status_code not in expected:
            raise SfmApiError(
                SFM_ERROR_MSGS["api_http_failed"].format(
                    status=response.status_code,
                    path=path,
                    body=self._response_preview(response, path),
                )
            )
        if not response.content:
            return {}
        try:
            return response.json()
        except requests.JSONDecodeError as exc:
            raise SfmApiError(
                SFM_ERROR_MSGS["api_json_invalid"].format(
                    path=path, error=exc,
                )
            ) from exc

    def _login(self):
        """Authenticate and install the returned bearer token on the session."""
        payload = {
            SFM_API_REQUEST_FIELDS["username"]: self.context["api_username"],
            SFM_API_REQUEST_FIELDS["password"]: self.context["api_password"],
        }
        response = self._request(
            SFM_HTTP_METHODS["post"],
            self._path("login"),
            SFM_HTTP_SUCCESS["login"],
            allow_reauthentication=False,
            json=payload,
        )
        token = _access_token(response)
        if not token:
            raise SfmApiError(SFM_ERROR_MSGS["api_token_missing"])
        self.session.headers.update({
            SFM_API_AUTH_HEADER: SFM_API_BEARER_TEMPLATE.format(token=token),
        })

    def remote_writes(self):
        """Return all configured Prometheus Remote Write targets."""
        return self._request(
            SFM_HTTP_METHODS["get"],
            self._path("remote_write_list"),
            SFM_HTTP_SUCCESS["read"],
        )

    def create_import(self):
        """Create a certificate-import parent for the Victoria target."""
        return self._request(
            SFM_HTTP_METHODS["post"],
            self._path("certificate_import"),
            SFM_HTTP_SUCCESS["create"],
            json={
                SFM_API_REQUEST_FIELDS["target_name"]:
                    SFM_REMOTE_WRITE_TARGET_NAME,
            },
        )

    def upload_server_certificate(self, import_id, certificate):
        """Upload the Victoria CA and validate the returned import ID."""
        files = {
            SFM_API_MULTIPART_FIELD: (
                SFM_CA_CERTIFICATE_FILE,
                certificate,
                SFM_CA_CERTIFICATE_CONTENT_TYPE,
            ),
        }
        response = self._request(
            SFM_HTTP_METHODS["post"],
            self._path("server_certificate", import_id=import_id),
            SFM_HTTP_SUCCESS["create"],
            files=files,
        )
        response_id = _required_id(
            response, SFM_API_RESPONSE_KEYS["import_id"],
        )
        if response_id != import_id:
            raise SfmApiError(
                SFM_ERROR_MSGS["api_id_mismatch"].format(
                    field=SFM_API_RESPONSE_KEYS["import_id"],
                    value=response_id,
                )
            )
        return response

    def certificate_detail(self, import_id):
        """Return certificate metadata for one import parent."""
        return self._request(
            SFM_HTTP_METHODS["get"],
            self._path("certificate_import_detail", import_id=import_id),
            SFM_HTTP_SUCCESS["read"],
        )

    def create_remote_write(self, payload):
        """Create a Prometheus Remote Write target."""
        return self._request(
            SFM_HTTP_METHODS["post"],
            self._path("remote_write"),
            SFM_HTTP_SUCCESS["create"],
            json=payload,
        )

    def update_remote_write(self, remote_write_id, payload):
        """Update an existing Prometheus Remote Write target."""
        return self._request(
            SFM_HTTP_METHODS["put"],
            self._path(
                "remote_write_item", remote_write_id=remote_write_id,
            ),
            SFM_HTTP_SUCCESS["update"],
            json=payload,
        )

    def delete_remote_write(self, remote_write_id):
        """Delete a Prometheus Remote Write target."""
        return self._request(
            SFM_HTTP_METHODS["delete"],
            self._path(
                "remote_write_item", remote_write_id=remote_write_id,
            ),
            SFM_HTTP_SUCCESS["delete"],
        )

    def delete_import(self, import_id):
        """Delete an unreferenced certificate-import parent."""
        return self._request(
            SFM_HTTP_METHODS["delete"],
            self._path("certificate_import_item", import_id=import_id),
            SFM_HTTP_SUCCESS["delete"],
        )

    def query_range(self, query, start, end):
        """Run one authenticated range query through the SFM API."""
        return self._request(
            SFM_HTTP_METHODS["get"],
            self._path("query_range"),
            SFM_HTTP_SUCCESS["read"],
            params={
                "query": query,
                "start": start,
                "end": end,
                "step": SFM_QUERY_RANGE_STEP_SECONDS,
            },
        )


def _remote_write_rows(payload):
    """Normalize the Remote Write list response to target mappings."""
    rows = payload.get(SFM_API_RESPONSE_KEYS["remote_write_table"])
    if not isinstance(rows, list):
        raise SfmApiError(SFM_ERROR_MSGS["api_rows_invalid"])
    return [row for row in rows if isinstance(row, dict)]


def _target_row(rows):
    """Return the unique Victoria target or ``None``."""
    matches = [
        row for row in rows
        if row.get(SFM_API_REQUEST_FIELDS["target_name"])
        == SFM_REMOTE_WRITE_TARGET_NAME
    ]
    if len(matches) > 1:
        raise SfmApiError(
            SFM_ERROR_MSGS["api_duplicate_target"].format(
                target=SFM_REMOTE_WRITE_TARGET_NAME,
            )
        )
    return matches[0] if matches else None


def _validate_mutable_target(row):
    """Refuse targets whose unreadable OAuth secret prevents safe rollback."""
    if row is None:
        return
    auth_field = SFM_API_REQUEST_FIELDS["authorization_type"]
    if row.get(auth_field) != SFM_REMOTE_WRITE_AUTHORIZATION_TYPE:
        raise SfmApiError(
            SFM_ERROR_MSGS["api_target_auth_conflict"].format(
                target=SFM_REMOTE_WRITE_TARGET_NAME,
                authorization=row.get(auth_field),
            )
        )


def _remote_write_payload(import_id):
    """Build the complete SFM Remote Write request body."""
    return {
        SFM_API_REQUEST_FIELDS["target_name"]: SFM_REMOTE_WRITE_TARGET_NAME,
        SFM_API_REQUEST_FIELDS["url"]: SFM_REMOTE_WRITE_URL,
        SFM_API_REQUEST_FIELDS["state"]: SFM_REMOTE_WRITE_STATE,
        SFM_API_REQUEST_FIELDS["message_version"]:
            SFM_REMOTE_WRITE_MESSAGE_VERSION,
        SFM_API_REQUEST_FIELDS["authorization_type"]:
            SFM_REMOTE_WRITE_AUTHORIZATION_TYPE,
        SFM_API_REQUEST_FIELDS["tls_verify"]: SFM_REMOTE_WRITE_TLS_VERIFY,
        SFM_API_REQUEST_FIELDS["oauth_config"]:
            copy.deepcopy(SFM_REMOTE_WRITE_OAUTH_CONFIG),
        SFM_API_REQUEST_FIELDS["certificate_import_id"]: import_id,
    }


def _rollback_payload(row):
    """Build a rollback request from a non-OAuth target readback."""
    return {
        field: copy.deepcopy(row.get(field))
        for field in SFM_REMOTE_WRITE_FIELDS
    }


def _remote_write_mismatches(row, expected):
    """Return fields whose API readback differs from the request."""
    mismatches = []
    for field, expected_value in expected.items():
        actual_value = row.get(field)
        if field == SFM_API_REQUEST_FIELDS["tls_verify"]:
            if str(actual_value).lower() != str(expected_value).lower():
                mismatches.append(field)
        elif actual_value != expected_value:
            mismatches.append(field)
    return mismatches


def _required_id(payload, field):
    """Return a required API identifier or raise a safe error."""
    value = payload.get(field) if isinstance(payload, dict) else None
    if not value:
        raise SfmApiError(
            SFM_ERROR_MSGS["api_id_missing"].format(field=field)
        )
    return str(value)


def _query_series(payload):
    """Return matrix series from a Prometheus-compatible SFM response."""
    if payload.get(SFM_API_RESPONSE_KEYS["status"]) != "success":
        raise SfmApiError(SFM_ERROR_MSGS["api_query_failed"])
    data = payload.get(SFM_API_RESPONSE_KEYS["data"])
    rows = (
        data.get(SFM_API_RESPONSE_KEYS["result"])
        if isinstance(data, dict) else None
    )
    if not isinstance(rows, list):
        raise SfmApiError(SFM_ERROR_MSGS["api_query_shape_invalid"])
    return [row for row in rows if isinstance(row, dict)]


def _numeric_samples(row):
    """Return finite ``(timestamp, value)`` samples from one matrix row."""
    samples = []
    values = row.get(SFM_API_RESPONSE_KEYS["values"], [])
    if not isinstance(values, list):
        return samples
    for value in values:
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            continue
        try:
            timestamp = float(value[0])
            sample = float(value[1])
        except (TypeError, ValueError):
            continue
        if math.isfinite(timestamp) and math.isfinite(sample):
            samples.append((timestamp, sample))
    return samples


def _aggregate_query(client, query, start, end):
    """Aggregate the first/latest values and latest time for one query."""
    rows = _query_series(client.query_range(query, start, end))
    first_value = 0.0
    latest_value = 0.0
    latest_timestamps = []
    for row in rows:
        samples = _numeric_samples(row)
        if not samples:
            continue
        first_value += samples[0][1]
        latest_value += samples[-1][1]
        latest_timestamps.append(samples[-1][0])
    return {
        "first": first_value,
        "latest": latest_value,
        "timestamp": min(latest_timestamps) if latest_timestamps else 0.0,
    }


def _health_snapshot(client):
    """Return target-scoped Remote Write rates, queue trend, and health."""
    end = time.time()
    start = end - SFM_QUERY_RANGE_WINDOW_SECONDS
    values = {
        name: _aggregate_query(client, query, start, end)
        for name, query in SFM_HEALTH_QUERIES.items()
    }
    timestamps = [
        values[name]["timestamp"] for name in SFM_REQUIRED_HEALTH_QUERIES
    ]
    oldest_timestamp = (
        min(timestamps) if all(timestamps) else 0.0
    )
    pending_growth = (
        values["pending_samples"]["latest"]
        - values["pending_samples"]["first"]
    )
    sample_age = (
        max(0.0, end - oldest_timestamp)
        if oldest_timestamp else float("inf")
    )
    health = {
        name: value["latest"] for name, value in values.items()
    }
    health.update({
        "pending_growth": pending_growth,
        "sample_age": sample_age,
    })
    health["healthy"] = (
        health["bytes_total"] > 0
        and health["samples_total"] > 0
        and health["failed_samples"] <= SFM_MAX_FAILED_SAMPLES
        and pending_growth <= SFM_MAX_PENDING_GROWTH
        and sample_age <= SFM_MAX_HEALTH_SAMPLE_AGE_SECONDS
    )
    return health


def _empty_health(error="", prerequisite_failed=False):
    """Return a complete unhealthy snapshot for safe formatting."""
    return {
        "bytes_total": 0.0,
        "samples_total": 0.0,
        "retried_samples": 0.0,
        "failed_samples": 0.0,
        "pending_samples": 0.0,
        "pending_growth": 0.0,
        "sample_age": float("inf"),
        "healthy": False,
        "error": error,
        "prerequisite_failed": prerequisite_failed,
    }


def _poll_remote_write_health(client, prepare_health=None):
    """Poll target-scoped SFM health, reapplying network setup if supplied."""
    health = _empty_health()
    for attempt in range(1, SFM_HEALTH_POLL_ATTEMPTS + 1):
        if prepare_health is not None:
            try:
                prepare_health()
            except SfmApiError as exc:
                health = _empty_health(
                    error=str(exc), prerequisite_failed=True,
                )
                if attempt < SFM_HEALTH_POLL_ATTEMPTS:
                    time.sleep(SFM_HEALTH_POLL_INTERVAL_SECONDS)
                continue
        try:
            health = _health_snapshot(client)
        except SfmApiError as exc:
            health = _empty_health(error=str(exc))
        if health.get("healthy", False):
            break
        if attempt < SFM_HEALTH_POLL_ATTEMPTS:
            time.sleep(SFM_HEALTH_POLL_INTERVAL_SECONDS)
    health.setdefault("error", "")
    health.setdefault("prerequisite_failed", False)
    return health


def _configuration_is_reusable(client, row, force_rotation):
    """Return whether exact config and certificate metadata are reusable."""
    if row is None or force_rotation:
        return False
    import_id = row.get(SFM_API_REQUEST_FIELDS["certificate_import_id"])
    remote_write_id = row.get(SFM_API_RESPONSE_KEYS["remote_write_id"])
    if not import_id or not remote_write_id:
        return False
    if _remote_write_mismatches(row, _remote_write_payload(import_id)):
        return False
    try:
        detail = client.certificate_detail(import_id)
    except SfmApiError:
        return False
    filename = detail.get(
        SFM_API_RESPONSE_KEYS["server_certificate_file"],
    )
    return filename == SFM_CA_CERTIFICATE_FILE


def _import_is_referenced(client, import_id):
    """Return whether any Remote Write target references an import ID."""
    return any(
        row.get(SFM_API_REQUEST_FIELDS["certificate_import_id"])
        == import_id
        for row in _remote_write_rows(client.remote_writes())
    )


def _wait_import_unreferenced(client, import_id):
    """Wait until asynchronous target changes release an import ID."""
    for attempt in range(1, SFM_API_DELETE_POLL_ATTEMPTS + 1):
        if not _import_is_referenced(client, import_id):
            return True
        if attempt < SFM_API_DELETE_POLL_ATTEMPTS:
            time.sleep(SFM_API_DELETE_POLL_INTERVAL_SECONDS)
    return False


def _restore_target(client, old_row, remote_write_id, new_import_id):
    """Restore or remove the target after a failed configuration."""
    id_field = SFM_API_RESPONSE_KEYS["remote_write_id"]
    if old_row is None:
        target_id = remote_write_id
        if not target_id:
            row = _target_row(_remote_write_rows(client.remote_writes()))
            import_field = SFM_API_REQUEST_FIELDS["certificate_import_id"]
            if row and str(row.get(import_field, "")) == new_import_id:
                target_id = str(row.get(id_field, ""))
        if target_id:
            client.delete_remote_write(target_id)
        return

    old_id = _required_id(old_row, id_field)
    rollback_payload = _rollback_payload(old_row)
    response = client.update_remote_write(old_id, rollback_payload)
    response_id = _required_id(response, id_field)
    if response_id != old_id:
        raise SfmApiError(
            SFM_ERROR_MSGS["api_id_mismatch"].format(
                field=id_field, value=response_id,
            )
        )
    restored = _target_row(_remote_write_rows(client.remote_writes()))
    if (
        restored is None
        or str(restored.get(id_field, "")) != old_id
        or _remote_write_mismatches(restored, rollback_payload)
    ):
        raise SfmApiError(SFM_ERROR_MSGS["api_rollback_readback_failed"])


def _rollback(
    client,
    old_row,
    remote_write_id,
    new_import_id,
    target_mutation_attempted,
):
    """Rollback the target before deleting an unreferenced new import."""
    try:
        if target_mutation_attempted:
            _restore_target(
                client, old_row, remote_write_id, new_import_id,
            )
        if new_import_id and not _wait_import_unreferenced(
            client, new_import_id,
        ):
            raise SfmApiError(
                SFM_ERROR_MSGS["api_import_still_referenced"].format(
                    import_id=new_import_id,
                )
            )
    except SfmApiError as exc:
        return SFM_DETAIL_MSGS["rollback_import_retained"].format(error=exc)

    if not new_import_id:
        return ""
    try:
        client.delete_import(new_import_id)
    except SfmApiError as exc:
        return SFM_DETAIL_MSGS["rollback_cleanup_failed"].format(error=exc)
    return ""


def _write_target(client, current_row, payload):
    """Create or update the target and return its ID and action."""
    id_field = SFM_API_RESPONSE_KEYS["remote_write_id"]
    if current_row:
        remote_write_id = _required_id(current_row, id_field)
        response = client.update_remote_write(remote_write_id, payload)
        response_id = _required_id(response, id_field)
        if response_id != remote_write_id:
            raise SfmApiError(
                SFM_ERROR_MSGS["api_id_mismatch"].format(
                    field=id_field, value=response_id,
                )
            )
        return remote_write_id, SFM_ACTIONS["updated"]
    response = client.create_remote_write(payload)
    return _required_id(response, id_field), SFM_ACTIONS["created"]


def _verify_readback(client, payload, import_id):
    """Verify target fields and uploaded certificate filename."""
    row = _target_row(_remote_write_rows(client.remote_writes()))
    if row is None:
        raise SfmApiError(SFM_ERROR_MSGS["api_readback_missing"])
    mismatches = _remote_write_mismatches(row, payload)
    if mismatches:
        raise SfmApiError(
            SFM_ERROR_MSGS["api_readback_mismatch"].format(
                fields=", ".join(mismatches),
            )
        )
    detail = client.certificate_detail(import_id)
    filename = detail.get(SFM_API_RESPONSE_KEYS["server_certificate_file"])
    if filename != SFM_CA_CERTIFICATE_FILE:
        raise SfmApiError(
            SFM_ERROR_MSGS["api_certificate_mismatch"].format(
                filename=filename,
            )
        )


def _create_import_parent(client):
    """Create one import parent and return its API identifier."""
    response = client.create_import()
    try:
        return _required_id(
            response, SFM_API_RESPONSE_KEYS["import_id"],
        )
    except SfmApiError as exc:
        raise SfmApiError(
            SFM_ERROR_MSGS["api_import_id_ambiguous"]
        ) from exc


def _upload_and_validate_import(client, import_id, certificate):
    """Upload and read back a certificate for a known import parent."""
    client.upload_server_certificate(import_id, certificate)
    detail = client.certificate_detail(import_id)
    filename = detail.get(SFM_API_RESPONSE_KEYS["server_certificate_file"])
    if filename != SFM_CA_CERTIFICATE_FILE:
        raise SfmApiError(
            SFM_ERROR_MSGS["api_certificate_mismatch"].format(
                filename=filename,
            )
        )


def _require_healthy_configuration(client, prepare_health):
    """Return health data or raise when the switched target is unhealthy."""
    health = _poll_remote_write_health(client, prepare_health)
    if health.get("healthy", False):
        return health
    reason = health.get("error") or SFM_DETAIL_MSGS["health_reason"].format(
        **health,
    )
    raise SfmApiError(
        SFM_ERROR_MSGS["remote_write_unhealthy"].format(
            attempts=SFM_HEALTH_POLL_ATTEMPTS,
            reason=reason,
        )
    )


def _retained_import_details(old_import_id, new_import_id):
    """Return retained rollback import ID and user-facing warning."""
    retained_id = old_import_id if old_import_id != new_import_id else ""
    warning = (
        SFM_DETAIL_MSGS["old_import_retained"].format(import_id=retained_id)
        if retained_id else ""
    )
    return retained_id, warning


def _rotate_configuration(
    client,
    current_row,
    certificate,
    prepare_health,
):
    """Switch to a new import, prove health, and retain rollback material."""
    old_row = copy.deepcopy(current_row)
    old_import_id = (
        str(current_row.get(
            SFM_API_REQUEST_FIELDS["certificate_import_id"], "",
        )) if current_row else ""
    )
    state = {
        "new_import_id": "",
        "target_mutation_attempted": False,
        "remote_write_id": (
            str(current_row.get(
                SFM_API_RESPONSE_KEYS["remote_write_id"], "",
            )) if current_row else ""
        ),
    }
    try:
        state["new_import_id"] = _create_import_parent(client)
        _upload_and_validate_import(
            client, state["new_import_id"], certificate,
        )
        payload = _remote_write_payload(state["new_import_id"])
        state["target_mutation_attempted"] = True
        state["remote_write_id"], action = _write_target(
            client, current_row, payload,
        )
        _verify_readback(client, payload, state["new_import_id"])
        health = _require_healthy_configuration(client, prepare_health)
    except SfmApiError as exc:
        rollback_error = _rollback(
            client,
            old_row,
            state["remote_write_id"],
            state["new_import_id"],
            state["target_mutation_attempted"],
        )
        if rollback_error:
            raise SfmApiError(
                SFM_ERROR_MSGS["api_rollback_failed"].format(
                    error=rollback_error,
                )
            ) from exc
        raise

    retained_import_id, warning = _retained_import_details(
        old_import_id, state["new_import_id"],
    )
    return {
        "action": action,
        "remote_write_id": state["remote_write_id"],
        "import_id": state["new_import_id"],
        "retained_import_id": retained_import_id,
        "warning": warning,
        "health": health,
    }


def configure_remote_write(
    context,
    certificate,
    force_rotation=False,
    prepare_health=None,
):
    """Configure and health-check the SFM Victoria Remote Write target.

    Args:
        context: Validated API connection settings and credentials.
        certificate: VictoriaMetrics CA certificate bytes.
        force_rotation: Rotate the import even if exact config is healthy.
        prepare_health: Optional callback that restores pod network mapping.

    Returns:
        Dict containing action, target/import IDs, warning, and health data.

    Raises:
        SfmApiError: If API configuration, health proof, or rollback fails.
    """
    with _SfmApiClient(context) as client:
        current_row = _target_row(_remote_write_rows(client.remote_writes()))
        _validate_mutable_target(current_row)
        if _configuration_is_reusable(client, current_row, force_rotation):
            health = _poll_remote_write_health(client, prepare_health)
            if health.get("healthy", False):
                return {
                    "action": SFM_ACTIONS["reused"],
                    "remote_write_id": str(
                        current_row[SFM_API_RESPONSE_KEYS["remote_write_id"]]
                    ),
                    "import_id": str(current_row[
                        SFM_API_REQUEST_FIELDS["certificate_import_id"]
                    ]),
                    "retained_import_id": "",
                    "warning": SFM_DETAIL_MSGS[
                        "certificate_identity_unavailable"
                    ],
                    "health": health,
                }
            if health.get("prerequisite_failed", False):
                raise SfmApiError(
                    SFM_ERROR_MSGS["health_prerequisite_failed"].format(
                        error=health.get("error", ""),
                    )
                )
            if health.get("error"):
                raise SfmApiError(
                    SFM_ERROR_MSGS["health_query_failed"].format(
                        error=health["error"],
                    )
                )
        return _rotate_configuration(
            client,
            current_row,
            certificate,
            prepare_health,
        )


def query_remote_write_health(context, prepare_health=None):
    """Poll target-scoped SFM Remote Write health without mutation.

    Args:
        context: Validated API connection settings and credentials.
        prepare_health: Optional callback that restores pod network mapping.

    Returns:
        Dict with target-scoped rates, queue trend, freshness, and ``healthy``.

    Raises:
        SfmApiError: If authentication or health API calls fail.
    """
    with _SfmApiClient(context) as client:
        return _poll_remote_write_health(client, prepare_health)
