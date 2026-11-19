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

"""Build Stream creates no folder outside the domain folders of OMNIA_DATA_PATH."""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

DEPLOY_VARS = (
    Path(__file__).resolve().parents[5]
    / "src" / "build_stream" / "roles" / "deploy_bsm" / "vars" / "main.yml"
)
DOMAIN_FOLDERS = ("repo_manager", "image_build_manager", "orchestrator")


def _upload_dirs():
    return yaml.safe_load(DEPLOY_VARS.read_text(encoding="utf-8"))["build_stream_upload_dirs"]


def test_upload_dirs_are_catalog_or_domain_input_folders():
    """GIVEN the deploy role WHEN it creates upload folders THEN each is catalog or a domain's."""
    for entry in _upload_dirs():
        first = entry.split("/", 1)[0]
        assert entry == "catalog" or first in DOMAIN_FOLDERS, entry


def test_no_top_level_input_folder_is_created():
    """No upload folder is a top-level input/<project> folder next to the domains."""
    assert not [entry for entry in _upload_dirs() if entry.split("/", 1)[0] == "input"]


def test_every_domain_input_folder_is_still_created():
    """The three domain input folders the API writes to are still created and mounted."""
    entries = _upload_dirs()
    for domain in DOMAIN_FOLDERS:
        assert f"{domain}/input/{{{{ project_name }}}}" in entries
