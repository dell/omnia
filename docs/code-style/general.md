# General Code Style — Image Build Manager

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

## 3. File Organization

- Group related files in directories
- Use descriptive file names in `snake_case`
- Keep files focused on a single responsibility
- Maximum file length: ~300 lines (split if larger)

## 4. Version Control

- One logical change per commit
- Clear, descriptive commit messages
- Branch naming: `feature/<name>` or `fix/<name>`
