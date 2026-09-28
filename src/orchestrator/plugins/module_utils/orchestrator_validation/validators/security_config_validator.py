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
"""L2 validation for the Orchestrator security configuration."""

from __future__ import annotations

from logging import Logger
from typing import Any

from ..messages import orchestrator_messages as msg
from .network_spec_validator import record_error

SUPPORTED_LDAP_CONNECTION_TYPES = {"SSL", "TLS"}


def validate(
    config_data: Any,
    logger: Logger | None = None,
) -> list[str]:
    """Validate values that cannot be expressed case-insensitively in JSON Schema."""
    errors: list[str] = []
    if not isinstance(config_data, dict):
        return errors

    connection_type = config_data.get("ldap_connection_type")
    if (
        isinstance(connection_type, str)
        and connection_type.upper() not in SUPPORTED_LDAP_CONNECTION_TYPES
    ):
        record_error(
            errors,
            logger,
            msg.security_ldap_connection_type_msg(connection_type),
        )
    return errors
