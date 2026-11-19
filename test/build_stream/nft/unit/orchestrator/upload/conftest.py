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

"""Isolate upload use case tests from the real Omnia data directories."""

import pytest

from orchestrator.upload.use_cases import upload_files as upload_module


@pytest.fixture(autouse=True)
def isolated_upload_destinations(tmp_path, monkeypatch):
    """Redirect every destination UploadFilesUseCase writes to into ``tmp_path``.

    The use case resolves its destinations (domain input dirs, catalog dir,
    restart state, system omnia.env) from module-level constants derived from
    ``OMNIA_DATA_PATH``. Without this fixture a test run on an OIM overwrites
    the operator's real input files, e.g. ``network_spec.yml`` and
    ``pxe_mapping_file.csv``, under ``/opt/omnia/<domain>/input/<project>/``.
    """
    root = tmp_path / "omnia"
    domain_dirs = {name: str(root / name / "input") for name in upload_module.DOMAIN_INPUT_DIRS}
    monkeypatch.setattr(upload_module, "DOMAIN_INPUT_DIRS", domain_dirs)
    monkeypatch.setattr(
        upload_module, "DEFAULT_PLAYBOOK_INPUT_DIR", str(root / "input" / "project") + "/"
    )
    monkeypatch.setattr(upload_module, "CATALOG_DIR", str(root / "catalog"))
    monkeypatch.setattr(upload_module, "RESTART_STATE_DIR", str(root / "restart_state"))
    monkeypatch.setattr(
        upload_module, "OMNIA_ENV_SYSTEM_PATH", str(root / "etc" / "omnia.env")
    )
    return root
