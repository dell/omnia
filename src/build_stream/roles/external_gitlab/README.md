# external_gitlab

## Description

Configures BuildStream CI/CD against a customer-managed (external) GitLab
instance (`gitlab_mode: external`, ER-BSM-003). The role runs on the OIM
(`localhost`) and talks to the GitLab REST API only. It does not install GitLab
and does not deploy or register a runner: the operator provides a pre-registered
runner that is online for the project.

## What it does

1. Validates the custom CA bundle (if any), connectivity (3 attempts, 5s/15s/45s),
   GitLab version (17.x-19.x), PAT scopes (`api`, `write_repository`) and the
   token user's Owner/Maintainer role on the namespace.
2. Creates the project with the `managed-by:omnia-buildstream` marker, or adopts a
   marked project. A same-named project without the marker fails closed.
3. Protects the default branch, verifies an online runner, creates the `omnia-ci`
   project access token and the pipeline trigger, and sets the CI/CD variables.
4. Pushes the CI templates, `omnia.env`, input files and sample catalogs.
5. Records every resource ID (never secret values) in
   `<OMNIA_DATA_PATH>/build_stream/output/<project>/external_gitlab_journal.json`
   (root:0600, atomic writes). On failure, resources created in the run are rolled
   back in reverse order; adopted projects are never deleted.

## Inputs

`build_stream_config.yml`: `gitlab_mode`, `gitlab_external_url`,
`gitlab_project_namespace`, `gitlab_ca_cert_path`, `gitlab_project_name`,
`gitlab_project_visibility`, `gitlab_default_branch`, `gitlab_project_ci_timeout`.
`build_stream_credentials.yml` (Vault): `gitlab_api_token`.

## Requirements

- Ansible >= 2.14, Python >= 3.9
- GitLab CE/EE 17.x-19.x reachable over HTTPS from the OIM

## Dependencies

None. Shared CI templates are read from the `hosted_gitlab` role files.

## License

Apache-2.0
