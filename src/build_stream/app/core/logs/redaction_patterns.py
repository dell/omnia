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
# Applicable rules used: CG-LOGGING-001.2, CG-SECRETS-001.1
# ****

"""Tiered credential redaction pattern registry (ER-BSM-003 HLD 5.3.4).

Tier 1 (secrets) is applied to every log served by the API. Tier 2 (IP and
e-mail identifiers) is applied only when full redaction is requested; Tier 3
operational data (host IPs, stage names, task output) is never redacted from
execution logs.

Every pattern uses bounded quantifiers so a single long line cannot cause
catastrophic backtracking. Replacements are idempotent: re-applying a pattern
to already-redacted text leaves it unchanged.
"""

import re
from typing import Callable, List, Pattern, Tuple, Union

REDACTED = "***REDACTED***"
REDACTION_SUPPRESSED_LINE = "[REDACTION ERROR \u2014 line suppressed]"
REDACTED_IP = "<REDACTED_IP>"
REDACTED_EMAIL = "<REDACTED_EMAIL>"

Replacement = Union[str, Callable[[re.Match], str]]
RedactionRule = Tuple[Pattern[str], Replacement]

PRIVATE_KEY_BEGIN = re.compile(r"-----BEGIN (?:[A-Z0-9]{1,16} ){0,4}PRIVATE KEY-----")
PRIVATE_KEY_END = re.compile(r"-----END (?:[A-Z0-9]{1,16} ){0,4}PRIVATE KEY-----")

_SECRET_KEY_WORDS = (
    r"(?:password|passwd|pwd|secret|token|api[_-]?key|apikey|credential|private[_-]?key)"
)

_KEY_VALUE = re.compile(
    r"(?P<prefix>(?<![\w.-])[\"']?[\w.-]{0,40}?" + _SECRET_KEY_WORDS
    + r"[\w.-]{0,40}[\"']?\s{0,3}[:=]\s{0,3})"
    r"(?P<value>\"[^\"\n]{0,4096}\"|'[^'\n]{0,4096}'|[^\s,;\"'}\])]{1,4096})",
    re.IGNORECASE,
)


def _redact_key_value(match: re.Match) -> str:
    """Replace the value of a secret-bearing key, keeping any surrounding quotes."""
    value = match.group("value")
    if value[0] in "\"'":
        return f"{match.group('prefix')}{value[0]}{REDACTED}{value[0]}"
    return f"{match.group('prefix')}{REDACTED}"


SECRET_RULES: List[RedactionRule] = [
    (
        re.compile(
            r"-----BEGIN (?:[A-Z0-9]{1,16} ){0,4}PRIVATE KEY-----.*?"
            r"(?:-----END (?:[A-Z0-9]{1,16} ){0,4}PRIVATE KEY-----|$)"
        ),
        REDACTED,
    ),
    (
        re.compile(
            r"\b(?:glpat|glprt|glrt|gldt|glptt|glcbt|glimt|glagent|gloas|glsoat|glffct|glft)"
            r"-[A-Za-z0-9_-]{8,256}"
        ),
        REDACTED,
    ),
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]{5,4096}\.[A-Za-z0-9_-]{5,4096}\.[A-Za-z0-9_-]{5,4096}"),
        REDACTED,
    ),
    (re.compile(r"(?i)\b(bearer\s{1,5})[A-Za-z0-9._~+/=-]{1,4096}"), r"\1" + REDACTED),
    (
        re.compile(r"(?i)\b([a-z][a-z0-9+.-]{1,20}://[^\s:/@]{1,128}:)[^\s@/]{1,256}@"),
        r"\1" + REDACTED + "@",
    ),
    (_KEY_VALUE, _redact_key_value),
]

IDENTIFIER_RULES: List[RedactionRule] = [
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), REDACTED_IP),
    (re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b"), REDACTED_IP),
    (
        re.compile(r"\b[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,24}\b"),
        REDACTED_EMAIL,
    ),
]
