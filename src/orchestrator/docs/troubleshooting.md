# Orchestrator -- Troubleshooting

## Common Issues

### 1. Project input directory or configuration is missing

```text
Required Orchestrator configuration was not found at .../orchestrator_config.yml
```

Run setup to stage the domain inputs, then edit the selected project:

```bash
cd src/main
sudo ./omnia.sh -s
source /etc/profile.d/omnia-env.sh
vi "$ORCHESTRATOR_DATA_PATH/input/$OMNIA_PROJECT_NAME/orchestrator_config.yml"
```

Setup initializes a missing project directory but never overwrites an existing
one. Restore individual missing files from `src/orchestrator/input/` when the
directory already exists.

---

### 2. PXE mapping file is missing or invalid

```text
pxe_mapping_file.csv not found
```

Confirm `pxe_mapping_file_path` and validate the staged file:

```bash
cd src/orchestrator/playbooks
ansible-playbook orchestrator.yml --tags validate
```

The file requires the exact 11-column header documented in the input contract.
Service Tags, admin/BMC MAC addresses, and admin/BMC IP addresses must be
populated and unique. Do not add an XNAME column.

---

### 3. Repository Manager status or certificate is missing

```text
Required Repo Manager output was not found
```

Run Repository Manager for the same project or correct
`repo_manager_output_path` in `orchestrator_config.yml`. The status must report
`overall_status: success`, contain supported repositories, and reference an
existing Pulp CA certificate when certificate data is present.

---

### 4. Image Build Manager status or boot artifact is unavailable

```text
image_build_manager output not found
```

Run Image Build Manager first and verify `image_build_manager_output_path`.
Every functional group used by the mapping must have kernel, initrd, and rootfs
paths. Orchestrator validates the complete artifact URLs before provisioning.

```bash
cd src/main
./omnia.sh --run image_build_manager --tags build
./omnia.sh --run orchestrator --tags precheck
```

---

### 5. Required catalog is missing or invalid

```text
Required catalog was not found
```

Run main setup to install the default catalog, set `CATALOG_FILE_PATH`, or set
`catalog_file_path` in `orchestrator_config.yml`. The catalog must contain
`catalog.groups`, `catalog.functionallayer`, `catalog.packages`, and base OS
metadata.

---

### 6. OpenCHAMI API authentication or TLS validation fails

Typical symptoms include HTTP 401/403 responses, certificate verification
errors, or failure of the `check_apis` action.

- Confirm the OpenCHAMI gateway and TokenSmith containers are healthy.
- Confirm the configured CA file exists and trusts the gateway certificate.
- Confirm the project token environment key matches the normalized OIM name.
- Rerun the deployment validation instead of disabling certificate checks.

```bash
cd src/orchestrator/playbooks
ansible-playbook orchestrator.yml --tags validate-deployment
systemctl status openchami.target
```

Do not pass JWT values on a command line or replace the CA with an insecure TLS
option.

---

### 7. Ansible cannot resolve an Orchestrator module

```text
couldn't resolve module/action 'omnia.orchestrator.openchami_reconcile'
```

Use the configured Omnia virtual environment and run from the domain playbook
directory so `ansible.cfg` loads the local module and module-utils paths:

```bash
source /etc/profile.d/omnia-env.sh
source "$OMNIA_VENV_PATH/bin/activate"
cd src/orchestrator/playbooks
ansible-playbook orchestrator.yml --syntax-check
```

For an installed collection, rebuild and reinstall the collection after source
changes before running through its FQCN.

---

### 8. Service Tag or network identity conflict

```text
SERVICE_TAG ... maps to multiple SMD XNAMEs
```

Identity reconciliation deliberately fails closed when a Service Tag, MAC, IP,
or existing SMD interface points to conflicting hardware. Compare the PXE mapping
with SMD Hardware Inventory and Ethernet interfaces. Correct the bad source
record deliberately; do not delete all Hardware Inventory to force allocation.

See [`hardware-identity-mapping.md`](hardware-identity-mapping.md) for the
identity and conflict rules.

---

### 9. Existing SMD nodes block new XNAME allocation

```text
SMD still has node components without Service Tag inventory
```

Orchestrator will not allocate over an existing unclaimed component. Ensure the
node's admin and BMC interfaces provide consistent evidence, or create the
correct Service Tag-to-XNAME Hardware Inventory binding under change control.
Rerun provisioning after the ambiguity is resolved.

---

### 10. Provision succeeds but reprovision_required remains true

This is expected when desired Metadata Service content changed. Provisioning
updates controller-side desired state but does not claim that a running node
has consumed it.

Run the PXE phase with node registration verification enabled. Only a fresh
boot with successful SSH and cloud-init verification clears
`reprovision_required` and sets `running_state_updated: true`.

---

### 11. Stale metadata group cannot be deleted

```text
Refusing to delete stale Metadata Service groups that still have SMD members
```

Move or remove the remaining nodes from the SMD group through the intended
functional-group change, then rerun provision. Orchestrator deletes only
Omnia-owned groups that are absent from desired state and have no SMD members.
Unmanaged groups are retained.

---

### 12. iDRAC is not ready or PXE boot fails

```text
Failed. iDRAC is not ready. Retry again after iDRAC is ready
```

Verify the BMC IP, credentials, network reachability, and iDRAC readiness.
PXE processing records the failed node and continues according to the playbook
strategy; it does not treat an unreachable BMC as a successful boot.

Review `pxeboot_status.yml` and `failed_nodes.json` before retrying the PXE tag.

---

### 13. Node registration or cloud-init verification fails

The node must be reachable over passwordless SSH, have `/usr/bin/python3` and
`/usr/bin/cloud-init`, report a boot newer than the PXE request, and complete
cloud-init without an unaccepted error.

On the affected node, inspect:

```bash
cloud-init status --long
journalctl -u cloud-init -u cloud-final --no-pager
cat /proc/uptime
```

The known OpenCHAMI empty user-data warning is accepted only when it is the sole
degraded condition. Other cloud-init errors or recoverable warnings fail node
verification.

---

### 14. OpenLDAP container does not become healthy

```bash
systemctl status omnia_auth.service
podman ps --all --filter name=omnia_auth
podman logs omnia_auth
```

Check the rendered Quadlet, mounted `slapd.conf`, bootstrap LDIF, certificates,
and persistence directory. After correcting configuration, reload systemd and
restart the service through the deployment workflow.

---

### 15. Cleanup removed credentials unexpectedly

Full cleanup removes the encrypted credential file and vault key by default.
To preserve them:

```bash
cd src/orchestrator/playbooks
ansible-playbook orchestrator.yml --tags cleanup \
  -e cleanup_credentials=false
```

The standalone `domain-init.sh --cleanup` helper removes staged input/log paths;
it does not replace component cleanup.

## Log Locations

| Log or report | Path |
|---------------|------|
| Top-level Ansible log | `/var/log/omnia/orchestrator/orchestrator.log` |
| Phase logs | `/var/log/omnia/orchestrator/{precheck,prepare,deploy,provision,pxeboot,validate,cleanup,upgrade,rollback}.log` |
| Domain logs | `<ORCHESTRATOR_DATA_PATH>/log/` |
| Provision report | `<ORCHESTRATOR_DATA_PATH>/output/<project>/provisioning_report.yml` |
| PXE report | `<ORCHESTRATOR_DATA_PATH>/output/<project>/pxeboot_status.yml` |
| Aggregate status | `<ORCHESTRATOR_DATA_PATH>/output/<project>/orchestrator_status.yml` |
| Failed-node view | `<ORCHESTRATOR_DATA_PATH>/output/<project>/failed_nodes.json` |

## Diagnostic Commands

```bash
# Validate inputs without contacting deployed services.
cd src/orchestrator/playbooks
ansible-playbook orchestrator.yml --tags validate

# Run environment, repository, image, and configuration prechecks.
ansible-playbook orchestrator.yml --tags precheck

# Validate deployed services.
ansible-playbook orchestrator.yml --tags validate-deployment

# Validate playbook/module loading without executing tasks.
ansible-playbook orchestrator.yml --syntax-check

# Inspect OpenCHAMI and OpenLDAP services.
systemctl status openchami.target
systemctl status omnia_auth.service
podman ps --all

# Inspect the latest lifecycle state.
python3 -m json.tool \
  "$ORCHESTRATOR_DATA_PATH/output/$OMNIA_PROJECT_NAME/failed_nodes.json"
```

Use `-vvv` only after checking the normal error and report files. Verbose
Ansible output may contain infrastructure details; protect logs accordingly.
