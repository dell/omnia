# discovery_setup

Bootstrap role that runs first (always-tagged) in the Discovery playbook and establishes the project context for every later play.

## What it does

- Validates the provided Ansible tags and tag combinations, and fails with a clear message on an invalid tag or combination.
- Sets the credential-skip flag for the `cleanup`, `validate`, and `precheck` routes so those routes never prompt for credentials.
- Resolves configuration from the environment and the Discovery data path (`DISCOVERY_DATA_PATH`, defaulting to `$OMNIA_DATA_PATH/discovery`), then derives the project input, output, and log paths.
- Verifies the project input directory, auto-copies the source input templates when the runtime input directory is missing, and ensures the runtime directories exist.
- Requires `discovery_config.yml` and loads it, then loads the common variables and marks setup complete.

## Variables

See `vars/main.yml` for the tag lists, messages, and path variables.

The internal `discovery_cleanup_mode=true` option is used only by the standalone cleanup playbook. Together with the `cleanup` and `cleanup_credentials` routes, it makes setup resolve the environment and project paths without validating or copying inputs, creating outputs, or loading `discovery_config.yml`.

## License

Apache-2.0
