# validate_discovery_input

Validates `discovery_config.yml` using the Discovery schema and cross-field
rules. Detailed validation output is written to
`<DISCOVERY_DATA_PATH>/log/<project>/discovery_validation_<project>.log`.

## Role Variables

- `input_project_dir`: Active Discovery input project directory.
- `discovery_schema_dir`: Directory containing the Discovery JSON schema.
- `log_dir`: Active Discovery project runtime-log directory, derived by
  `discovery_setup`.

## License

Apache-2.0
