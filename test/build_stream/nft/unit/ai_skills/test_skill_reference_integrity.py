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

"""Structural regression tests for `src/build_stream/ai_skills/`.

These guard against exactly the class of defect a package rename or split
silently introduces: a Markdown instruction file that references another
skill's file by its old (or simply wrong) path, or a skill package that
does not conform to the sdd-skillsmith package-layout contract (directory
name matches the skill's declared `name`, a `skill.yaml` manifest and a
`README.md` are both present, and the frontmatter `description` reads like
an actionable, discoverable skill description).
"""

import re
import unittest
from pathlib import Path

import yaml


def _find_repo_root(start: Path) -> Path:
    """Walk upward from `start` until a directory containing
    `src/build_stream/ai_skills` is found."""
    for candidate in (start, *start.parents):
        if (candidate / "src" / "build_stream" / "ai_skills").is_dir():
            return candidate
    raise RuntimeError("Could not locate repository root from " + str(start))


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
AI_SKILLS_ROOT = REPO_ROOT / "src" / "build_stream" / "ai_skills"

# Matches a backtick-quoted, repo-relative path into ai_skills, e.g.
# `src/build_stream/ai_skills/catalog-editing/references/pre_edit_gate.md`
_ABS_PATH_RE = re.compile(r"`(src/build_stream/ai_skills/[A-Za-z0-9_\-./]+)`")

# YAML line-length ceiling enforced by the repository's ansible-lint
# "production" profile (yamllint's default `line-length` rule, max 160).
_YAML_MAX_LINE_LENGTH = 160

# A skill's description should open with an imperative verb and name a
# concrete trigger, not simply describe what it is in the abstract.
_USE_WHEN_RE = re.compile(r"\buse when\b", re.IGNORECASE)


def _iter_markdown_files():
    return sorted(AI_SKILLS_ROOT.rglob("*.md"))


def _iter_skill_package_dirs():
    """Every immediate subdirectory of ai_skills/ that is a canonical skill
    package (has a top-level SKILL.md) -- excludes `shared/`, whose files
    are explicitly-documented non-standalone instruction fragments with no
    SKILL.md of their own."""
    for entry in sorted(AI_SKILLS_ROOT.iterdir()):
        if entry.is_dir() and (entry / "SKILL.md").is_file():
            yield entry


class AbsoluteReferenceIntegrityTests(unittest.TestCase):
    """Every backtick-quoted `src/build_stream/ai_skills/...` reference in
    any skill instruction file must resolve to a real file."""

    def test_every_absolute_ai_skills_reference_resolves(self):
        missing = []
        for md_file in _iter_markdown_files():
            text = md_file.read_text(encoding="utf-8")
            for match in _ABS_PATH_RE.finditer(text):
                if match.group(1).endswith(".log"):
                    # Runtime audit-trail files (gitignored; see .gitignore)
                    # are created on first write, not checked in.
                    continue
                referenced = REPO_ROOT / match.group(1)
                if not referenced.is_file():
                    missing.append(
                        f"{md_file.relative_to(REPO_ROOT)} references "
                        f"'{match.group(1)}', which does not exist"
                    )
        self.assertEqual(
            missing, [],
            "Broken ai_skills path reference(s):\n" + "\n".join(sorted(set(missing))),
        )

    def test_no_reference_uses_a_pre_rename_underscore_directory(self):
        """Directories were renamed to kebab-case (`catalog_editing` ->
        `catalog-editing`, etc.); no instruction file should still name the
        old underscore form as a path segment."""
        retired_segments = (
            "ai_skills/catalog_editing/", "ai_skills/catalog_generation/",
            "ai_skills/diff_changelog/", "ai_skills/analysis/",
            "ai_skills/master_reference/",
        )
        offenders = []
        for md_file in _iter_markdown_files():
            text = md_file.read_text(encoding="utf-8")
            for segment in retired_segments:
                if segment in text:
                    offenders.append(f"{md_file.relative_to(REPO_ROOT)} still contains "
                                     f"'{segment}'")
        self.assertEqual(offenders, [], "\n".join(offenders))


class SkillPackageLayoutTests(unittest.TestCase):
    """Every canonical skill package conforms to the sdd-skillsmith layout
    contract: directory name == declared name, skill.yaml + README.md
    present, and a discoverable, action-oriented description."""

    def test_every_skill_directory_name_matches_its_declared_name(self):
        mismatches = []
        for skill_dir in _iter_skill_package_dirs():
            frontmatter = _read_frontmatter(skill_dir / "SKILL.md")
            declared_name = frontmatter.get("name")
            if declared_name != skill_dir.name:
                mismatches.append(
                    f"{skill_dir.name}/SKILL.md declares name '{declared_name}', "
                    f"which does not match its directory name"
                )
        self.assertEqual(mismatches, [], "\n".join(mismatches))

    def test_every_skill_package_has_manifest_and_readme(self):
        missing = []
        for skill_dir in _iter_skill_package_dirs():
            if not (skill_dir / "skill.yaml").is_file():
                missing.append(f"{skill_dir.name}/ is missing skill.yaml")
            if not (skill_dir / "README.md").is_file():
                missing.append(f"{skill_dir.name}/ is missing README.md")
        self.assertEqual(missing, [], "\n".join(missing))

    def test_every_skill_description_has_a_use_when_trigger(self):
        missing_trigger = []
        for skill_dir in _iter_skill_package_dirs():
            frontmatter = _read_frontmatter(skill_dir / "SKILL.md")
            description = frontmatter.get("description", "")
            if not _USE_WHEN_RE.search(description):
                missing_trigger.append(
                    f"{skill_dir.name}/SKILL.md's description has no 'Use when' trigger"
                )
        self.assertEqual(missing_trigger, [], "\n".join(missing_trigger))

    def test_skill_yaml_names_match_their_directory(self):
        mismatches = []
        for skill_dir in _iter_skill_package_dirs():
            manifest_path = skill_dir / "skill.yaml"
            if not manifest_path.is_file():
                continue  # reported by test_every_skill_package_has_manifest_and_readme
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("name") != skill_dir.name:
                mismatches.append(
                    f"{skill_dir.name}/skill.yaml declares name '{manifest.get('name')}'"
                )
        self.assertEqual(mismatches, [], "\n".join(mismatches))


class SkillYamlLintComplianceTests(unittest.TestCase):
    """Every skill.yaml stays within the repository's enforced YAML line
    length so the required Ansible Lint CI check stays green."""

    def test_no_skill_yaml_line_exceeds_the_configured_limit(self):
        offenders = []
        for manifest_path in sorted(AI_SKILLS_ROOT.glob("*/skill.yaml")):
            for lineno, line in enumerate(
                manifest_path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if len(line) > _YAML_MAX_LINE_LENGTH:
                    offenders.append(
                        f"{manifest_path.relative_to(REPO_ROOT)}:{lineno} is "
                        f"{len(line)} chars (max {_YAML_MAX_LINE_LENGTH})"
                    )
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_every_skill_yaml_is_valid_yaml_with_a_description(self):
        for manifest_path in sorted(AI_SKILLS_ROOT.glob("*/skill.yaml")):
            with self.subTest(manifest=str(manifest_path.relative_to(REPO_ROOT))):
                manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
                self.assertIsInstance(manifest, dict)
                self.assertTrue(manifest.get("description"))


def _read_frontmatter(skill_md_path: Path) -> dict:
    """Parse the `---`-delimited YAML frontmatter at the top of a SKILL.md."""
    text = skill_md_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


if __name__ == "__main__":
    unittest.main()
