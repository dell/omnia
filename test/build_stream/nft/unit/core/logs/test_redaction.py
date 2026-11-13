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

"""TC-UT-005: RedactionService tiered pattern application (ER-BSM-003 FR-3.2).

Secret-looking values below are synthetic fixtures, not real credentials.
"""

import re
import time

import pytest

from core.logs.redaction import RedactionService, RedactionTier
from core.logs.redaction_patterns import (
    REDACTED,
    REDACTED_EMAIL,
    REDACTED_IP,
    REDACTION_SUPPRESSED_LINE,
)

pytestmark = pytest.mark.unit


@pytest.fixture(name="service")
def service_fixture() -> RedactionService:
    """Default redaction service."""
    return RedactionService()


class TestTierSelection:
    """Tier 1 vs Tier 1 + Tier 2 behaviour."""

    def test_secrets_only_redacts_token_and_keeps_ip(self, service):
        """GIVEN a GitLab token and host IP WHEN secrets_only THEN only the token is hidden."""
        out = service.redact("token glpat-abc123secret on 192.168.1.100")
        assert "glpat-abc123secret" not in out
        assert REDACTED in out
        assert "192.168.1.100" in out

    def test_full_tier_also_redacts_ip_and_email(self, service):
        """GIVEN a token, IP, and e-mail WHEN full THEN all three are hidden."""
        out = service.redact(
            "glpat-abc123secret 192.168.1.100 ops@example.com", RedactionTier.FULL
        )
        assert "glpat-abc123secret" not in out
        assert REDACTED_IP in out
        assert REDACTED_EMAIL in out

    def test_default_tier_is_secrets_only(self, service):
        """Default tier preserves operational identifiers (Tier 3)."""
        assert service.redact("node 10.5.0.1 ready") == "node 10.5.0.1 ready"


class TestSecretPatterns:
    """Each Tier 1 pattern from HLD 5.3.4."""

    @pytest.mark.parametrize(
        "line, leaked",
        [
            ("Authorization: Bearer abc.def-ghi", "abc.def-ghi"),
            ("jwt eyJhbGciOiJSUzI1.eyJzdWIiOiJjbGllbnQ.c2lnbmF0dXJlX2Jsb2I", "eyJhbGciOiJSUzI1"),
            ("client_secret=hunter2", "hunter2"),
            ("password=mysecretpassword", "mysecretpassword"),  # gitleaks:allow - test fixture
            ("passwd: plainvalue", "plainvalue"),  # gitleaks:allow - test fixture
            ('{"ansible_password": "s3cr3t-value", "changed": false}', "s3cr3t-value"),
            ("api_key='k-123456'", "k-123456"),
            ("postgresql://admin:dbpass123@localhost:5432/bsm", "dbpass123"),
            ("runner glrt-AbCdEf123456789", "glrt-AbCdEf123456789"),
        ],
    )
    def test_secret_values_are_redacted(self, service, line, leaked):
        """GIVEN a secret-bearing line WHEN redacted THEN the secret value is removed."""
        out = service.redact(line)
        assert leaked not in out
        assert REDACTED in out

    def test_quoted_value_keeps_quotes(self, service):
        """JSON structure remains valid after redaction."""
        out = service.redact('{"gitlab_root_password": "abc"}')
        assert out == '{"gitlab_root_password": "' + REDACTED + '"}'

    def test_db_url_keeps_user_and_host(self, service):
        """Only the credential portion of a URL is removed."""
        out = service.redact("postgresql://admin:dbpass123@localhost:5432/bsm")
        assert out == f"postgresql://admin:{REDACTED}@localhost:5432/bsm"

    def test_inline_private_key_redacted(self, service):
        """A JSON-escaped PEM key on one line is removed entirely."""
        line = 'key: "-----BEGIN RSA PRIVATE KEY-----\\nMIIEabc\\n-----END RSA PRIVATE KEY-----" x'  # gitleaks:allow - test fixture
        out = service.redact(line)
        assert "MIIEabc" not in out
        assert out.endswith(" x")

    @pytest.mark.parametrize(
        "line",
        [
            "TASK [hosted_gitlab : Change GitLab root password] ****",
            "Installed glibc-minimal-langpack-2.39 on 10.5.0.1",
            "ok: [oim] => (item=gitlab_root_password)",
            "PLAY RECAP oim : ok=12 changed=3 unreachable=0 failed=0",
        ],
    )
    def test_operational_content_preserved(self, service, line):
        """GIVEN task names, packages, and IPs WHEN redacted THEN they stay verbatim."""
        assert service.redact(line) == line


class TestMultiLinePrivateKey:
    """PEM blocks that span lines, including windows starting mid-block."""

    def test_full_block_redacted_and_following_line_kept(self, service):
        """BEGIN..END lines are redacted; subsequent output is preserved."""
        lines = [
            "before",
            "-----BEGIN EC PRIVATE KEY-----",
            "MHcCAQEEIBody",
            "-----END EC PRIVATE KEY-----",
            "after",
        ]
        result = service.redact_lines(lines)
        assert result.lines == ["before", REDACTED, REDACTED, REDACTED, "after"]
        assert result.redacted_lines == 3

    def test_window_starting_inside_block(self, service):
        """GIVEN a tail window that begins inside a key WHEN redacted THEN body lines are hidden."""
        lines = ["MIIEbody1", "MIIEbody2", "-----END RSA PRIVATE KEY-----", "after"]
        result = service.redact_lines(lines)
        assert result.lines == [REDACTED, REDACTED, REDACTED, "after"]

    def test_unterminated_block_redacts_remaining_lines(self, service):
        """A block without END redacts every remaining line (fail closed)."""
        lines = ["-----BEGIN OPENSSH PRIVATE KEY-----", "b3BlbnNzaC1rZXk", "more"]  # gitleaks:allow - test fixture
        assert service.redact_lines(lines).lines == [REDACTED, REDACTED, REDACTED]


class TestIdempotencyAndCounting:
    """Second-pass safety and counters used for NFR-4 logging."""

    @pytest.mark.parametrize(
        "line",
        [
            f"password={REDACTED}",
            f'"password": "{REDACTED}"',
            f"Authorization: Bearer {REDACTED}",
            f"postgresql://admin:{REDACTED}@db",  # gitleaks:allow - test fixture
            REDACTED,
        ],
    )
    def test_already_redacted_content_unchanged(self, service, line):
        """GIVEN write-time markers WHEN redacted again THEN the line is unchanged."""
        result = service.redact_lines([line])
        assert result.lines == [line]
        assert result.redacted_lines == 0

    def test_counts_only_changed_lines(self, service):
        """redacted_lines counts lines whose content changed."""
        result = service.redact_lines(["ok", "password=x", "token: y", "fine"])
        assert result.redacted_lines == 2
        assert result.suppressed_lines == 0


class _ExplodingPattern:  # pylint: disable=too-few-public-methods
    """Pattern stand-in whose substitution fails like a runaway regex."""

    def sub(self, _replacement, _line):
        """Raise the error the service must contain."""
        raise re.error("catastrophic backtracking")


class TestFailClosed:
    """Redaction failures never leak the original line."""

    def test_failing_pattern_suppresses_line(self):
        """GIVEN a pattern that errors WHEN redacting THEN the line is withheld."""
        service = RedactionService(secret_rules=[(_ExplodingPattern(), REDACTED)])
        result = service.redact_lines(["password=leak", "other"])
        assert result.lines == [REDACTION_SUPPRESSED_LINE, REDACTION_SUPPRESSED_LINE]
        assert result.suppressed_lines == 2
        assert "leak" not in "".join(result.lines)

    def test_long_hostile_line_is_bounded(self, service):
        """Bounded quantifiers keep a 400 KB adversarial line fast."""
        hostile = "a" * 200_000 + "password" + "b" * 200_000
        started = time.monotonic()
        service.redact(hostile)
        assert time.monotonic() - started < 2.0
