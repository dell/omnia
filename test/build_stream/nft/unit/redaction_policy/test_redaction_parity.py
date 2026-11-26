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

"""Parity: baseline rules redact exactly like the former hard-coded SECRET_RULES (TC-UT-018)."""

import re
from typing import List

import pytest

from core.logs.redaction import RedactionService, RedactionTier
from core.logs.redaction_patterns import REDACTED, RedactionRule

pytestmark = pytest.mark.unit

_LEGACY_REDACTED_IP = "<REDACTED_IP>"
_LEGACY_REDACTED_EMAIL = "<REDACTED_EMAIL>"
_LEGACY_KEY_WORDS = (
    r"(?:password|passwd|pwd|secret|token|api[_-]?key|apikey|credential|private[_-]?key)"
)
_LEGACY_KEY_VALUE = re.compile(
    r"(?P<prefix>(?<![\w.-])[\"']?[\w.-]{0,40}?" + _LEGACY_KEY_WORDS
    + r"[\w.-]{0,40}[\"']?\s{0,3}[:=]\s{0,3})"
    r"(?P<value>\"[^\"\n]{0,4096}\"|'[^'\n]{0,4096}'|[^\s,;\"'}\])]{1,4096})",
    re.IGNORECASE,
)


def _legacy_redact_key_value(match: re.Match) -> str:
    """Legacy key = value replacement, keeping surrounding quotes."""
    value = match.group("value")
    if value[0] in "\"'":
        return f"{match.group('prefix')}{value[0]}{REDACTED}{value[0]}"
    return f"{match.group('prefix')}{REDACTED}"


LEGACY_SECRET_RULES: List[RedactionRule] = [
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
    (_LEGACY_KEY_VALUE, _legacy_redact_key_value),
]

LEGACY_IDENTIFIER_RULES: List[RedactionRule] = [
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), _LEGACY_REDACTED_IP),
    (re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b"), _LEGACY_REDACTED_IP),
    (
        re.compile(r"\b[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,24}\b"),
        _LEGACY_REDACTED_EMAIL,
    ),
]

CORPUS = [
    "token=abc123xyz",
    "password: 'hunter2'",
    'api_key = "abcd-1234"',
    "API_KEY: s3cret",
    "api-key=foo",
    "apikey: bar",
    "private-key: xyz",
    "privatekey=abc",
    "private_key: 'x y'",
    "credential: value",
    "passwd=pw1",
    "pwd: pw2",
    "secret = zzz",
    "db_password=foo",
    'token: "quoted value with spaces"',
    "vault_pass: s3cret",
    "glpat-abcdefghijk12345",
    "glft-abcdefgh",
    "Authorization: Bearer abc.def-ghi_jkl",
    "bearer    tokenvalue",
    "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.abcdefSIG123",  # gitleaks:allow
    "https://user:p%40ss@git.example.com/repo.git",  # gitleaks:allow
    "https://git.example.com/repo.git",
    "http://admin:secret@host:8080/x",  # gitleaks:allow
    "-----BEGIN RSA PRIVATE KEY-----MIIEabc-----END RSA PRIVATE KEY-----",  # gitleaks:allow
    "host 10.0.0.12 up",
    "ipv6 fe80:0:0:0:0:0:0:1 link",
    "mail admin@example.com now",
    "TASK [Gathering Facts] ********",
    "already <REDACTED_IP> and ***REDACTED***",
    "password: ***REDACTED***",  # gitleaks:allow
    "ok line with no secrets",
]

KEY_BLOCK_LINES = [
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "b3BlbnNzaC1rZXktdjEAAAAABG5vbmU=",
    "-----END OPENSSH PRIVATE KEY-----",
    "after the key 10.1.2.3",
]


@pytest.fixture(name="legacy")
def legacy_fixture() -> RedactionService:
    """Service built from the legacy hard-coded rules."""
    return RedactionService(LEGACY_SECRET_RULES, LEGACY_IDENTIFIER_RULES)


@pytest.fixture(name="policy")
def policy_fixture() -> RedactionService:
    """Service built from the rules loaded from the baseline file."""
    return RedactionService()


@pytest.mark.parametrize("tier", [RedactionTier.SECRETS_ONLY, RedactionTier.FULL])
def test_baseline_rules_redact_corpus_like_legacy_rules(legacy, policy, tier):
    """Every corpus line gives identical output for both tiers."""
    expected = legacy.redact_lines(CORPUS, tier).lines
    actual = policy.redact_lines(CORPUS, tier).lines
    assert actual == expected


@pytest.mark.parametrize("tier", [RedactionTier.SECRETS_ONLY, RedactionTier.FULL])
def test_baseline_rules_redact_key_block_like_legacy_rules(legacy, policy, tier):
    """Multi-line PEM blocks and the lines after them redact identically."""
    assert policy.redact_lines(KEY_BLOCK_LINES, tier).lines == (
        legacy.redact_lines(KEY_BLOCK_LINES, tier).lines
    )


def test_baseline_streaming_redaction_matches_legacy(legacy, policy):
    """Line-by-line redaction carries key-block state the same way."""
    legacy_state = legacy.new_stream_state()
    policy_state = policy.new_stream_state()
    for line in KEY_BLOCK_LINES + CORPUS:
        assert policy.redact_stream_line(line, policy_state) == (
            legacy.redact_stream_line(line, legacy_state)
        )
