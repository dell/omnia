# Defect Analysis: OMN-DEF #440 — Nodes boot with wrong hostname (nid000)

**Date:** 2026-09-04  
**Status:** Analysis complete, awaiting diagnostic confirmation  
**Affected code:** `src/orchestrator/roles/provision_common/`

---

## Symptoms

1. **Hostname:** Nodes boot with `nid000` instead of configured hostnames
2. **Password:** Provision password doesn't work for login (both publickey and password auth fail)

## Verified by Reporter

- Network connectivity OK — nodes are pingable and reachable to/from OIM
- SMD registration correct — MAC addresses properly registered with correct descriptions
- Boot-service working — correct boot scripts generated for right MAC addresses
- Coresmd-coredhcp cache cleared — not a cache issue
- PXE boot video shows correct station IP and OIM IP

## Architecture Overview

### Hostname Flow
```
hostname.yaml.j2 → hostname_<category>.yaml → POST /metadata-service/instanceinfos
  ↓
metadata-service stores: { instance_id: <xname>, hostname: <FQDN>, local_hostname: <FQDN> }
  ↓
Node boots → cloud-init → GET http://<OIM>:8081/metadata-service/meta-data
  ↓
HAProxy (:80, option forwardfor) → metadata-service (:8080)
  ↓
metadata-service: X-Forwarded-For IP → SMD lookup → xname → instanceinfo → hostname
```

### Password Flow
```
Provision password → openssl passwd -6 → hashed_password_output
  ↓
Two delivery mechanisms:
  1. FG-specific group templates (ms-group-<fg>.yaml.j2): users[].hashed_passwd
  2. Common group template (ms-group-common.yaml.j2): chpasswd.users[].password
  ↓
Both require metadata-service to identify the node's groups via SMD
```

### Fallback Hostname Generation
```
clusterdefaults: short_name="nid", nid_length=3
  → hostname = nid{NID:03d}
  → If NID=0 (default/unresolvable): hostname = nid000
```

Key files:
- `roles/deploy_openchami/tasks/deploy_openchami.yml` (line 90-91): `cluster_shortname: "nid"`, `cluster_nidlength: 3`
- `roles/configure_ochami/templates/metadata_svc/ms-defaults.yaml.j2`: renders these into clusterdefaults

## Root Cause Analysis

Both symptoms share a **single underlying cause**: the metadata-service cannot identify the booting node, so it returns default data without hostname overrides or group-specific cloud-init templates.

### Suspect 1 (MOST LIKELY): EthernetInterface IPs missing in SMD

**File:** `roles/provision_common/tasks/delete_smd_endpoints.yml` (lines 28-31)

```yaml
- name: Delete all ochami interfaces
  ansible.builtin.command: /usr/bin/ochami smd iface delete --no-confirm --all
```

This deletes ALL ethernet interfaces from SMD. Then `ochami discover static --overwrite` re-creates them from `nodes_<category>.yaml`.

**The problem:** The verification step (lines 238-248 in `register_nodes.yml`) only checks for **components**, not ethernet interface IPs:

```yaml
- name: Verify nodes registered in SMD
  ansible.builtin.shell: |
    set -o pipefail && \
    /usr/bin/ochami smd component get | jq '.Components[] | select(.Type == "Node")'
```

If `ochami discover static` creates components and MACs but does NOT re-create EthernetInterfaces with ADMIN_IP, the metadata-service can't map node IP → xname → instanceinfo/groups.

**Why this explains both symptoms:**
- No IP→xname mapping → metadata-service can't identify node
- Can't identify node → no instanceinfo → hostname falls back to `nid000` (NID=0 default)
- Can't identify node → no group membership → no group templates applied → no password config

**Evidence:**
- User verified "MAC addresses properly registered" — but did NOT verify IPs
- Boot-service uses MACs (not IPs) to match nodes → boot-service working doesn't prove IPs are registered
- `nid000` = NID 0, which should NEVER happen from the template (loop.index starts at 1)

### Suspect 2: Multi-category data deletion (cross-play data loss)

**File:** `roles/provision_common/tasks/delete_smd_endpoints.yml`

Each `provision_*.yml` playbook calls `provision_common`, which runs `delete_smd_endpoints.yml` deleting **ALL** endpoints (not scoped to the current category).

Execution order in `orchestrator.yml`:
1. `provision_kubernetes.yml` → delete ALL → register K8s nodes ✓
2. `provision_slurm.yml` → **delete ALL (including K8s data)** → register Slurm nodes ✓
3. `provision_os.yml` → **delete ALL (including Slurm data)** → register OS nodes ✓

After the last category, only that category's data survives. Previous categories' nodes have NO:
- Boot configurations
- Instanceinfos (hostnames)
- Metadata-service groups (passwords)
- SMD group memberships

**This bug exists even if it's not the primary cause of #440.** It would affect any deployment with multiple categories.

### Suspect 3: InstanceInfo ordering dependency

**File:** `roles/configure_ochami/tasks/configure_boot_svc_metadata_svc.yml` (lines 169-172)

```yaml
# Re-apply per-node hostname data after all defaults and group configs are set.
# The metadata-service stores data in-memory and the ordering matters:
# defaults/groups must be loaded before per-node instance overrides.
# This matches the reload order used in upgrade (reload_metadata_svc_data.yml).
```

In the current `provision_common` flow:
1. `register_nodes.yml` POSTs instanceinfos **BEFORE** clusterdefaults/groups are set
2. `main.yml` sets clusterdefaults and groups, then re-applies instanceinfos
3. Re-apply uses POST with `status_code: [200, 201, 409]` — gets **409 (conflict)** and does NOT update

If the metadata-service needs defaults loaded first for instanceinfos to properly override hostnames, the early instanceinfo (created before defaults) may be ineffective, and the re-apply silently fails to update it.

**Fix options:**
- Use PUT instead of POST for re-apply
- DELETE + POST for re-apply
- Remove the first POST from `register_nodes.yml`

## Diagnostic Commands (run on OIM)

```bash
# === CRITICAL: Check if EthernetInterfaces have IPs (Suspect 1) ===
ochami smd iface get | jq '.[].IPAddresses'
# Expected: Each interface should have an IP address
# If empty arrays → confirms Suspect 1

# === Check what metadata-service returns for a specific node IP ===
# Replace <NODE_ADMIN_IP> with the node's admin network IP
curl -s -H "X-Forwarded-For: <NODE_ADMIN_IP>" \
  http://localhost:8081/metadata-service/meta-data
# Expected: Should show correct hostname, instance_id, groups
# If shows nid000 or empty → metadata-service can't identify the node

# === Check instanceinfos exist in metadata-service ===
TOKEN=$(cat /etc/openchami/configs/access_token 2>/dev/null || echo "$OIM_ACCESS_TOKEN")
curl -sk -H "Authorization: Bearer $TOKEN" \
  https://$(hostname -f):8443/metadata-service/instanceinfos | jq '.[].spec'
# Expected: Each entry should have hostname, local_hostname, instance_id

# === Check clusterdefaults ===
curl -sk -H "Authorization: Bearer $TOKEN" \
  https://$(hostname -f):8443/metadata-service/clusterdefaultss | jq '.[].spec'
# Expected: cluster_name, short_name="nid", nid_length=3, base_url, public_keys

# === Check metadata-service groups ===
curl -sk -H "Authorization: Bearer $TOKEN" \
  https://$(hostname -f):8443/metadata-service/groups | jq '.[].metadata.name'
# Expected: ssh, chrony, phone_home, slurm_node_x86_64, etc.

# === Check SMD components have NIDs ===
ochami smd component get | jq '.Components[] | {ID: .ID, NID: .NID, Type: .Type}'
# Expected: Each Node should have NID > 0

# === Check SMD group membership ===
ochami smd group get | jq '.[] | {label: .label, members: .members.ids}'
# Expected: Each group should list xnames as members

# === Verify user-data and vendor-data ===
curl -s -H "X-Forwarded-For: <NODE_ADMIN_IP>" \
  http://localhost:8081/metadata-service/user-data
curl -s -H "X-Forwarded-For: <NODE_ADMIN_IP>" \
  http://localhost:8081/metadata-service/vendor-data
# user-data should have #cloud-config with users, chpasswd, write_files, runcmd
# vendor-data should reference group yaml files
```

## Key Files

| File | Purpose |
|------|---------|
| `roles/provision_common/tasks/main.yml` | Main provisioning pipeline (per category) |
| `roles/provision_common/tasks/register_nodes.yml` | SMD registration + instanceinfos POST |
| `roles/provision_common/tasks/delete_smd_endpoints.yml` | Deletes ALL SMD + metadata-service data |
| `roles/provision_common/tasks/configure_metadata_svc.yml` | Per-FG metadata-service group configuration |
| `roles/provision_common/tasks/configure_metadata_svc_common.yml` | Common group (ssh/chrony/phone_home) configuration |
| `roles/configure_ochami/templates/nodes/hostname.yaml.j2` | Hostname YAML generation template |
| `roles/configure_ochami/templates/nodes/nodes.yaml.j2` | Nodes YAML for SMD registration |
| `roles/configure_ochami/templates/metadata_svc/ms-defaults.yaml.j2` | ClusterDefaults template |
| `roles/configure_ochami/templates/metadata_svc/ms-group-common.yaml.j2` | Common group cloud-init (password in chpasswd) |
| `roles/configure_ochami/templates/metadata_svc/ms-group-*.yaml.j2` | FG-specific cloud-init (hashed_passwd in users) |
| `roles/configure_ochami/templates/boot_svc/boot-svc.yaml.j2` | Boot parameters (cloud-init datasource URL) |
| `roles/deploy_openchami/templates/haproxy.cfg.j2` | HAProxy config (X-Forwarded-For) |
| `roles/deploy_openchami/templates/metadata-service.yaml.j2` | Metadata-service config (smd_url, data_dir) |

## Proposed Fixes

### Fix for Suspect 1: Add EthernetInterface IP verification

In `register_nodes.yml`, after the SMD registration, add:

```yaml
- name: Verify EthernetInterfaces have IP addresses
  ansible.builtin.shell: |
    set -o pipefail && \
    /usr/bin/ochami smd iface get | jq -e '[.[] | select(.IPAddresses | length > 0)] | length > 0'
  register: iface_ip_check
  failed_when: iface_ip_check.rc != 0
  changed_when: false
```

### Fix for Suspect 2: Scope deletion to current category

In `delete_smd_endpoints.yml`, instead of deleting ALL endpoints, only delete endpoints for the current category's nodes.

### Fix for Suspect 3: Use DELETE+POST for instanceinfo re-apply

In `main.yml`, change the re-apply to delete existing instanceinfos first:

```yaml
- name: Delete existing instanceinfos before re-apply
  ansible.builtin.uri:
    url: "https://{{ cluster_name }}.{{ cluster_domain }}:8443/metadata-service/instanceinfos/{{ item.metadata.uid }}"
    method: DELETE
    headers:
      Authorization: "Bearer {{ ochami_env[(oim_node_name | upper) + '_ACCESS_TOKEN'] }}"
    status_code: [200, 204, 404]
    validate_certs: false
  loop: "{{ existing_instanceinfos_for_reapply.json | default([]) }}"
  # ... then POST with status_code: [200, 201]
```

## Additional Observations from Terminal Commands

The user's SSH attempts to `100.96.46.19` (likely a provisioned node) confirm:
1. SSH key auth fails (`/root/.ssh/oim_rsa` offered but rejected) — key wasn't delivered via cloud-init
2. Password auth fails — password wasn't set via cloud-init
3. The node IS running SSH (Ubuntu 24.04 based on `OpenSSH_9.6p1 Ubuntu-3ubuntu13.18`)
4. This confirms cloud-init did NOT apply the metadata-service group templates

---

*Generated with [Devin](https://devin.ai)*
