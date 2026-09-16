# Discovery precheck environment role

## Overview

Performs non-mutating prerequisite checks for Discovery. The role runs only
when the Discovery entry point is called with `--tags precheck`. It does not
read credentials, authenticate to OME, call the OME API, or modify system
configuration.

## Checks

- Reports whether `/etc/omnia/omnia.env` is installed. A missing file is a
  warning because Discovery also supports an explicitly exported environment.
- Validates the resolved `DISCOVERY_DATA_PATH` without creating it. The
  component path defaults to `$OMNIA_DATA_PATH/discovery`.
- Verifies that the configured OME IP is reachable from the OIM host on TCP
  port 443.
- Displays the resolved Discovery project and a consolidated result.

## Usage

```bash
cd src/discovery/playbooks
ansible-playbook discovery.yml --tags precheck
```

`discovery_setup` runs first with the `always` tag and supplies the resolved
data path, project, and configuration facts used by this role. Setup may create
the runtime project directories and copy default inputs when they do not yet
exist; the precheck role itself does not write to them.

## License

Apache-2.0
