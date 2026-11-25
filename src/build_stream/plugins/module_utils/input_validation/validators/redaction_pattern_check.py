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

"""Pattern-safety check for operator redaction patterns (ER-BSM-003 FR-3.3, HLD 5.3.5).

Mirrors ``core/logs/redaction_policy.check_pattern_safety`` in the BuildStream
application. Both implementations run the same shared vectors
(``test/build_stream/nft/unit/redaction_policy/pattern_safety_vectors.yml``).
Reason codes are part of that contract and must not change.
"""

import re
from typing import Any, List, Optional, Set

RESERVED_RULE_IDS = frozenset({
    "private-key", "key-value", "gitlab-token", "jwt", "bearer", "url-credentials",
    "ipv4", "ipv6", "email",
})

MAX_PATTERN_LENGTH = 256


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


_REPEAT_OPS = frozenset({
    sre_constants.MAX_REPEAT,
    sre_constants.MIN_REPEAT,
    getattr(sre_constants, "POSSESSIVE_REPEAT", None),
})
_ATOMIC_GROUP = getattr(sre_constants, "ATOMIC_GROUP", None)


def check_pattern_safety(pattern: str, allow_nested: bool = False) -> Optional[str]:
    """Return the reason a pattern must not be used (checked in order), or None if safe."""
    if not isinstance(pattern, str) or not pattern.strip():
        return "empty"
    if len(pattern) > MAX_PATTERN_LENGTH:
        return "too-long"
    try:
        re.compile(pattern)
        tree = sre_parse.parse(pattern)
    except (re.error, OverflowError, RecursionError, ValueError):
        return "does-not-compile"
    return _tree_reason(tree, allow_nested)


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


def _has_repeat(sequence: Any) -> bool:
    """Return True when any node in the sequence is a quantifier."""
    return any(
        op in _REPEAT_OPS or any(_has_repeat(sub) for sub in _sub_sequences(op, args))
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
            if args[1] > 1 and _has_repeat(args[2]):
                flags.add("nested-quantifier")
        for sub in _sub_sequences(op, args):
            flags |= _tree_flags(sub)
    return flags


def _tree_reason(tree: Any, allow_nested: bool) -> Optional[str]:
    """Return the first unsafe feature of a parsed pattern, in check order."""
    flags = _tree_flags(tree)
    if "group-reference" in flags:
        return "group-reference"
    if "unbounded-quantifier" in flags:
        return "unbounded-quantifier"
    if "nested-quantifier" in flags and not allow_nested:
        return "nested-quantifier"
    return None
