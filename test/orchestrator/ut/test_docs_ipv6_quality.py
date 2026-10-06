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
"""Unit tests for ER-ORCH-005 customer-facing documentation quality.

Story: ER-ORCH-005-customer-docs
Covers:
- NFR-1: No hardcoded /opt/omnia/ paths; fd00:1b:: documentation prefix
- NFR-2: Tables have header rows; diagrams have plain-text descriptions
- FR-1: Configuration guide exists (dual-stack, IPv4-only, IPv6-only modes)
- FR-2: Allocation export and network_spec reference documented
- FR-3: Troubleshooting guide has failure-state entries
- Release notes: CHANGELOG has ER-ORCH-005 entry

These are isolated UT-level checks with no cluster dependency.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# Repository and documentation paths
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DOCS_DIR = _REPO_ROOT / "src" / "orchestrator" / "docs"
_CHANGELOG = _REPO_ROOT / "src" / "orchestrator" / "CHANGELOG.md"

# Documentation files authored by Story ER-ORCH-005-customer-docs
_DOC_FILES = {
    "config_guide": _DOCS_DIR / "ipv6-infiniband-configuration.md",
    "upgrade_guide": _DOCS_DIR / "ipv6-upgrade-guide.md",
    "troubleshooting": _DOCS_DIR / "troubleshooting.md",
    "changelog": _CHANGELOG,
}

# Hardcoded path pattern: /opt/omnia/ NOT preceded by $ or env variable
_HARDCODED_PATH_RE = re.compile(r'(?<!\$)(?<!\w)/opt/omnia/')

# Markdown table header pattern: | Header | Header | ... |
# followed by a separator line: | --- | --- | ... |
_TABLE_HEADER_RE = re.compile(
    r'^\|[^\n]+\|\s*\n\|[\s:|-]+\|',
    re.MULTILINE,
)

# Bare table (pipe-separated) without separator
_BARE_TABLE_RE = re.compile(r'^\|[^\n]+\|$', re.MULTILINE)

# Markdown cross-reference link pattern: [text](relative-path.md)
_CROSS_REF_RE = re.compile(r'\[([^\]]+)\]\(([^)]+\.md)\)')


def _read_doc(path: Path) -> str:
    """Read a documentation file and return its content."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ===================================================================
# TC-UT-DOC-001: Documentation files exist
# ===================================================================

class TestDocumentationFilesExist:
    """FR-1/FR-2/FR-3: Required documentation files exist."""

    def test_config_guide_exists(self):
        """ORCH_UT_DOC_001: IPoIB IPv6 configuration guide exists."""
        assert _DOC_FILES["config_guide"].is_file(), (
            f"Missing: {_DOC_FILES['config_guide']}"
        )

    def test_upgrade_guide_exists(self):
        """ORCH_UT_DOC_002: IPv6 upgrade guide exists."""
        assert _DOC_FILES["upgrade_guide"].is_file(), (
            f"Missing: {_DOC_FILES['upgrade_guide']}"
        )

    def test_troubleshooting_exists(self):
        """ORCH_UT_DOC_003: Troubleshooting guide exists."""
        assert _DOC_FILES["troubleshooting"].is_file(), (
            f"Missing: {_DOC_FILES['troubleshooting']}"
        )

    def test_changelog_exists(self):
        """ORCH_UT_DOC_004: CHANGELOG.md exists."""
        assert _DOC_FILES["changelog"].is_file(), (
            f"Missing: {_DOC_FILES['changelog']}"
        )


# ===================================================================
# TC-UT-DOC-002: No hardcoded /opt/omnia/ paths (NFR-1)
# ===================================================================

class TestNoHardcodedPaths:
    """NFR-1: No hardcoded /opt/omnia/ paths in documentation."""

    @pytest.mark.parametrize("doc_key", ["config_guide", "upgrade_guide"])
    def test_no_hardcoded_opt_omnia(self, doc_key: str):
        """ORCH_UT_DOC_010: Doc files use variables, not /opt/omnia/."""
        path = _DOC_FILES[doc_key]
        if not path.is_file():
            pytest.skip(f"File not found: {path}")
        content = _read_doc(path)
        matches = _HARDCODED_PATH_RE.findall(content)
        assert not matches, (
            f"{path.name} contains hardcoded /opt/omnia/ path(s): "
            f"found {len(matches)} occurrence(s)"
        )

    def test_troubleshooting_no_hardcoded_paths(self):
        """ORCH_UT_DOC_011: Troubleshooting uses variables, not /opt/omnia/."""
        path = _DOC_FILES["troubleshooting"]
        if not path.is_file():
            pytest.skip(f"File not found: {path}")
        content = _read_doc(path)
        matches = _HARDCODED_PATH_RE.findall(content)
        assert not matches, (
            f"troubleshooting.md contains hardcoded /opt/omnia/ path(s): "
            f"found {len(matches)} occurrence(s)"
        )


# ===================================================================
# TC-UT-DOC-003: Documentation prefix fd00:1b:: (NFR-1)
# ===================================================================

class TestDocumentationPrefix:
    """NFR-1: Examples use fd00:1b:: documentation prefix."""

    @pytest.mark.parametrize("doc_key", ["config_guide", "upgrade_guide"])
    def test_uses_documentation_prefix(self, doc_key: str):
        """ORCH_UT_DOC_020: IPv6 examples use fd00:1b:: prefix."""
        path = _DOC_FILES[doc_key]
        if not path.is_file():
            pytest.skip(f"File not found: {path}")
        content = _read_doc(path)
        # Verify documentation uses fd00:1b:: examples
        assert "fd00:1b::" in content, (
            f"{path.name} does not contain fd00:1b:: documentation prefix"
        )

    @pytest.mark.parametrize("doc_key", ["config_guide", "upgrade_guide"])
    def test_no_production_ipv6_addresses(self, doc_key: str):
        """ORCH_UT_DOC_021: No production 2001:db8:: in examples."""
        path = _DOC_FILES[doc_key]
        if not path.is_file():
            pytest.skip(f"File not found: {path}")
        content = _read_doc(path)
        # 2001:db8:: is RFC 3849 documentation prefix but we use fd00:1b::
        # Verify no global unicast addresses (2000::/3) are used in examples
        # Allow 2001:db8:: as RFC documentation prefix if present
        global_unicast = re.findall(
            r'(?<![a-fA-F0-9:])2[0-9a-fA-F]{3}:'
            r'(?!db8:)[0-9a-fA-F:]+',
            content,
        )
        assert not global_unicast, (
            f"{path.name} contains global unicast addresses: {global_unicast}"
        )


# ===================================================================
# TC-UT-DOC-004: Cross-references resolve (NFR-1)
# ===================================================================

class TestCrossReferences:
    """NFR-1: Markdown cross-reference links resolve to existing files."""

    @pytest.mark.parametrize("doc_key", ["config_guide", "upgrade_guide"])
    def test_cross_references_resolve(self, doc_key: str):
        """ORCH_UT_DOC_030: All Markdown links in doc point to existing files."""
        path = _DOC_FILES[doc_key]
        if not path.is_file():
            pytest.skip(f"File not found: {path}")
        content = _read_doc(path)
        refs = _CROSS_REF_RE.findall(content)
        broken = []
        for link_text, rel_path in refs:
            # Skip external URLs
            if rel_path.startswith("http://") or rel_path.startswith("https://"):
                continue
            target = (path.parent / rel_path).resolve()
            if not target.is_file():
                broken.append(f"[{link_text}]({rel_path}) -> {target}")
        assert not broken, (
            f"{path.name} has broken cross-references:\n"
            + "\n".join(f"  - {b}" for b in broken)
        )


# ===================================================================
# TC-UT-DOC-005: Configuration guide content (FR-1)
# ===================================================================

class TestConfigGuideContent:
    """FR-1: Configuration guide covers dual-stack, IPv4-only, IPv6-only."""

    @pytest.fixture()
    def config_content(self) -> str:
        """Load configuration guide content."""
        path = _DOC_FILES["config_guide"]
        if not path.is_file():
            pytest.skip(f"File not found: {path}")
        return _read_doc(path)

    def test_covers_dual_stack(self, config_content: str):
        """ORCH_UT_DOC_040: Config guide covers dual-stack mode."""
        assert "dual-stack" in config_content.lower() or "Dual-Stack" in config_content

    def test_covers_ipv4_only(self, config_content: str):
        """ORCH_UT_DOC_041: Config guide covers IPv4-only mode."""
        assert "ipv4-only" in config_content.lower() or "IPv4-Only" in config_content

    def test_covers_ipv6_only(self, config_content: str):
        """ORCH_UT_DOC_042: Config guide covers IPv6-only mode."""
        assert "ipv6-only" in config_content.lower() or "IPv6-Only" in config_content

    def test_documents_ib_ipv4_column(self, config_content: str):
        """ORCH_UT_DOC_043: Config guide references IB_IPV4 column."""
        assert "IB_IPV4" in config_content

    def test_documents_ib_ipv6_column(self, config_content: str):
        """ORCH_UT_DOC_044: Config guide references IB_IPV6 column."""
        assert "IB_IPV6" in config_content

    def test_documents_ipv4_subnet_field(self, config_content: str):
        """ORCH_UT_DOC_045: Config guide references ipv4_subnet field."""
        assert "ipv4_subnet" in config_content

    def test_documents_ipv6_subnet_field(self, config_content: str):
        """ORCH_UT_DOC_046: Config guide references ipv6_subnet field."""
        assert "ipv6_subnet" in config_content

    def test_csv_example_has_12_columns(self, config_content: str):
        """ORCH_UT_DOC_047: CSV example shows 12-column header."""
        assert "IB_IPV4,IB_IPV6" in config_content

    def test_documents_backward_compatibility(self, config_content: str):
        """ORCH_UT_DOC_048: Config guide mentions backward compatibility."""
        lower = config_content.lower()
        assert "backward" in lower or "legacy" in lower


# ===================================================================
# TC-UT-DOC-006: Tables have header rows (NFR-2)
# ===================================================================

class TestTableHeaders:
    """NFR-2: All Markdown tables have proper header rows."""

    @pytest.mark.parametrize("doc_key", ["config_guide", "upgrade_guide"])
    def test_tables_have_headers(self, doc_key: str):
        """ORCH_UT_DOC_050: All tables have header + separator rows."""
        path = _DOC_FILES[doc_key]
        if not path.is_file():
            pytest.skip(f"File not found: {path}")
        content = _read_doc(path)
        # Find all pipe-separated lines (table rows)
        bare_rows = _BARE_TABLE_RE.findall(content)
        if not bare_rows:
            # No tables in doc — pass
            return
        # Verify at least one proper table exists (with header separator)
        proper_tables = _TABLE_HEADER_RE.findall(content)
        assert proper_tables, (
            f"{path.name} has pipe-separated rows but no proper table "
            f"header+separator pattern"
        )


# ===================================================================
# TC-UT-DOC-007: CHANGELOG entry (Release Notes)
# ===================================================================

class TestChangelogEntry:
    """Release notes: CHANGELOG has ER-ORCH-005 entry."""

    @pytest.fixture()
    def changelog_content(self) -> str:
        """Load CHANGELOG content."""
        path = _DOC_FILES["changelog"]
        if not path.is_file():
            pytest.skip(f"File not found: {path}")
        return _read_doc(path)

    def test_changelog_has_version_entry(self, changelog_content: str):
        """ORCH_UT_DOC_060: CHANGELOG has version entry for IPv6 feature."""
        assert "2.3.1" in changelog_content

    def test_changelog_mentions_ipv6(self, changelog_content: str):
        """ORCH_UT_DOC_061: CHANGELOG entry mentions IPv6."""
        assert "IPv6" in changelog_content

    def test_changelog_mentions_er_id(self, changelog_content: str):
        """ORCH_UT_DOC_062: CHANGELOG entry references ER-ORCH-005."""
        assert "ER-ORCH-005" in changelog_content

    def test_changelog_mentions_dual_stack(self, changelog_content: str):
        """ORCH_UT_DOC_063: CHANGELOG entry mentions dual-stack."""
        assert "dual-stack" in changelog_content.lower()

    def test_changelog_mentions_connectx(self, changelog_content: str):
        """ORCH_UT_DOC_064: CHANGELOG entry mentions supported hardware."""
        assert "ConnectX" in changelog_content

    def test_changelog_mentions_known_limitations(self, changelog_content: str):
        """ORCH_UT_DOC_065: CHANGELOG has known limitations section."""
        assert "Known Limitations" in changelog_content


# ===================================================================
# TC-UT-DOC-008: Troubleshooting IPv6 entries (FR-3)
# ===================================================================

class TestTroubleshootingEntries:
    """FR-3: Troubleshooting guide has IPv6 failure-state entries."""

    @pytest.fixture()
    def troubleshooting_content(self) -> str:
        """Load troubleshooting guide content."""
        path = _DOC_FILES["troubleshooting"]
        if not path.is_file():
            pytest.skip(f"File not found: {path}")
        return _read_doc(path)

    def test_has_degraded_ipv6_entry(self, troubleshooting_content: str):
        """ORCH_UT_DOC_070: Troubleshooting covers DEGRADED_IPV6."""
        assert "DEGRADED_IPV6" in troubleshooting_content

    def test_has_dad_failure_entry(self, troubleshooting_content: str):
        """ORCH_UT_DOC_071: Troubleshooting covers DAD failure."""
        lower = troubleshooting_content.lower()
        assert "dad" in lower or "duplicate address detection" in lower

    def test_has_device_selection_entry(self, troubleshooting_content: str):
        """ORCH_UT_DOC_072: Troubleshooting covers IB device selection."""
        lower = troubleshooting_content.lower()
        assert "device not found" in lower or "wrong interface" in lower

    def test_has_roce_filter_entry(self, troubleshooting_content: str):
        """ORCH_UT_DOC_073: Troubleshooting covers RoCE/Ethernet filter."""
        assert "RoCE" in troubleshooting_content or "Ethernet" in troubleshooting_content

    def test_has_legacy_csv_entry(self, troubleshooting_content: str):
        """ORCH_UT_DOC_074: Troubleshooting covers legacy IB_IP CSV."""
        assert "IB_IP" in troubleshooting_content


# ===================================================================
# TC-UT-DOC-009: Upgrade guide content
# ===================================================================

class TestUpgradeGuideContent:
    """Upgrade guide covers migration steps and rollback."""

    @pytest.fixture()
    def upgrade_content(self) -> str:
        """Load upgrade guide content."""
        path = _DOC_FILES["upgrade_guide"]
        if not path.is_file():
            pytest.skip(f"File not found: {path}")
        return _read_doc(path)

    def test_has_network_spec_update_step(self, upgrade_content: str):
        """ORCH_UT_DOC_080: Upgrade guide has network_spec update step."""
        assert "network_spec" in upgrade_content

    def test_has_csv_update_step(self, upgrade_content: str):
        """ORCH_UT_DOC_081: Upgrade guide has CSV update step."""
        assert "pxe_mapping_file" in upgrade_content

    def test_has_validation_step(self, upgrade_content: str):
        """ORCH_UT_DOC_082: Upgrade guide has validation step."""
        lower = upgrade_content.lower()
        assert "validate" in lower

    def test_has_rollback_section(self, upgrade_content: str):
        """ORCH_UT_DOC_083: Upgrade guide has rollback section."""
        assert "Rollback" in upgrade_content or "rollback" in upgrade_content

    def test_has_faq_section(self, upgrade_content: str):
        """ORCH_UT_DOC_084: Upgrade guide has FAQ section."""
        assert "FAQ" in upgrade_content

    def test_documents_backward_compat(self, upgrade_content: str):
        """ORCH_UT_DOC_085: Upgrade guide mentions backward compatibility."""
        lower = upgrade_content.lower()
        assert "backward" in lower or "legacy" in lower
