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

"""In-process HTTPS helpers for the BuildStream and GitLab APIs.

Requests are sent from the test process with ``urllib`` so tokens, client
secrets and request bodies stay in memory: they never appear on a command
line, in a process listing or in returned error text. Every context passed in
verifies the server certificate (see ``tls_from_pem``).
"""

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Unpack

from ..vars.execute_vars import HTTP_TIMEOUT


class HttpOptions(TypedDict, total=False):
    """Optional ``http_json`` keywords: request headers and a JSON or form body."""

    headers: Optional[Dict[str, str]]
    payload: Optional[Dict[str, Any]]
    form: Optional[Dict[str, str]]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Report a redirect as its own status instead of following it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # pylint: disable=too-many-arguments,too-many-positional-arguments
        return None


def tls_from_pem(pem: str, *, leaf_is_anchor: bool = False) -> ssl.SSLContext:
    """Return a context that trusts only ``pem`` and checks the host name.

    Args:
        pem: CA (or self-signed server) certificate in PEM form.
        leaf_is_anchor: Trust a self-signed server certificate directly.

    Raises:
        ssl.SSLError: When the PEM text is not a certificate.
    """
    context = ssl.create_default_context(cadata=pem)
    if leaf_is_anchor:
        context.verify_flags |= ssl.VerifyFlags.VERIFY_X509_PARTIAL_CHAIN
    return context


def _encode_body(options: HttpOptions) -> Tuple[Optional[bytes], Dict[str, str]]:
    """Return the request body and headers for a JSON or form payload."""
    headers = dict(options.get("headers") or {})
    payload, form = options.get("payload"), options.get("form")
    if payload is not None:
        headers["Content-Type"] = "application/json"
        return json.dumps(payload).encode(), headers
    if form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        return urllib.parse.urlencode(form).encode(), headers
    return None, headers


def http_exchange(tls: ssl.SSLContext, method: str, url: str, *,
                  headers: Optional[Dict[str, str]] = None,
                  body: Optional[bytes] = None,
                  timeout: int = HTTP_TIMEOUT) -> Dict[str, Any]:
    """Send one request and return its status and body, including 4xx/5xx answers.

    Returns:
        Dict with keys: success (a response was received), status, body
        (text), json (decoded body or None), error (never echoes headers or
        bodies).
    """
    request = urllib.request.Request(url, data=body, headers=dict(headers or {}),
                                     method=method)
    try:
        with urllib.request.urlopen(  # nosec B310  # https URL built from validated config
            request, context=tls, timeout=timeout
        ) as response:
            status, raw = response.status, response.read().decode(errors="replace")
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read().decode(errors="replace")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"success": False, "status": 0, "body": "", "json": None,
                "error": f"{method} {url} failed: {exc}"}
    try:
        parsed = json.loads(raw) if raw.strip() else None
    except json.JSONDecodeError:
        parsed = None
    return {"success": True, "status": status, "body": raw, "json": parsed, "error": ""}


def http_json(tls: ssl.SSLContext, method: str, url: str,
              **options: Unpack[HttpOptions]) -> Dict[str, Any]:
    """Send an HTTP request over ``tls`` and decode a JSON response.

    ``options`` takes headers, payload (sent as JSON) or form (sent
    urlencoded); payload wins over form.

    Returns:
        Dict with keys: success (2xx), status, data (decoded JSON or text),
        error (no request headers or bodies are echoed).
    """
    body, headers = _encode_body(options)
    response = http_exchange(tls, method, url, headers=headers, body=body)
    if not response["success"]:
        return {"success": False, "status": 0, "data": None, "error": response["error"]}
    if not 200 <= response["status"] < 300:
        return {"success": False, "status": response["status"], "data": None,
                "error": f"HTTP {response['status']} for {method} {url}"}
    data = response["json"] if response["json"] is not None else (response["body"] or None)
    return {"success": True, "status": response["status"], "data": data, "error": ""}


def http_status(tls: ssl.SSLContext, url: str) -> int:
    """Return the HTTP status of ``GET url`` without following redirects (0 = no answer)."""
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=tls), _NoRedirect)
    try:
        with opener.open(url, timeout=HTTP_TIMEOUT) as response:  # nosec B310
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except (urllib.error.URLError, OSError, ValueError):
        return 0


def multipart_body(files: List[Tuple[str, str, bytes]]) -> Tuple[bytes, str]:
    """Encode ``(field, filename, content)`` parts as multipart/form-data.

    Returns:
        (body, Content-Type header value).
    """
    boundary = f"omnia-{uuid.uuid4().hex}"
    chunks: List[bytes] = []
    for field, filename, content in files:
        chunks.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; "
            f"filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n"
            .encode()
        )
        chunks.extend([content, b"\r\n"])
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"
