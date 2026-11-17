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
from typing import List, Optional, Sequence, Tuple

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


@dataclass
class StreamRedactionState:
    """Mutable cross-line state for streaming (line-by-line) redaction.

    The watcher redacts Ansible output one line at a time as it is read from
    the subprocess pipe (ER-BSM-003 HLD 5.3.4). Unlike the window-based
    ``redact_lines`` used by the API read path, a streaming consumer sees each
    line exactly once and must remember when it is inside a multi-line PEM
    private-key block so the key body never leaks.

    Attributes:
        in_key_block: True while the stream is between a PEM BEGIN marker and
            its matching END marker.
    """

    in_key_block: bool = False


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

    @staticmethod
    def new_stream_state() -> StreamRedactionState:
        """Create fresh state for a streaming (line-by-line) redaction session."""
        return StreamRedactionState()

    def redact_stream_line(
        self,
        line: str,
        state: StreamRedactionState,
        tier: RedactionTier = RedactionTier.SECRETS_ONLY,
    ) -> Tuple[str, bool]:
        """Redact a single streamed line, carrying PEM key-block state across calls.

        This is the streaming counterpart of :meth:`redact_lines`, used by the
        playbook watcher to sanitize Ansible output as each line is read from
        the subprocess pipe. It fails closed: a line that cannot be processed is
        replaced with the suppression marker, never passed through unsanitized.

        Args:
            line: One line of subprocess output (without a trailing newline).
            state: Mutable state returned by :meth:`new_stream_state`.
            tier: Which pattern tiers to apply (write-time uses SECRETS_ONLY).

        Returns:
            A ``(output_line, suppressed)`` tuple where ``suppressed`` is True
            when the line was withheld because redaction raised.
        """
        rules = self._secret_rules
        if tier == RedactionTier.FULL:
            rules = rules + self._identifier_rules
        try:
            if state.in_key_block:
                if PRIVATE_KEY_END.search(line):
                    state.in_key_block = False
                return REDACTED, False
            begin = PRIVATE_KEY_BEGIN.search(line)
            if begin and not PRIVATE_KEY_END.search(line, begin.end()):
                state.in_key_block = True
            return _apply_rules(line, rules), False
        except (re.error, RecursionError, TypeError):
            return REDACTION_SUPPRESSED_LINE, True

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
