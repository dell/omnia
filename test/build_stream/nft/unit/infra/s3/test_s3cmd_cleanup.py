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

"""Unit tests for the S3CmdCleanupService implementation."""

import subprocess
from unittest.mock import patch

import pytest

from core.cleanup.exceptions import CleanupS3FailedError
from infra.s3.s3cmd_cleanup import S3CmdCleanupService


pytestmark = pytest.mark.unit


_VALID_PATH = (
    "s3://boot-images/slurm_node_x86_64/"
    "rhel-slurm_node_x86_64_018f3c4b-image-build1/"
)


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Build a minimal CompletedProcess-like stub."""
    return subprocess.CompletedProcess(
        args=["s3cmd"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class TestS3CmdCleanupServiceSuccess:
    """Happy-path tests for s3cmd subprocess invocation."""

    def test_delete_returns_count_from_delete_lines(self):
        service = S3CmdCleanupService()
        stdout = (
            "delete: 's3://boot-images/x/img1'\n"
            "delete: 's3://boot-images/x/img2'\n"
            "delete: 's3://boot-images/x/img3'\n"
        )
        with patch("subprocess.run", return_value=_completed(stdout=stdout)) as run:
            result = service.delete_image_path(_VALID_PATH)

        assert result.success is True
        assert result.objects_deleted == 3
        assert result.exit_code == 0

        cmd = run.call_args.args[0]
        assert cmd[:4] == ["s3cmd", "del", "--recursive", "--force"]
        assert cmd[-1] == _VALID_PATH

    def test_no_output_returns_zero(self):
        service = S3CmdCleanupService()
        with patch("subprocess.run", return_value=_completed(stdout="")):
            result = service.delete_image_path(_VALID_PATH)
        assert result.success is True
        assert result.objects_deleted == 0

    def test_missing_path_treated_as_noop(self):
        service = S3CmdCleanupService()
        completed = _completed(
            returncode=64, stderr="ERROR: NoSuchKey, key does not exist"
        )
        with patch("subprocess.run", return_value=completed):
            result = service.delete_image_path(_VALID_PATH)
        assert result.success is True
        assert result.objects_deleted == 0
        # Exit code is normalised to 0 for the missing-path edge case
        assert result.exit_code == 0


class TestS3CmdCleanupServiceFailure:
    """Failure paths must raise CleanupS3FailedError."""

    def test_non_zero_exit_raises(self):
        service = S3CmdCleanupService()
        completed = _completed(returncode=2, stderr="boom")
        with patch("subprocess.run", return_value=completed):
            with pytest.raises(CleanupS3FailedError):
                service.delete_image_path(_VALID_PATH)

    def test_timeout_raises(self):
        service = S3CmdCleanupService()
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="s3cmd", timeout=1),
        ):
            with pytest.raises(CleanupS3FailedError):
                service.delete_image_path(_VALID_PATH)


class TestS3CmdCleanupServiceValidation:
    """Path validation guards."""

    def test_empty_path_rejected(self):
        service = S3CmdCleanupService()
        with pytest.raises(CleanupS3FailedError):
            service.delete_image_path("")

    def test_wrong_bucket_rejected(self):
        service = S3CmdCleanupService(bucket_uri="s3://boot-images")
        with pytest.raises(CleanupS3FailedError):
            service.delete_image_path("s3://other-bucket/role/")

    def test_command_injection_rejected(self):
        service = S3CmdCleanupService()
        with pytest.raises(CleanupS3FailedError):
            service.delete_image_path("s3://boot-images/role; rm -rf /")
