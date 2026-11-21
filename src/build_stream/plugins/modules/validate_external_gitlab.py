#!/usr/bin/python
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

# pylint: disable=import-error,no-name-in-module
"""Ansible module: probe and validate an external GitLab (ER-BSM-003 FR-1, FR-2).

Checks the custom CA bundle, connectivity (3 attempts, 5s/15s/45s backoff),
the GitLab version (17.x-19.x), the personal access token scopes and the
token user's role on the target namespace. The token is never logged or returned.
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.external_gitlab import ca_cert
from ansible.module_utils.external_gitlab.gitlab_client import (
    MIN_NAMESPACE_ACCESS_LEVEL,
    REQUIRED_PAT_SCOPES,
    SUPPORTED_MAJOR_VERSIONS,
    GitLabApiError,
    GitLabClient,
    encode_namespace,
    parse_major_minor,
)
from ansible.module_utils.input_validation.messages import build_stream_messages as msg

DOCUMENTATION = r'''
---
module: validate_external_gitlab
short_description: Validate connectivity, version, token scopes and namespace role of an external GitLab
description:
  - Read-only checks against the external GitLab API using the supplied personal access token.
options:
  url:
    description: HTTPS URL of the external GitLab.
    type: str
    required: true
  token:
    description: Personal access token (api, write_repository).
    type: str
    required: true
    no_log: true
  namespace:
    description: Target group path.
    type: str
    required: true
  ca_cert_path:
    description: Optional PEM CA bundle for HTTPS calls.
    type: str
    default: ""
  check_ca_permissions:
    description: Require the CA file to be root-owned with mode 0644 or stricter.
    type: bool
    default: true
  ca_only:
    description: Validate only the CA bundle and skip all API calls.
    type: bool
    default: false
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Validate external GitLab
  validate_external_gitlab:
    url: https://gitlab.example.com
    token: "{{ gitlab_api_token }}"
    namespace: infra/omnia-builds
'''

RETURN = r'''
errors:
  description: Actionable validation errors.
  returned: always
  type: list
info:
  description: Non-secret facts (version, scopes, user, namespace_id, access_level, token_expires_at, ca_cert_path).
  returned: always
  type: dict
'''


def check_ca(path, check_permissions):
    """Return CA validation errors for a configured bundle."""
    detail = ca_cert.validate_pem_bundle(path)
    if detail:
        return [msg.ca_cert_error_msg(detail)]
    return ca_cert.check_permissions(path) if check_permissions else []


def check_version(client, info):
    """Verify the GitLab version is supported."""
    _, data = client.get("/version")
    version = str((data or {}).get("version", ""))
    info["version"] = version
    parsed = parse_major_minor(version)
    if parsed is None or parsed[0] not in SUPPORTED_MAJOR_VERSIONS:
        return [msg.unsupported_gitlab_version_msg(version or "unknown")]
    return []


def check_token(client, info):
    """Verify the token is active and carries the required scopes."""
    _, data = client.get("/personal_access_tokens/self")
    data = data or {}
    scopes = sorted(data.get("scopes", []))
    info["scopes"] = scopes
    info["token_expires_at"] = data.get("expires_at") or ""
    missing = [s for s in REQUIRED_PAT_SCOPES if s not in scopes]
    return [msg.missing_pat_scopes_msg(missing)] if missing else []


def check_namespace(client, namespace, info):
    """Verify the token user is Owner/Maintainer of the group."""
    _, user = client.get("/user")
    user = user or {}
    info["user"] = user.get("username", "")
    _, group = client.get(f"/groups/{encode_namespace(namespace)}", ok=(200, 404))
    if not group:
        return [f"Namespace '{namespace}' was not found or is not visible to the token user."]
    info["namespace_id"] = group.get("id")
    if user.get("is_admin"):
        info["access_level"] = MIN_NAMESPACE_ACCESS_LEVEL
        return []
    _, member = client.get(
        f"/groups/{group['id']}/members/all/{user.get('id')}", ok=(200, 404)
    )
    level = int((member or {}).get("access_level", 0))
    info["access_level"] = level
    return [] if level >= MIN_NAMESPACE_ACCESS_LEVEL else [
        msg.insufficient_namespace_role_msg(namespace)
    ]


def validate(client, namespace):
    """Run all API checks; returns (errors, info). Stops early on transport failure."""
    info, errors = {}, []
    try:
        errors += check_version(client, info)
        errors += check_token(client, info)
        errors += check_namespace(client, namespace, info)
    except GitLabApiError as exc:
        if exc.status in (401, 403):
            errors.append(
                f"GitLab rejected gitlab_api_token ({exc}). Verify the token is active "
                "and has the api and write_repository scopes."
            )
        else:
            errors.append(f"External GitLab is not reachable or returned an error: {exc}")
    return errors, info


def run_module():
    """Module entry point."""
    module = AnsibleModule(
        argument_spec=dict(
            url=dict(type="str", required=True),
            token=dict(type="str", required=True, no_log=True),
            namespace=dict(type="str", required=True),
            ca_cert_path=dict(type="str", default=""),
            check_ca_permissions=dict(type="bool", default=True),
            ca_only=dict(type="bool", default=False),
        ),
        supports_check_mode=True,
    )
    params = module.params
    errors = []
    ca_path = params["ca_cert_path"] or None
    if ca_path:
        errors += check_ca(ca_path, params["check_ca_permissions"])
    info = {"ca_cert_path": ca_path or "system default"}
    if not errors and not params["ca_only"]:
        client = GitLabClient(params["url"], params["token"], ca_path)
        api_errors, api_info = validate(client, params["namespace"])
        errors += api_errors
        info.update(api_info)
    module.exit_json(changed=False, failed=bool(errors), errors=errors, info=info,
                     msg="; ".join(errors) if errors else "External GitLab validated")


def main():
    """Main entry point."""
    run_module()


if __name__ == "__main__":
    main()
