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

"""Unit tests for GenerateInputFilesCommand."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from core.artifacts.value_objects import SafePath
from core.jobs.value_objects import CorrelationId, JobId
from orchestrator.catalog.commands.generate_input_files import GenerateInputFilesCommand


VALID_JOB_ID = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
VALID_CORRELATION_ID = "018f3c4b-2d9e-7d1a-8a2b-111111111111"


class TestGenerateInputFilesCommand:
    """Tests for GenerateInputFilesCommand value object."""

    def test_valid_command_without_adapter_policy(self) -> None:
        cmd = GenerateInputFilesCommand(
            job_id=JobId(VALID_JOB_ID),
            correlation_id=CorrelationId(VALID_CORRELATION_ID),
            adapter_policy_path=None,
        )
        assert cmd.job_id.value == VALID_JOB_ID
        assert cmd.correlation_id.value == VALID_CORRELATION_ID
        assert cmd.adapter_policy_path is None

    def test_valid_command_with_adapter_policy(self) -> None:
        policy_path = SafePath.from_string("/opt/omnia/policy.json")
        cmd = GenerateInputFilesCommand(
            job_id=JobId(VALID_JOB_ID),
            correlation_id=CorrelationId(VALID_CORRELATION_ID),
            adapter_policy_path=policy_path,
        )
        assert cmd.job_id.value == VALID_JOB_ID
        assert cmd.correlation_id.value == VALID_CORRELATION_ID
        assert cmd.adapter_policy_path == policy_path
        assert str(cmd.adapter_policy_path.value) == "/opt/omnia/policy.json"

    def test_immutable(self) -> None:
        cmd = GenerateInputFilesCommand(
            job_id=JobId(VALID_JOB_ID),
            correlation_id=CorrelationId(VALID_CORRELATION_ID),
            adapter_policy_path=None,
        )
        with pytest.raises(FrozenInstanceError):
            cmd.adapter_policy_path = SafePath.from_string("/other/path")  # type: ignore[misc]

    def test_equality_based_on_values(self) -> None:
        policy_path = SafePath.from_string("/opt/omnia/policy.json")
        
        cmd1 = GenerateInputFilesCommand(
            job_id=JobId(VALID_JOB_ID),
            correlation_id=CorrelationId(VALID_CORRELATION_ID),
            adapter_policy_path=policy_path,
        )
        
        cmd2 = GenerateInputFilesCommand(
            job_id=JobId(VALID_JOB_ID),
            correlation_id=CorrelationId(VALID_CORRELATION_ID),
            adapter_policy_path=policy_path,
        )
        
        assert cmd1 == cmd2
        assert hash(cmd1) == hash(cmd2)

    def test_inequality_with_different_values(self) -> None:
        policy_path1 = SafePath.from_string("/opt/omnia/policy1.json")
        policy_path2 = SafePath.from_string("/opt/omnia/policy2.json")
        
        cmd1 = GenerateInputFilesCommand(
            job_id=JobId(VALID_JOB_ID),
            correlation_id=CorrelationId(VALID_CORRELATION_ID),
            adapter_policy_path=policy_path1,
        )
        
        cmd2 = GenerateInputFilesCommand(
            job_id=JobId(VALID_JOB_ID),
            correlation_id=CorrelationId(VALID_CORRELATION_ID),
            adapter_policy_path=policy_path2,
        )
        
        assert cmd1 != cmd2
        assert hash(cmd1) != hash(cmd2)

    def test_string_representation(self) -> None:
        policy_path = SafePath.from_string("/opt/omnia/policy.json")
        cmd = GenerateInputFilesCommand(
            job_id=JobId(VALID_JOB_ID),
            correlation_id=CorrelationId(VALID_CORRELATION_ID),
            adapter_policy_path=policy_path,
        )
        
        str_repr = str(cmd)
        assert VALID_JOB_ID in str_repr
        assert VALID_CORRELATION_ID in str_repr
        assert "/opt/omnia/policy.json" in str_repr
