# Orchestrator -- Hardware Identity Mapping

**Domain**: `orchestrator` | **Collection**: `omnia.orchestrator`

This document defines how Orchestrator assigns a permanent OpenCHAMI XNAME to
each physical server, reconciles mutable node configuration, and reports when a
new PXE boot is required.

---

## 1. Identity Contract

The PXE mapping file identifies physical hardware by `SERVICE_TAG`. Users do
not provide XNAME values. Orchestrator resolves and persists this relationship:

```text
SERVICE_TAG -> permanent Node XNAME
```

The mapping is stored in SMD Hardware Inventory as the node's FRU serial
number. For example:

```json
{
  "ID": "x1000c0s0b0n0",
  "PopulatedFRU": {
    "NodeFRUInfo": {
      "SerialNumber": "EXAMPLE01"
    }
  }
}
```

SMD is the persistent authority. No separate Omnia database, database account,
or password is required.

## 2. Current Identity Model

Users provide the physical server Service Tag, not an XNAME. Orchestrator
allocates an internal XNAME only when the Service Tag has no persistent SMD
binding. Every later run reuses the stored relationship.

CSV order is not part of node identity. Rows may be reordered, or a new row may
be inserted, without changing XNAMEs already assigned to other servers.

## 3. System Context

```text
 pxe_mapping_file.csv
 SERVICE_TAG, hostname, role, MACs, IPs
                  |
                  v
       +--------------------------+
       | openchami_reconcile      |
       |                          |
       | validate input           |
       | resolve permanent XNAME  |
       | reject conflicts         |
       +------------+-------------+
                    |
          +---------+----------+
          |                    |
          v                    v
 +------------------+  +------------------+
 | SMD              |  | Metadata Service |
 | hardware identity|  | hostname/config  |
 | components       |  | groups/defaults  |
 | interfaces/groups|  | instance info    |
 +--------+---------+  +---------+--------+
          |                      |
          +----------+-----------+
                     v
             Boot Service and PXE
```

All OpenCHAMI requests made by the reconciliation module use a TokenSmith JWT
and validate the gateway TLS certificate with the configured CA certificate.

## 4. Resolution Flow

For every PXE mapping row, Orchestrator performs the following sequence:

1. Normalize and validate the Service Tag, admin/BMC MAC addresses, and IP
   addresses.
2. Reject duplicate Service Tags, MAC addresses, or IP addresses in the input.
3. Read SMD components, Ethernet interfaces, and Hardware Inventory.
4. Reuse the XNAME when exactly one Hardware Inventory record contains the
   Service Tag.
5. For an existing SMD node without a Hardware Inventory binding, preserve its
   XNAME only when the admin and BMC interfaces provide consistent evidence.
6. Refuse new allocation while ambiguous, unclaimed SMD node components exist.
7. Otherwise allocate the first free Node/NodeBMC XNAME pair.
8. Persist the Service Tag in SMD Hardware Inventory and read it back.
9. Validate that the requested MAC addresses and IP addresses do not belong to
   a different XNAME.
10. Publish the resolved XNAME to discovery, groups, Metadata Service, Boot
    Service, validation, reporting, and PXE boot tasks.

The source CSV remains unchanged. Its normalized temporary copy is used for
input cleanup and functional-group normalization; no XNAME is added to it.

## 5. XNAME Allocation

New nodes retain the established Omnia numbering format:

```text
x1000c<c>s<s>b<b>n0
```

Allocation begins at index zero and selects the first pair for which both the
Node XNAME and its parent NodeBMC XNAME are unused. For example, the Node
`x1000c0s0b0n0` uses parent NodeBMC `x1000c0s0b0`.

Allocation is ordered by normalized Service Tag instead of CSV position. A
root-owned `0600` lock file serializes allocation on the OIM host so concurrent
runs cannot select the same free XNAME.

## 6. Conflict Handling

Identity reconciliation fails before discovery when any of these conditions is
detected:

| Conflict | Behavior |
|----------|----------|
| Duplicate Service Tag in the PXE mapping | Reject the input |
| One Service Tag mapped to multiple SMD XNAMEs | Fail closed |
| Multiple PXE rows resolving to one XNAME | Fail closed |
| Admin or BMC MAC owned by another XNAME | Fail closed |
| Admin or BMC IP owned by another XNAME | Fail closed |
| Ambiguous SMD nodes without Service Tags | Stop new allocation |
| SMD write does not read back as one unique binding | Fail reconciliation |

Check mode calculates and returns planned mappings without changing SMD.

## 7. Mutable Node Configuration

Service Tag and XNAME define physical identity. The remaining PXE mapping
fields describe desired configuration and may change independently.

| User change | Identity result | Reconciliation result |
|-------------|-----------------|-----------------------|
| Reorder rows | XNAME retained | No identity write |
| Insert a new row | Existing XNAMEs retained | Allocate one new free XNAME |
| Change hostname | XNAME retained | Update InstanceInfo in place |
| Change functional group | XNAME retained | Reconcile SMD membership, metadata, and boot configuration |
| Change admin or BMC IP | XNAME retained | Rediscover the interface after ownership validation |
| Replace admin or BMC NIC | XNAME retained | Remove the component-owned stale interface and discover the new MAC |
| Remove a row | Existing SMD identity retained | No automatic identity deletion |
| Change Service Tag | Treated as different hardware | Allocate or bootstrap another identity; corrections require a controlled identity update |

Retaining identity for an absent row prevents temporary inventory omissions
from silently releasing an XNAME for reuse.

## 8. Metadata Reconciliation

Orchestrator reconciles Metadata Service resources through the same verified
API client instead of deleting and recreating every resource.

- InstanceInfo is keyed by XNAME and updated in place by UID.
- Metadata groups and ClusterDefaults receive Omnia ownership labels containing
  the project name.
- Existing matching resources can be adopted by adding ownership labels.
- Duplicate InstanceInfo and ClusterDefaults resources are reduced to one
  canonical resource.
- A stale Omnia-owned metadata group is deleted only when it is absent from the
  complete desired configuration and has no SMD members.
- Unmanaged metadata groups are retained.

The ownership boundary prevents one project from garbage-collecting resources
that it does not manage.

## 9. Provision and PXE State

Provisioning records desired-state changes in `orchestrator_status.yml`:

| Field | Meaning |
|-------|---------|
| `identity_changed` | The run created the persistent Service Tag-to-XNAME binding |
| `metadata_changed` | Desired metadata differs from the last verified node application |
| `running_state_updated` | PXE and node verification confirmed the desired state was applied |
| `reprovision_required` | A successful verified PXE boot is still required |

A repeated provision run preserves an existing `reprovision_required: true`
state even when reconciliation is otherwise idempotent. Provisioning alone does
not claim that a running node consumed new metadata.

After PXE boot, passwordless SSH, boot freshness, and cloud-init completion are
verified on the node. A successful verified boot clears `metadata_changed` and
`reprovision_required` and sets `running_state_updated: true`. Disabling
verification or manually booting a node does not automatically prove that the
desired runtime state was applied.

## 10. Security and Recovery

- The API client requires HTTPS, a trusted CA certificate, and a TokenSmith JWT.
- Tokens and credential-bearing tasks use Ansible `no_log` protection.
- API response bodies are size-limited and all requests use finite timeouts.
- Automatic retries are restricted to safe HTTP methods.
- Static discovery uses a fixed subprocess argument list without a shell.
- Identity allocation validates lock-file type, ownership, and permissions.
- Hardware Inventory is preserved during category-scoped discovery cleanup.
- Metadata containing credentials or private keys is written with root-only
  permissions.

If reconciliation reports an identity conflict, correct the PXE mapping or SMD
record deliberately. Do not delete Hardware Inventory merely to force a new
XNAME: the persistent binding protects running-cluster identity.

## 11. Interfaces and Consumers

| Interface | Purpose |
|-----------|---------|
| `pxe_mapping_file.csv` | User/discovery-owned desired hardware and configuration input |
| SMD Hardware Inventory | Persistent Service Tag-to-XNAME registry |
| SMD Components and Interfaces | Current discovered node and network topology |
| SMD Groups | Functional and common group membership |
| Metadata Service | Hostname, cloud-init, group, and cluster-default data |
| Boot Service | Functional-group boot artifacts and node boot configuration |
| `orchestrator_status.yml` | Persistent provision/PXE application status |

Input columns are defined in
[`contracts/input-contract.md`](contracts/input-contract.md). Output and status
fields are defined in
[`contracts/output-contract.md`](contracts/output-contract.md).

## 12. Validation Coverage

The implementation has been exercised for initial registration, repeated
provisioning, row reordering, hostname changes, functional-group changes,
restoration of the original mapping, metadata reconciliation, PXE verification,
and API readback. Negative conflict and large-scale concurrency cases should be
covered by automated test infrastructure rather than embedded live-cluster data
in this maintained architecture document.
