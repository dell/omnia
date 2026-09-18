# deploy_pulp

Deploys the Pulp container as a reboot-enabled Quadlet service with HTTPS only.

The user configures the host-facing port in
`repo_manager_endpoint_config.yml`. The role maps that port to the Pulp image's
built-in nginx listener on container port 443. The server certificate, private
key, persistent Django secret, and CLI configuration are stored below the
resolved Repo Manager runtime directory (`REPO_MANAGER_DATA_PATH`, or
`OMNIA_DATA_PATH/repo_manager`).

The role also renders a managed nginx proxy-timeout snippet below the resolved
settings directory and mounts it read-only at
`/etc/nginx/pulp/omnia_proxy_timeouts.conf`. Worker counts and the ordered
Gunicorn, nginx, and Repo Manager query timeouts are defined in
`vars/default.yml`; deployment preflight rejects an invalid timeout order.

An unchanged rerun preserves the certificate, secret, and administrator
password and does not restart the service. Configuration, port, image, or
certificate changes, including a changed timeout snippet, trigger a controlled
restart.
