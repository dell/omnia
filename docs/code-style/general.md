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

## 6. Version Control

- One logical change per commit
- Clear, descriptive commit messages
- Branch naming: `feature/<name>` or `fix/<name>`
