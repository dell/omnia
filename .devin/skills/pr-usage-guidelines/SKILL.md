# PR Usage Guidelines

## Context
This skill provides guidelines for when to include a Usage section in PR descriptions and what it should contain.

## Guidelines

### When to Include a Usage Section
Include a Usage section only when the change introduces:
- New commands
- New CLI options
- New APIs/endpoints
- New configurations
- New deployment or operational workflows
- Migration steps

### Usage Section Requirements
- The Usage section should contain only practical examples that users or operators can run immediately
- Prefer copy-pasteable command snippets
- Do not include Usage if there is nothing actionable for consumers

## Examples

### Good Usage Section (for new CLI option)
```markdown
## Usage

### New flag for dry-run mode
```bash
ansible-playbook playbooks/utils.yml --tags collect --extra-vars "dry_run=true"
```

### New configuration option
```yaml
# In omnia.env
DRY_RUN_MODE=true
```
```

### Bad Usage Section (no actionable content)
```markdown
## Usage

This change updates the internal data structure for better performance. No user action required.
```
→ This should be omitted entirely.

## When Generating PR Descriptions
1. Check if the change introduces any of the items listed above
2. If yes, create a Usage section with practical, copy-pasteable examples
3. If no, omit the Usage section entirely
