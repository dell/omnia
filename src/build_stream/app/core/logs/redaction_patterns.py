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

"""Built-in redaction rules and markers (ER-BSM-003 HLD 5.3.4, 5.3.5).

Logic that is not data lives here: the private-key block and the ``key = value``
rule, whose key names come from the redaction policy. Other rules are loaded
from ``redaction_baseline.yml``.
"""

import re
from typing import Callable, Pattern, Sequence, Tuple, Union

REDACTED = "***REDACTED***"
REDACTION_SUPPRESSED_LINE = "[REDACTION ERROR \u2014 line suppressed]"
REDACTED_IP = "<REDACTED_IP>"
REDACTED_EMAIL = "<REDACTED_EMAIL>"

Replacement = Union[str, Callable[[re.Match], str]]
RedactionRule = Tuple[Pattern[str], Replacement]

PRIVATE_KEY_BEGIN = re.compile(r"-----BEGIN (?:[A-Z0-9]{1,16} ){0,4}PRIVATE KEY-----")
PRIVATE_KEY_END = re.compile(r"-----END (?:[A-Z0-9]{1,16} ){0,4}PRIVATE KEY-----")

PRIVATE_KEY_RULE: RedactionRule = (
    re.compile(
        r"-----BEGIN (?:[A-Z0-9]{1,16} ){0,4}PRIVATE KEY-----.*?"
        r"(?:-----END (?:[A-Z0-9]{1,16} ){0,4}PRIVATE KEY-----|$)"
    ),
    REDACTED,
)


def _redact_key_value(match: re.Match) -> str:
    """Replace the value of a secret-bearing key, keeping any surrounding quotes."""
    value = match.group("value")
    if value[0] in "\"'":
        return f"{match.group('prefix')}{value[0]}{REDACTED}{value[0]}"
    return f"{match.group('prefix')}{REDACTED}"


def build_key_value_rule(key_names: Sequence[str]) -> RedactionRule:
    """Build the ``key = value`` rule for the given secret key names.

    Names are escaped and matched case-insensitively; the value replacement
    keeps any surrounding quotes.
    """
    if not key_names:
        raise ValueError("at least one secret key name is required")
    keywords = "|".join(re.escape(name) for name in key_names)
    pattern = re.compile(
        r"(?P<prefix>(?<![\w.-])[\"']?[\w.-]{0,40}?(?:" + keywords + r")"
        r"[\w.-]{0,40}[\"']?\s{0,3}[:=]\s{0,3})"
        r"(?P<value>\"[^\"\n]{0,4096}\"|'[^'\n]{0,4096}'|[^\s,;\"'}\])]{1,4096})",
        re.IGNORECASE,
    )
    return (pattern, _redact_key_value)
