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
"""Unit coverage for the persistent global image dictionary."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_UTILS = (
    REPO_ROOT / "src/image_build_manager/plugins/module_utils"
)
sys.path.insert(0, str(MODULE_UTILS))

from image_group_dictionary import (  # noqa: E402
    ImageGroupDictionaryRepository,
    make_entry_key,
)


def _entry(
    package_hash="hash-1",
    group="slurm_node_x86_64",
    architecture="x86_64",
    image_group_id="catalog-v1.0",
):
    return {
        "package_hash": package_hash,
        "functional_group": group,
        "architecture": architecture,
        "image_group_id": image_group_id,
        "catalog_identifier": image_group_id,
        "s3_paths": {
            "kernel": f"boot-images/{group}/vmlinuz",
            "initrd": f"boot-images/{group}/initramfs.img",
            "rootfs": f"boot-images/{group}/rootfs.squashfs",
        },
    }


def test_dictionary_missing_file_returns_empty_document(tmp_path):
    repository = ImageGroupDictionaryRepository(tmp_path / "dictionary.json")
    assert repository.load() == {
        "dictionary_version": 1,
        "entries": {},
        "last_updated": "",
    }


def test_dictionary_upsert_persists_complete_entry(tmp_path):
    path = tmp_path / "dictionary.json"
    repository = ImageGroupDictionaryRepository(
        path, clock=lambda: "2026-09-24T00:00:00Z"
    )
    assert repository.upsert([_entry()], catalog_schema_version=2) == 1
    document = json.loads(path.read_text(encoding="utf-8"))
    key = make_entry_key("hash-1", "slurm_node_x86_64", "x86_64")
    assert document["catalog_schema_version"] == 2
    assert document["entries"][key]["build_timestamp"].endswith("Z")


def test_dictionary_lookup_returns_hit_and_touches_last_used(tmp_path):
    timestamps = iter(
        ["2026-09-24T00:00:00Z", "2026-09-24T00:01:00Z"]
    )
    repository = ImageGroupDictionaryRepository(
        tmp_path / "dictionary.json", clock=lambda: next(timestamps)
    )
    repository.upsert([_entry()])
    hit = repository.lookup("hash-1", "slurm_node_x86_64", "x86_64")
    assert hit["last_used_at"] == "2026-09-24T00:01:00Z"
    assert hit["build_timestamp"] == "2026-09-24T00:00:00Z"


def test_dictionary_key_isolates_group_and_architecture(tmp_path):
    repository = ImageGroupDictionaryRepository(tmp_path / "dictionary.json")
    repository.upsert([_entry()])
    assert repository.lookup("hash-1", "slurm_control_x86_64", "x86_64") is None
    assert repository.lookup("hash-1", "slurm_node_x86_64", "aarch64") is None


@pytest.mark.parametrize(
    "field",
    ["package_hash", "functional_group", "architecture", "image_group_id"],
)
def test_dictionary_rejects_incomplete_entries(tmp_path, field):
    entry = _entry()
    entry[field] = ""
    repository = ImageGroupDictionaryRepository(tmp_path / "dictionary.json")
    with pytest.raises(ValueError, match=field):
        repository.upsert([entry])


def test_dictionary_rejects_incomplete_s3_paths(tmp_path):
    entry = _entry()
    entry["s3_paths"]["rootfs"] = ""
    repository = ImageGroupDictionaryRepository(tmp_path / "dictionary.json")
    with pytest.raises(ValueError, match="s3_paths.rootfs"):
        repository.upsert([entry])


def test_dictionary_update_retains_valid_backup(tmp_path):
    path = tmp_path / "dictionary.json"
    repository = ImageGroupDictionaryRepository(path)
    repository.upsert([_entry("hash-1")])
    first = path.read_text(encoding="utf-8")
    repository.upsert([_entry("hash-2")])
    assert path.with_suffix(".json.bak").read_text(encoding="utf-8") == first


def test_dictionary_recovers_from_valid_backup(tmp_path):
    path = tmp_path / "dictionary.json"
    repository = ImageGroupDictionaryRepository(path)
    repository.upsert([_entry("hash-1")])
    repository.upsert([_entry("hash-2")])
    path.write_text("{broken", encoding="utf-8")
    recovered = ImageGroupDictionaryRepository(path)
    document = recovered.load()
    assert recovered.recovered_from_backup is True
    assert len(document["entries"]) == 1


def test_dictionary_invalid_primary_and_backup_return_empty(tmp_path):
    path = tmp_path / "dictionary.json"
    path.write_text("{broken", encoding="utf-8")
    path.with_suffix(".json.bak").write_text("[]", encoding="utf-8")
    repository = ImageGroupDictionaryRepository(path)
    assert repository.load()["entries"] == {}
    assert "backup" in repository.load_error


def test_dictionary_migrates_legacy_hash_key_on_lookup(tmp_path):
    path = tmp_path / "dictionary.json"
    entry = _entry()
    path.write_text(
        json.dumps(
            {
                "dictionary_version": 1,
                "entries": {"hash-1": entry},
                "last_updated": "",
            }
        ),
        encoding="utf-8",
    )
    repository = ImageGroupDictionaryRepository(path)
    assert repository.lookup("hash-1", "slurm_node_x86_64", "x86_64")
    assert "hash-1" not in repository.load()["entries"]


def test_dictionary_prune_removes_only_requested_image_group(tmp_path):
    repository = ImageGroupDictionaryRepository(tmp_path / "dictionary.json")
    repository.upsert(
        [_entry("hash-1", image_group_id="catalog-v1.0"),
         _entry("hash-2", group="login_node_x86_64", image_group_id="catalog-v2.0")]
    )
    assert repository.prune("catalog-v1.0") == 1
    remaining = repository.load()["entries"].values()
    assert {entry["image_group_id"] for entry in remaining} == {"catalog-v2.0"}


def test_dictionary_empty_upsert_is_noop(tmp_path):
    path = tmp_path / "dictionary.json"
    repository = ImageGroupDictionaryRepository(path)
    assert repository.upsert([]) == 0
    assert not path.exists()
