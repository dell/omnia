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
"""Core L1 schema and L2 logic validation entry points for telemetry."""

from ansible.module_utils.input_validation.core.data_validation import logic, schema
from ansible.module_utils.input_validation.core.logical_validation import validate_input_logic

__all__ = ["schema", "logic", "validate_input_logic"]
