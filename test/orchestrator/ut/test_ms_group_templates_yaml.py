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

"""The metadata-service group templates must render to parseable YAML.

provision_common parses each rendered ms-group-<fg>.yaml with ``from_yaml``
("Parse FG group entries"). Every line of the cloud-config embedded under
``content: |`` has to stay indented below the block, so a shell heredoc body or
terminator written at column 1 ends the block and breaks the parse for the whole
functional group.

The Jinja is neutralised (tag-only lines removed, ``{{ ... }}`` replaced by a
placeholder) so the check needs no Ansible and covers every branch of the template.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATE_DIR = (_REPO_ROOT / "src" / "orchestrator" / "roles" / "provision_common"
                 / "templates" / "metadata_svc")
_TEMPLATES = sorted(_TEMPLATE_DIR.glob("ms-group-*.yaml.j2"))

_TAG_ONLY_LINE = re.compile(r"^\s*(\{%.*%\}|\{#.*#\})\s*$")
_EXPRESSION = re.compile(r"\{\{.*?\}\}")


def _neutralise(text: str) -> str:
    """Return the template text with its Jinja removed or replaced by a placeholder."""
    lines = [line for line in text.splitlines() if not _TAG_ONLY_LINE.match(line)]
    return _EXPRESSION.sub("X", "\n".join(lines)) + "\n"


def test_templates_found():
    """The glob finds the templates (a moved folder must not silently pass)."""
    assert len(_TEMPLATES) >= 10


@pytest.mark.parametrize("template", _TEMPLATES, ids=lambda path: path.name)
def test_template_renders_parseable_yaml(template):
    """Each group template is a YAML list whose first entry carries file.content."""
    try:
        entries = yaml.safe_load(_neutralise(template.read_text(encoding="utf-8")))
    except yaml.YAMLError as exc:
        pytest.fail(f"{template.name} does not render to valid YAML: {exc}")
    assert isinstance(entries, list) and entries, f"{template.name}: no group entries"
    for entry in entries:
        assert entry.get("name"), f"{template.name}: an entry has no name"
        content = (entry.get("file") or {}).get("content")
        assert isinstance(content, str) and content.strip(), (
            f"{template.name}: entry {entry.get('name')} has no file.content")


@pytest.mark.parametrize("template", _TEMPLATES, ids=lambda path: path.name)
def test_heredoc_terminators_stay_inside_the_block(template):
    """A heredoc terminator (EOF, MPIEOF, ...) is never written at column 1."""
    for number, line in enumerate(template.read_text(encoding="utf-8").splitlines(), 1):
        assert not re.fullmatch(r"[A-Z_]*EOF", line), (
            f"{template.name}:{number} '{line}' is at column 1 and ends the YAML block")
