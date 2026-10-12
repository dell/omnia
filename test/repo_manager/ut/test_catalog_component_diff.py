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

"""Granular catalog component patches preserve exact ordered round trips."""

import copy
import itertools
import json
import sys
import unittest

from source_loader import MODULE_UTILS_PATH

sys.path.insert(0, str(MODULE_UTILS_PATH))
from catalog.differ import CatalogFormatError, apply_patch, diff_catalogs  # pylint: disable=wrong-import-position
from catalog.report_renderer import summarize  # pylint: disable=wrong-import-position


def catalog_with(items, section="groups"):
    """Build a minimal engine fixture with a group or functional-layer owner."""
    entry = {"name": "example", "components": list(items)}
    return {"catalog": {
        "packages": {},
        "groups": {"example": entry} if section == "groups" else {},
        "functionallayer": [entry] if section != "groups" else [],
    }}


class ComponentDiffTests(unittest.TestCase):
    """Exercise generation, application, legacy compatibility and reporting."""

    def assert_round_trip(self, old, new):
        """Verify both directions, JSON serialization and input immutability."""
        snapshots = copy.deepcopy((old, new))
        result = diff_catalogs(old, new)
        self.assertEqual(result, diff_catalogs(old, new))
        forward = json.loads(json.dumps(result["forward_diff"]))
        reverse = json.loads(json.dumps(result["reverse_diff"]))
        self.assertEqual(apply_patch(old, forward), new)
        self.assertEqual(apply_patch(new, reverse), old)
        self.assertEqual((old, new), snapshots)
        return forward

    def test_htop_append_contains_only_added_component(self):
        """The reported htop case must not repeat unaffected group members."""
        old = catalog_with(["gcc", "vim", "perf"])
        new = catalog_with(["gcc", "vim", "perf", "htop"])
        new["catalog"]["packages"]["htop"] = {"name": "htop", "packagetype": "rpm"}
        ops = self.assert_round_trip(old, new)
        self.assertEqual(len(ops), 2)
        self.assertEqual(ops[0]["op"], "add")
        self.assertEqual(ops[1], {
            "op": "insert_component",
            "path": ["catalog", "groups", "example", "components"],
            "index": 3, "value": "htop",
        })

    def test_ordered_edits_and_duplicates_round_trip(self):
        """Beginning/middle/end edits, reorders and duplicate values retain order."""
        cases = [
            ([], ["a"]), (["a"], []),
            (["b", "d"], ["a", "b", "c", "d", "e"]),
            (["a", "b", "c", "d", "e"], ["b", "d"]),
            (["a", "b", "c"], ["c", "a", "b"]),
            (["a", "a", "b"], ["a", "b", "a"]),
            (["a", "b"], ["x", "y"]),
        ]
        for section, (old_items, new_items) in itertools.product(
                ("groups", "functionallayer"), cases):
            with self.subTest(section=section, old=old_items, new=new_items):
                ops = self.assert_round_trip(catalog_with(old_items, section),
                                             catalog_with(new_items, section))
                self.assertTrue(all(op["op"] in ("insert_component", "remove_component")
                                    for op in ops))

    def test_exhaustive_small_sequences(self):
        """All pairs of short sequences, including repeats, reconstruct exactly."""
        sequences = [items for size in range(4)
                     for items in itertools.product(("a", "b"), repeat=size)]
        for old_items, new_items in itertools.product(sequences, repeat=2):
            self.assert_round_trip(catalog_with(old_items), catalog_with(new_items))

    def test_large_list_small_edit_stays_compact(self):
        """Long lists must not trigger wholesale replacement or autojunk churn."""
        items = [f"package_{index}" for index in range(400)]
        new_items = items[:200] + ["htop"] + items[200:]
        self.assertEqual(len(self.assert_round_trip(catalog_with(items),
                                                    catalog_with(new_items))), 1)

    def test_no_change_is_empty(self):
        """Identical catalogs produce no patch operations."""
        old = catalog_with(["a", "b"])
        self.assertEqual(self.assert_round_trip(old, copy.deepcopy(old)), [])

    def test_metadata_changes_use_legacy_replacement(self):
        """Changing metadata and components together retains complete object data."""
        old, new = catalog_with(["a"]), catalog_with(["b"])
        new["catalog"]["groups"]["example"]["description"] = "New description"
        ops = self.assert_round_trip(old, new)
        self.assertEqual([op["op"] for op in ops], ["set"])

    def test_legacy_set_and_whole_owner_add_remove(self):
        """Old patches still apply; owner creation/deletion remains whole-object."""
        old, new = catalog_with(["a"]), catalog_with(["b"])
        legacy = [{"op": "set", "path": ["catalog", "groups", "example"],
                   "value": new["catalog"]["groups"]["example"]}]
        self.assertEqual(apply_patch(old, legacy), new)
        empty = catalog_with([])
        empty["catalog"]["groups"] = {}
        self.assertEqual(self.assert_round_trip(empty, old)[0]["op"], "add")
        self.assertEqual(self.assert_round_trip(old, empty)[0]["op"], "remove")

    def test_invalid_component_operations_fail_without_mutation(self):
        """Invalid paths, values, bounds and stale removals cannot corrupt input."""
        old = catalog_with(["a", "b"])
        original = copy.deepcopy(old)
        valid = {"op": "remove_component",
                 "path": ["catalog", "groups", "example", "components"],
                 "index": 0, "value": "a"}
        changes = [
            {"index": -1}, {"index": 2}, {"index": True}, {"index": "0"},
            {"value": "b"}, {"value": None},
            {"path": ["catalog", "packages", "example", "components"]},
            {"path": ["catalog", "groups", "missing", "components"]},
            {"path": ["catalog", "groups", "example"]},
            {"op": "insert_component", "index": 3}, {"op": "unknown"},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(CatalogFormatError):
                apply_patch(old, [{**valid, **change}])
            self.assertEqual(old, original)

    def test_multiple_edits_count_as_one_changed_owner(self):
        """Reports must not count component additions as new groups/layers."""
        for section in ("groups", "functionallayer"):
            old, new = catalog_with(["a", "b"], section), catalog_with(["x", "y"], section)
            ops = self.assert_round_trip(old, new)
            report = summarize(old["catalog"], new["catalog"], ops)
            self.assertEqual(report[section]["added"], [])
            self.assertEqual(report[section]["removed"], [])
            self.assertEqual(len(report[section]["changed"]), 1)

    def test_late_failure_leaves_source_unchanged(self):
        """Failure after a valid operation still cannot mutate the caller's catalog."""
        old = catalog_with(["a"])
        snapshot = copy.deepcopy(old)
        insert = {"op": "insert_component",
                  "path": ["catalog", "groups", "example", "components"],
                  "index": 1, "value": "b"}
        with self.assertRaises(CatalogFormatError):
            apply_patch(old, [insert, {**insert, "op": "remove_component", "value": "c"}])
        self.assertEqual(old, snapshot)


if __name__ == "__main__":
    unittest.main()
