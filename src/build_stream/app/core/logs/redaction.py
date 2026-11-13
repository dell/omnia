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
# Applicable rules used: CG-LOGGING-001.2, CG-OUTPUT-001.3
# ****

"""Response-time credential redaction (ER-BSM-003 FR-3.2)."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

from core.logs.redaction_patterns import (
    IDENTIFIER_RULES,
    PRIVATE_KEY_BEGIN,
    PRIVATE_KEY_END,
    REDACTED,
    REDACTION_SUPPRESSED_LINE,
    SECRET_RULES,
    RedactionRule,
)


class RedactionTier(str, Enum):
    """Which pattern tiers to apply."""

    SECRETS_ONLY = "secrets_only"
    FULL = "full"


@dataclass(frozen=True)
class RedactionResult:
    """Outcome of redacting a window of lines.

    Attributes:
        lines: Redacted lines.
        redacted_lines: Number of lines whose content changed.
        suppressed_lines: Number of lines withheld because redaction failed.
    """

    lines: List[str]
    redacted_lines: int
    suppressed_lines: int


class RedactionService:
    """Applies the tiered pattern registry to log lines.

    Multi-line PEM private keys are tracked across lines. When a window starts
    inside a key block (an END marker appears before any BEGIN marker), every
    line up to and including that END marker is redacted. Redaction fails
    closed: a line that cannot be processed is replaced, never passed through.
    """

    def __init__(
        self,
        secret_rules: Optional[Sequence[RedactionRule]] = None,
        identifier_rules: Optional[Sequence[RedactionRule]] = None,
    ) -> None:
        """Create the service, optionally with custom rule sets (used by tests)."""
        self._secret_rules = list(SECRET_RULES if secret_rules is None else secret_rules)
        self._identifier_rules = list(
            IDENTIFIER_RULES if identifier_rules is None else identifier_rules
        )

    def redact(self, text: str, tier: RedactionTier = RedactionTier.SECRETS_ONLY) -> str:
        """Redact a block of text and return it."""
        return "\n".join(self.redact_lines(text.split("\n"), tier).lines)

    def redact_lines(
        self,
        lines: Sequence[str],
        tier: RedactionTier = RedactionTier.SECRETS_ONLY,
    ) -> RedactionResult:
        """Redact each line and report how many lines changed or were withheld."""
        rules = self._secret_rules
        if tier == RedactionTier.FULL:
            rules = rules + self._identifier_rules
        leading_block_end = _leading_key_block_end(lines)
        in_key_block = False
        output: List[str] = []
        redacted = 0
        suppressed = 0
        for index, line in enumerate(lines):
            try:
                if index <= leading_block_end or in_key_block:
                    if in_key_block and PRIVATE_KEY_END.search(line):
                        in_key_block = False
                    new_line = REDACTED
                else:
                    begin = PRIVATE_KEY_BEGIN.search(line)
                    if begin and not PRIVATE_KEY_END.search(line, begin.end()):
                        in_key_block = True
                    new_line = _apply_rules(line, rules)
            except (re.error, RecursionError, TypeError):
                output.append(REDACTION_SUPPRESSED_LINE)
                suppressed += 1
                continue
            if new_line != line:
                redacted += 1
            output.append(new_line)
        return RedactionResult(lines=output, redacted_lines=redacted, suppressed_lines=suppressed)


def _apply_rules(line: str, rules: Sequence[RedactionRule]) -> str:
    """Apply every rule to a single line."""
    for pattern, replacement in rules:
        line = pattern.sub(replacement, line)
    return line


def _leading_key_block_end(lines: Sequence[str]) -> int:
    """Return the index of an END key marker seen before any BEGIN marker, else -1."""
    for index, line in enumerate(lines):
        if PRIVATE_KEY_BEGIN.search(line):
            return -1
        if PRIVATE_KEY_END.search(line):
            return index
    return -1
