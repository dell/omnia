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

"""Unit tests for LDMS Kafka Bridge commands."""

import pytest

from library.vars.ldms_vars import LDMS_CMD_TEMPLATES


@pytest.mark.parametrize(
    "command_name",
    [
        "rest_create_consumer",
        "rest_subscribe_topic",
        "rest_consume_records",
        "rest_delete_consumer",
    ],
)
def test_ldms_rest_commands_use_tls_bridge(command_name):
    """Use TLS for the REST listener configured by the KafkaBridge CR."""
    command = LDMS_CMD_TEMPLATES[command_name]

    assert "https://{bridge_ip}:{port}/" in command
    assert "http://{bridge_ip}:{port}/" not in command
    assert "curl -kfsS --max-time 15" in command
