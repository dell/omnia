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

"""
Validation error/warning message constants for the discovery domain.

All message strings are defined here as UPPER_SNAKE_CASE constants to
keep validator logic free of inline strings.
"""

# ── discovery_config.yml messages ────────────────────────────────────────────

OME_IP_REQUIRED_MSG = "discovery_config: ome_ip is required when enable_bmc_discovery is true."
OME_IP_LOOPBACK_MSG = (
    "discovery_config: ome_ip '{}' is a loopback address. "
    "Provide the actual OME appliance IP."
)
OME_IP_INVALID_MSG = "discovery_config: ome_ip '{}' is not a valid IPv4 address."

# ── Engine messages ──────────────────────────────────────────────────────────

VALIDATOR_EXCEPTION_MSG = "{}: Validator {} raised: {}"
