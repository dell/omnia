## PR Title

<!-- Use Conventional Commits format: <type>(<scope>): <description>. -->

### Description of the Solution

<!-- Required: summarize what this PR does and why in 2-3 sentences. -->

### Related Issue

<!-- Required: use #123, owner/repository#123, or a full GitHub issue URL. -->

- Fixes #

### Changes

<!-- Required: group changes by component or area. Use sub-headings for each area. -->

#### Component (`path/to/files`)
- Change description

### Files Changed

<!-- Required: list every changed file and identify whether it was added, modified, or deleted. For 50+ files, group related files by directory. -->

| File | Change Type | Description |
|------|-------------|-------------|
| `path/to/file` | Added / Modified / Deleted | Brief description |

### Testing

<!-- Required: include automated tests, manual verification, and relevant CI results. State explicitly when a test was not run and why. -->

- Test or verification result

### Backward Compatibility

<!-- Required: describe impact on existing behavior, APIs, configuration, and migration. State "No breaking changes" when applicable. -->

- Compatibility notes

### Security Review

<!-- Required: tick every item that applies; write "N/A" after items that do not. The "Secure Code Review" bot comment on this PR lists automated findings (SEC-01..SEC-22). It is advisory and does not block merge, but explain any failed check under Security Notes. -->

- [ ] **Input Validation**: External input (CSV, YAML, CLI, API) validated with strict allowlists?
- [ ] **Secret Management**: No hardcoded secrets, Vault/tmpfs decrypt, credential files mode 0600? (SEC-01, SEC-08)
- [ ] **Path Security**: File paths validated, symlinks rejected, containment enforced? (SEC-15)
- [ ] **Command Injection**: No shell string interpolation, argv or `| quote` used? (SEC-04, SEC-05, SEC-09)
- [ ] **Template Injection**: No `include_vars` on operator-edited files, no unsafe Jinja lookups? (SEC-06)
- [ ] **Network / TLS**: TLS verification and SSH host-key checking enabled, no 0.0.0.0 without docs? (SEC-02, SEC-03, SEC-20)
- [ ] **Container / K8s**: SecurityContext set, no privileged/hostNetwork, images pinned by digest? (SEC-17, SEC-19)
- [ ] **Logging**: Secrets masked, `no_log` on credential tasks, exceptions logged not swallowed? (SEC-10, SEC-11, SEC-12)
- [ ] **Crypto / Tokens**: Approved algorithms, `secrets` for randomness, token TTL set? (SEC-21)
- [ ] **Dependencies**: Python packages pinned to exact versions? (SEC-18)
- [ ] **Permissions / Temp files**: No world-writable modes, secure temp files? (SEC-13, SEC-14)
- [ ] **Testing**: Security tests and negative/edge cases included?

**Security Notes:**
<!-- Document security considerations, mitigations, or exceptions (e.g. justified `# nosec`). Write "None" if not applicable. -->

### Suggested Reviewers

<!-- Required: identify reviewer names, teams, or roles and explain the relevant review area. -->

| Reviewer | Review Focus |
|----------|--------------|
| `@reviewer-or-team` | Component, domain, security, test, or compatibility focus |
