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

# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-LOGGING-001.2, CG-SECRETS-001.7, CG-INPUT-001.9, CG-LOGGING-001.1
# ****

"""Redaction policy loader (ER-BSM-003 FR-3.3, HLD 5.3.5).

The baseline file ships next to this module and holds the rules that were
hard-coded before. The optional ``redaction`` section of
``build_stream_config.yml`` adds key names and Tier 1 patterns. An invalid
baseline raises :class:`RedactionPolicyError` so the caller fails closed; an
invalid operator section is ignored and reported in ``operator_errors``.

Error messages name rule ids, indexes and reason codes only. They never carry
pattern text, matched values or secrets.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional, Set, Tuple

import yaml

from core.logs.redaction_patterns import (
    PRIVATE_KEY_RULE,
    REDACTED,
    RedactionRule,
    build_key_value_rule,
)

# The safety check parses patterns with the engine's own parser, so it sees exactly
# what the engine compiles (verbose-mode comments, escapes and classes included).
# The constants module is chosen at import time, so pylint cannot resolve its members.
# pylint: disable=no-member
try:
    from re import _constants as sre_constants  # pylint: disable=protected-access
    from re import _parser as sre_parse  # pylint: disable=protected-access
except ImportError:  # pragma: no cover - Python 3.10 and earlier
    import sre_constants  # pylint: disable=deprecated-module
    import sre_parse  # pylint: disable=deprecated-module

BASELINE_POLICY_PATH = Path(__file__).with_name("redaction_baseline.yml")

SCHEMA_VERSION = 1
MAX_OPERATOR_ITEMS = 50
MAX_PATTERN_LENGTH = 256
MAX_BACKTRACK_PATHS = 4096
MAX_DESCRIPTION_LENGTH = 200
BUILT_IN_RULE_IDS = frozenset({"private-key", "key-value"})

_KEY_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,39}")
_PATTERN_ID_RE = re.compile(r"[a-z][a-z0-9-]{1,40}")
_GROUP_REFERENCE_RE = re.compile(r"\\([1-9])(?!\d)")
_BASELINE_KEYS = frozenset({"schema_version", "secret_key_names", "secret_patterns",
                            "identifier_patterns"})
_BASELINE_ENTRY_KEYS = frozenset({"id", "description", "pattern", "replacement"})
_OPERATOR_ENTRY_KEYS = frozenset({"id", "description", "pattern"})
_OPERATOR_SECTION_KEYS = frozenset({"additional_secret_key_names", "additional_secret_patterns"})

_REPEAT_OPS = frozenset({
    sre_constants.MAX_REPEAT,
    sre_constants.MIN_REPEAT,
    getattr(sre_constants, "POSSESSIVE_REPEAT", None),
})
_ATOMIC_GROUP = getattr(sre_constants, "ATOMIC_GROUP", None)
_BRANCH_OPS = frozenset({sre_constants.BRANCH, sre_constants.GROUPREF_EXISTS})


class RedactionPolicyError(Exception):
    """The baseline redaction policy is missing or invalid; no service may start."""


@dataclass(frozen=True)
class RedactionPolicy:
    """Rule lists for ``RedactionService`` plus operator-section problems."""

    secret_rules: List[RedactionRule]
    identifier_rules: List[RedactionRule]
    operator_errors: List[str]


@dataclass(frozen=True)
class _Baseline:
    """Parsed baseline file before operator additions are merged."""

    key_names: List[str]
    secret_rules: List[RedactionRule]
    identifier_rules: List[RedactionRule]
    rule_ids: Set[str]


def check_pattern_safety(pattern: str, allow_nested: bool = False) -> Optional[str]:
    """Return the reason a pattern must not be used (checked in order), or None if safe."""
    # allow_nested (baseline rules only) skips nested-quantifier, quantified-alternation
    # and too-complex.
    if not isinstance(pattern, str) or not pattern.strip():
        return "empty"
    if len(pattern) > MAX_PATTERN_LENGTH:
        return "too-long"
    try:
        re.compile(pattern)
        tree = sre_parse.parse(pattern)
    except (re.error, OverflowError, RecursionError, ValueError):
        return "does-not-compile"
    return _tree_reason(tree, allow_nested) or _match_reason(tree, pattern)


def _match_reason(tree: Any, pattern: str) -> Optional[str]:
    """Return matches-empty or matches-marker when the pattern would corrupt log lines."""
    # A zero-width match would insert the marker at every position of every line.
    if tree.getwidth()[0] == 0:
        return "matches-empty"
    # A rule that matches the marker would rewrite already-redacted text.
    if re.search(pattern, REDACTED):
        return "matches-marker"
    return None


def _sub_sequences(op: Any, args: Any) -> List[Any]:
    """Return the nested sequences of one parse-tree node (none for leaves)."""
    if op in _REPEAT_OPS:
        return [args[2]]
    if op in (sre_constants.SUBPATTERN, sre_constants.ASSERT, sre_constants.ASSERT_NOT):
        return [args[-1]]
    if op is sre_constants.BRANCH:
        return list(args[1])
    if op is sre_constants.GROUPREF_EXISTS:
        return [branch for branch in args[1:] if branch is not None]
    if op is _ATOMIC_GROUP:
        return [args]
    return []


def _has_op(sequence: Any, ops: Any) -> bool:
    """Return True when any node in the sequence, at any depth, is one of *ops*."""
    return any(
        op in ops or any(_has_op(sub, ops) for sub in _sub_sequences(op, args))
        for op, args in sequence
    )


def _tree_flags(sequence: Any) -> Set[str]:
    """Collect the unsafe features present anywhere in a parse-tree sequence."""
    flags: Set[str] = set()
    for op, args in sequence:
        if op in (sre_constants.GROUPREF, sre_constants.GROUPREF_EXISTS):
            flags.add("group-reference")
        if op in _REPEAT_OPS:
            if args[1] == sre_constants.MAXREPEAT:
                flags.add("unbounded-quantifier")
            if args[1] > 1 and _has_op(args[2], _REPEAT_OPS):
                flags.add("nested-quantifier")
            # Overlapping branches under a repeat backtrack exponentially: (?:a|aa){1,40}b.
            if args[1] > 1 and _has_op(args[2], _BRANCH_OPS):
                flags.add("quantified-alternation")
        for sub in _sub_sequences(op, args):
            flags |= _tree_flags(sub)
    return flags


def _backtrack_paths(sequence: Any) -> int:
    """Bound the match paths per start position: quantifier ranges multiply, branches add."""
    # Caps adjacent overlapping quantifiers such as \d{1,200}\d{1,200}x (~1 s per 8 KiB line).
    paths = 1
    for op, args in sequence:
        subs = [_backtrack_paths(sub) for sub in _sub_sequences(op, args)]
        if op in _REPEAT_OPS:
            paths *= (args[1] - args[0] + 1) * subs[0]
        elif op in _BRANCH_OPS:
            paths *= sum(subs)
        elif subs:
            paths *= subs[0]
    return paths


def _tree_reason(tree: Any, allow_nested: bool) -> Optional[str]:
    """Return the first unsafe feature of a parsed pattern, in check order."""
    flags = _tree_flags(tree)
    checked = ["group-reference", "unbounded-quantifier"]
    if not allow_nested:
        checked += ["nested-quantifier", "quantified-alternation"]
    reason = next((name for name in checked if name in flags), None)
    if reason is None and not allow_nested and _backtrack_paths(tree) > MAX_BACKTRACK_PATHS:
        reason = "too-complex"
    return reason


def _read_yaml(path: Path) -> Any:
    """Parse a YAML file with the safe loader."""
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _read_baseline(path: Path) -> _Baseline:
    """Load and validate the baseline file; any problem raises RedactionPolicyError."""
    try:
        data = _read_yaml(path)
    except OSError as exc:
        raise RedactionPolicyError("redaction baseline file is missing or unreadable") from exc
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        raise RedactionPolicyError("redaction baseline file is not valid YAML") from exc
    if not isinstance(data, dict) or set(data) != _BASELINE_KEYS:
        raise RedactionPolicyError("redaction baseline has missing or unexpected keys")
    version = data["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != SCHEMA_VERSION:
        raise RedactionPolicyError("redaction baseline schema_version is not supported")
    key_names = data["secret_key_names"]
    if not isinstance(key_names, list) or not all(
            isinstance(name, str) and _KEY_NAME_RE.fullmatch(name) for name in key_names):
        raise RedactionPolicyError("redaction baseline secret_key_names is invalid")
    rule_ids: Set[str] = set(BUILT_IN_RULE_IDS)
    secret_entries = _baseline_entries("secret_patterns", data["secret_patterns"], rule_ids)
    identifier_entries = _baseline_entries(
        "identifier_patterns", data["identifier_patterns"], rule_ids)
    return _Baseline(
        key_names=list(key_names),
        secret_rules=[rule for _, rule in secret_entries],
        identifier_rules=[rule for _, rule in identifier_entries],
        rule_ids=rule_ids,
    )


def _baseline_entries(
    section: str, entries: Any, rule_ids: Set[str]
) -> List[Tuple[str, RedactionRule]]:
    """Validate one baseline pattern list and compile its rules in file order."""
    if not isinstance(entries, list):
        raise RedactionPolicyError(f"redaction baseline {section} must be a list")
    rules: List[Tuple[str, RedactionRule]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != _BASELINE_ENTRY_KEYS:
            raise RedactionPolicyError(f"redaction baseline {section}[{index}] is invalid")
        rule_id = entry["id"]
        if (not isinstance(rule_id, str) or not _PATTERN_ID_RE.fullmatch(rule_id)
                or rule_id in rule_ids or not isinstance(entry["description"], str)):
            raise RedactionPolicyError(f"redaction baseline {section}[{index}] has a bad id")
        reason = check_pattern_safety(entry["pattern"], allow_nested=True)
        if reason:
            raise RedactionPolicyError(
                f"redaction baseline pattern '{rule_id}' is unsafe: {reason}")
        compiled = re.compile(entry["pattern"])
        _check_replacement(rule_id, entry["replacement"], compiled.groups)
        rule_ids.add(rule_id)
        rules.append((rule_id, (compiled, entry["replacement"])))
    return rules


def _check_replacement(rule_id: str, replacement: Any, group_count: int) -> None:
    """Allow only plain text and one group reference per existing group."""
    if not isinstance(replacement, str):
        raise RedactionPolicyError(f"redaction baseline pattern '{rule_id}' has no replacement")
    references = [int(match.group(1)) for match in _GROUP_REFERENCE_RE.finditer(replacement)]
    leftover = _GROUP_REFERENCE_RE.sub("", replacement)
    if "\\" in leftover or any(ref > group_count for ref in references):
        raise RedactionPolicyError(
            f"redaction baseline pattern '{rule_id}' has an invalid replacement")


def _load_operator_section(
    config_path: Optional[Path], reserved_ids: Set[str]
) -> Tuple[List[str], List[RedactionRule], List[str]]:
    """Read the operator ``redaction`` section; problems are reported, never raised."""
    section, errors = _read_operator_section(config_path)
    if section is None:
        return [], [], errors
    if not isinstance(section, dict) or not set(section) <= _OPERATOR_SECTION_KEYS:
        return [], [], ["redaction section is invalid; additions ignored"]
    key_names = _operator_key_names(section.get("additional_secret_key_names"), errors)
    rules = _operator_patterns(section.get("additional_secret_patterns"), reserved_ids, errors)
    return key_names, rules, errors


def _read_operator_section(config_path: Optional[Path]) -> Tuple[Any, List[str]]:
    """Return (raw redaction section or None, errors) from the operator config file."""
    if config_path is None:
        return None, []
    try:
        data = _read_yaml(config_path)
    except FileNotFoundError:
        data = None
    except OSError:
        return None, ["build_stream_config.yml is unreadable; redaction additions ignored"]
    except (yaml.YAMLError, UnicodeDecodeError):
        return None, ["build_stream_config.yml is not valid YAML; redaction additions ignored"]
    if data is None:
        return None, []
    if not isinstance(data, dict):
        return None, ["build_stream_config.yml is not a mapping; redaction additions ignored"]
    return data.get("redaction"), []


def _operator_key_names(value: Any, errors: List[str]) -> List[str]:
    """Validate operator key names; duplicates are dropped silently."""
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_OPERATOR_ITEMS:
        errors.append("additional_secret_key_names must be a list of at most 50 names; ignored")
        return []
    names: List[str] = []
    seen: Set[str] = set()
    for index, name in enumerate(value):
        if not isinstance(name, str) or not _KEY_NAME_RE.fullmatch(name):
            errors.append(f"additional_secret_key_names[{index}] is not a valid key name; skipped")
            continue
        if name.lower() not in seen:
            seen.add(name.lower())
            names.append(name)
    return names


def _operator_patterns(
    value: Any, reserved_ids: Set[str], errors: List[str]
) -> List[RedactionRule]:
    """Validate operator patterns; invalid entries are skipped and reported by id."""
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_OPERATOR_ITEMS:
        errors.append("additional_secret_patterns must be a list of at most 50 entries; ignored")
        return []
    rules: List[RedactionRule] = []
    used_ids: Set[str] = set(reserved_ids)
    for index, entry in enumerate(value):
        label = f"additional_secret_patterns[{index}]"
        if (not isinstance(entry, dict) or not set(entry) <= _OPERATOR_ENTRY_KEYS
                or "id" not in entry or "pattern" not in entry):
            errors.append(f"{label} is not valid; skipped")
            continue
        rule_id = entry["id"]
        if not isinstance(rule_id, str) or not _PATTERN_ID_RE.fullmatch(rule_id):
            errors.append(f"{label} has an invalid id; skipped")
            continue
        if rule_id in used_ids:
            errors.append(f"{label} ({rule_id}) reuses a reserved or duplicate id; skipped")
            continue
        description = entry.get("description", "")
        if not isinstance(description, str) or len(description) > MAX_DESCRIPTION_LENGTH:
            errors.append(f"{label} ({rule_id}) has an invalid description; skipped")
            continue
        reason = check_pattern_safety(entry["pattern"])
        if reason:
            errors.append(f"{label} ({rule_id}) rejected: {reason}; skipped")
            continue
        used_ids.add(rule_id)
        rules.append((re.compile(entry["pattern"]), REDACTED))
    return rules


def _merge_key_names(baseline_names: List[str], operator_names: List[str]) -> List[str]:
    """Combine key names in order, dropping case-insensitive duplicates."""
    merged: List[str] = []
    seen: Set[str] = set()
    for name in baseline_names + operator_names:
        if name.lower() not in seen:
            seen.add(name.lower())
            merged.append(name)
    return merged


def load_policy(
    config_path: Optional[Path], baseline_path: Path = BASELINE_POLICY_PATH
) -> RedactionPolicy:
    """Build the rule lists from the baseline and the operator section.

    Raises:
        RedactionPolicyError: The baseline file is missing, unreadable or invalid.
    """
    baseline = _read_baseline(baseline_path)
    key_names, operator_rules, errors = _load_operator_section(config_path, baseline.rule_ids)
    return RedactionPolicy(
        secret_rules=[
            PRIVATE_KEY_RULE,
            *baseline.secret_rules,
            build_key_value_rule(_merge_key_names(baseline.key_names, key_names)),
            *operator_rules,
        ],
        identifier_rules=list(baseline.identifier_rules),
        operator_errors=errors,
    )


def load_baseline(path: Path = BASELINE_POLICY_PATH) -> RedactionPolicy:
    """Build the rule lists from the baseline file alone.

    Raises:
        RedactionPolicyError: The baseline file is missing, unreadable or invalid.
    """
    return load_policy(None, path)


@lru_cache(maxsize=1)
def baseline_policy() -> RedactionPolicy:
    """Return the shipped baseline policy, loaded once per process."""
    return load_baseline()
