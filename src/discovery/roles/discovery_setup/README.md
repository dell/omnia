# discovery_setup

Ansible role for the Omnia discovery collection.

## Role Variables

See `vars/main.yml` and `defaults/main.yml` for available variables.

The internal `discovery_cleanup_mode=true` option is used only by the
standalone cleanup playbook. Together with the `cleanup` and
`cleanup_credentials` routes, it makes setup resolve the environment and
project paths without validating or copying inputs, creating outputs, or
loading `discovery_config.yml`.

## License

Apache-2.0
