# discovery_common

Shared task-library role for the Omnia Discovery collection. Include a
specific task file with `ansible.builtin.include_role` and `tasks_from`; do not
invoke this role as a standalone workflow.

## Available Tasks

- `decrypt_include_encrypt.yml`: decrypt, load, and re-encrypt a Discovery
  credential file.
- `check_ome_connectivity.yml`: validate that `ome_ip` is configured and wait
  for its HTTPS TCP endpoint. This performs no authentication, TLS certificate
  validation, or OME API request.

## Role Variables

Connection timeouts have role defaults in `defaults/main.yml`. The fixed OME
HTTPS port, internal status, and error messages are defined in `vars/main.yml`.
The port is not a user input because the OME inventory client uses the standard
HTTPS endpoint on port 443.

| Variable | Default | Purpose |
|----------|---------|---------|
| `discovery_ome_connect_timeout` | `5` | Timeout for each TCP connection attempt, in seconds |
| `discovery_ome_connectivity_timeout` | `30` | Maximum time to wait for the OME endpoint, in seconds |

## License

Apache-2.0
