# General Code Style -- Omnia

Based on [Dell Omnia General Style Guide](https://github.com/dell/omnia).

## 1. Copyright Header

Every source file (`.yml`, `.py`, `.sh`) SHALL include this header. `.j2` templates are excluded (the parent role carries the header):

```
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
```

## 2. Principles

- **Readability**: Code should read like prose — clear variable names, step comments
- **Consistency**: Follow project conventions, not personal preference
- **Simplicity**: Prefer simple over clever
- **Maintainability**: Write for the next developer
- **Documentation**: Document the *why*, not just the *what*

## 3. File Naming Convention

| File Type | Convention | Examples |
|-----------|-----------|----------|
| Code files (`.py`, `.yml`, `.sh`, `.j2`) | `snake_case` | `validate_image_build_config.py`, `main.yml` |
| Documentation files (`.md`) | `kebab-case` | `domain-integration.md`, `galaxy-testing-guide.md` |
| Schema files (`.json`) | `snake_case` | `image_build_config.json` |
| Reserved names (uppercase) | `UPPER_CASE` | `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE`, `AGENTS.md` |

**Rules:**

- Code files SHALL use `snake_case` with lowercase letters
- Documentation files SHALL use `kebab-case` with lowercase letters
- Only standard community-recognized files use uppercase names (`README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `AGENTS.md`)
- Never use `SCREAMING_CASE` for regular documentation files
- Directory names SHALL use `snake_case`

## 4. README Content Guidelines

Every `README.md` SHALL include:

1. **Title** -- one-line `# <Component Name>` heading
2. **Purpose** -- 1-2 sentence description of what this component does
3. **Structure** -- directory tree or file listing (for domains and complex directories)

Domain-level `README.md` SHALL additionally include:

4. **Quick Start** -- minimal steps to run the playbook
5. **Tags** -- supported `--tags` values with descriptions
6. **Input/Output** -- what files are consumed and produced
7. **Dependencies** -- prerequisites and upstream contracts

Role-level `README.md` SHALL additionally include:

4. **Role Variables** -- key variables with defaults
5. **Dependencies** -- other roles or collections required
6. **Example Playbook** -- minimal usage snippet

## 5. File Organization

- Group related files in directories
- Use descriptive file names per the naming convention above
- Keep files focused on a single responsibility
- Maximum file length: ~300 lines (split if larger)

## 6. Test Automation — Mandatory Co-Change Rule

Every code change MUST include corresponding test automation updates. Code and tests are treated as a single deliverable — one is never merged without the other.

| Change Type | Required Test Update |
|-------------|---------------------|
| New feature / role / module | New FVT test cases covering the feature |
| Bug fix | Failing test that reproduces the bug, then passes after fix |
| Refactor (behavior unchanged) | Existing tests pass — no new tests needed unless coverage gaps exist |
| Config schema change | Unit test updates for schema validation |
| New env var / input field | Precheck test and validation test updates |
| Playbook tag added | New scenario directory under `fvt/` with deploy + verify tests |

**Rules:**

1. **PRs that change `src/` code without updating `test/` MUST include a justification** in the PR description explaining why no test changes are needed.
2. **New playbook tags MUST have a corresponding FVT scenario** — no tag goes untested.
3. **Deleted features MUST have their tests removed** — no orphan tests.
4. **Test coverage SHOULD increase or stay constant** — never decrease without justification.
5. **CI gates enforce this** — PR reviewers MUST verify test co-changes before approving.

## 7. AI Agent Usage Policy

AI agents (Devin, Copilot, Cursor, ChatGPT, Claude, or any other AI-assisted coding tool) MAY be used for development, but the following restrictions apply:

1. **AI agents MUST NOT be used for sign-off or approval.** All code reviews, PR approvals, and merge decisions MUST be made by a human team member. An AI-generated "LGTM" or approval comment is not a valid sign-off.
2. **AI-generated code MUST be reviewed by a human** before merge — the developer who submits the PR is responsible for every line, regardless of whether it was AI-generated.
3. **AI agents MUST NOT modify security policies**, compliance controls, branch protection rules, or CI gate configurations.
4. **AI-generated commit messages MUST be reviewed** — ensure they accurately describe the change and do not contain hallucinated details.
5. **Co-authored-by tags** (e.g., `Co-Authored-By: Devin <...>`) MUST NOT be included in commits. Only the human developer's `Signed-off-by` line should appear.

## 8. Version Control

### 8.1 Commit Format (MANDATORY)

```bash
git commit --signoff -m "<type>(<scope>): <description>"
```

**Types:** `feat` | `fix` | `docs` | `style` | `refactor` | `test` | `chore` | `sdd` | `ci` | `perf` | `build` | `revert`

**Scope:** domain, component, or Story ID (e.g., `oim`, `prov`, `A19`, `sdd`)

**Examples:**

```
feat(prov):       ER-PROV-001 add iDRAC-based node discovery
fix(tele):        A12-telemetry-fix null pointer in idrac collector
docs(specs):      update ER-OIM-001 acceptance criteria
sdd(checkpoint):  A19 CP2 approved [SHA:abc123]
sdd(plan):        scaffold add-idrac-telemetry-source Story workspace
```

### 8.2 Commit Message Rules

- **First line**: `<type>(<scope>): <description>` (max 72 characters)
- **Imperative mood**: "add" not "adds" or "added"
- **No period** at end of description line
- **Body** (optional): blank line, then explain the WHY — reference ER ID and Story ID
- **Signed-off-by**: auto-added by `--signoff` flag (required for DCO)
- **Co-Authored-By tags** (e.g., `Co-Authored-By: Devin <...>`) MUST NOT be included — only the human developer's `Signed-off-by` line should appear
- Include **Story ID** in scope or description for every code commit

### 8.3 Branch Naming

```
feature/<issue>-<short-description>
bugfix/<issue>-<short-description>
```

### 8.4 General Rules

- One logical change per commit
- Clear, descriptive commit messages
- Sync before commit/push: `git fetch origin && git merge origin/main`
