# Input Validation Ranges for Redfish Node Discovery

**Security Finding:** #2216806180  
**Component:** `src/orchestrator/plugins/modules/bulk_discover_node_specs.py`  
**Scope:** Input validation for hardware attributes (CERT_NONE/TLS issues addressed separately)

---

## Overview

This document provides the detailed justification for proposed input validation ranges for Redfish node discovery hardware attributes. The ranges are based on research across major server vendors (Dell, HPE, Lenovo) for 2024-2025 to ensure compatibility with legitimate hardware configurations worldwide while preventing malicious values.

---

## Proposed Validation Ranges

| Attribute | Type | Min | Max | Default (if invalid) |
|---|---|---:|---:|---|
| **Sockets** | int | 1 | 16 | 2 |
| **CoresPerSocket** | int | 1 | 160 | 72 |
| **ThreadsPerCore** | int | 1 | 2 | 1 |
| **RealMemory (MB)** | int | 8,192 | 8,000,000,000 (8TB) | 864,000 (864 GB) |
| **GPU count** | int | 0 | 16 | 0 |

---

## Detailed Justification by Attribute

### 1. Sockets

| Proposed | Min: 1 | Max: 16 |
|---|---:|---:|

**Vendor Research:**

| Vendor | Min Found | Max Found | Model Examples |
|---|---:|---:|---|
| **Dell** | 1 | 2 | R7615 (1-socket), R760/R7725 (2-socket) |
| **HPE** | 1 | 4 | DL345 Gen11 (1-socket), DL560 Gen10 (4-socket) |
| **Lenovo** | 1 | 2 | SR630 V4 (1-2 socket), SR675 V3 (2-socket) |
| **Scale-up** | 4 | 32 | HPE Scale-up 3200 (4-32 socket) |

**Justification for Max = 16:**
- Most standard rack servers are 1-2 socket
- 4-socket exists in enterprise servers (HPE DL560)
- Scale-up systems go up to 32 sockets (HPE Scale-up 3200), but these are multi-chassis shared-memory systems, not typical HPC nodes
- HPC nodes are almost always 1-2 socket
- Setting max to 16 provides headroom for future scale-up configurations while preventing absurd values like 100+ sockets

---

### 2. Cores per Socket

| Proposed | Min: 1 | Max: 160 |
|---|---:|---:|

**Vendor Research:**

| Vendor | Min Found | Max Found | Model Examples |
|---|---:|---:|---|
| **Dell** | 8 | 144 | R670: Intel Xeon 6 E-core up to 144 cores<br>R770: Intel Xeon 6 E-core up to 144 cores<br>R7615: AMD EPYC 9004 up to 128 cores |
| **HPE** | 8 | 144 | DL320 Gen12: Intel Xeon 6 E-core up to 144 cores<br>DL345 Gen11: AMD EPYC 9004 up to 128 cores |
| **Lenovo** | 8 | 144 | SR630 V4: Intel Xeon 6 E-core up to 144 cores<br>SR675 V3: AMD EPYC 9004/9005 up to 128 cores |

**Justification for Max = 160:**
- Current maximum across all vendors: 144 cores (Intel Xeon 6 E-core)
- AMD EPYC 9004/9005: up to 128 cores
- Setting max to 160 provides ~11% headroom for next-generation CPUs
- Prevents malicious values like 10,000 cores while covering all legitimate current and near-future hardware

**Justification for Min = 1:**
- Minimum found: 8 cores (low-end Intel Xeon 6 P-core models)
- However, edge/embedded servers or older generations could have single-core CPUs
- Setting min to 1 ensures compatibility with all possible configurations

---

### 3. Threads per Core

| Proposed | Min: 1 | Max: 2 |
|---|---:|---:|

**Vendor Research:**

| Vendor | Min Found | Max Found | Model Examples |
|---|---:|---:|---|
| **Dell** | 1 | 2 | All Intel Xeon and AMD EPYC processors support 1-2 threads per core (Hyper-Threading/SMT) |
| **HPE** | 1 | 2 | All Intel Xeon and AMD EPYC processors support 1-2 threads per core |
| **Lenovo** | 1 | 2 | All Intel Xeon and AMD EPYC processors support 1-2 threads per core |

**Justification for Max = 2:**
- Intel Hyper-Threading: 2 threads per core
- AMD SMT (Simultaneous Multithreading): 2 threads per core
- No mainstream x86 server CPU exceeds 2 threads per core
- This is a hard architectural limit for current server CPUs

**Justification for Min = 1:**
- CPUs can run with hyper-threading/SMT disabled (1 thread per core)
- This is the minimum valid configuration

---

### 4. RealMemory (in MB)

| Proposed | Min: 8,192 (8 GB) | Max: 8,000,000,000 (8 TB) |
|---|---:|---:|

**Vendor Research:**

| Vendor | Min Found | Max Found | Model Examples |
|---|---:|---:|---|
| **Dell** | 16 GB | 8 TB | R650: Up to 4TB<br>R7725: Up to 6TB<br>R770: Up to 8TB<br>R9825: Up to 8TB |
| **HPE** | 128 GB | 64 TB | DL380 Gen11: Up to 6TB<br>DL560 Gen10: Up to 6TB<br>Scale-up 3200: Up to 64TB shared (4-32 socket system) |
| **Lenovo** | 128 GB | 4 TB | SR650: Up to 4TB |

**Justification for Max = 8TB:**
- Maximum per-node memory in standard rack servers: 8TB (Dell R770, R9825)
- HPE Scale-up 3200 supports 64TB, but this is shared across 4-32 sockets in a multi-chassis system—not a single HPC node
- Setting max to 8TB covers all single-node configurations while preventing absurd values
- 8TB = 8,000,000,000 MB (Slurm uses MB as the unit for RealMemory)

**Justification for Min = 8GB:**
- Minimum found in current servers: 16GB (Dell R650)
- However, edge nodes, embedded systems, or older servers could have 8GB
- Setting min to 8GB ensures compatibility with small configurations
- 8GB = 8,192 MB

**Unit Conversion:**
- Redfish API returns memory in **GiB** (Gibibytes)
- Code converts GiB to **MB** (Megabytes) for Slurm compatibility: `MB = GiB * 1024 * 1.024`
- User-provided defaults are already in **MB** (Slurm format)
- Validation is performed in **MB** units

---

### 5. GPU Count

| Proposed | Min: 0 | Max: 16 |
|---|---:|---:|

**Vendor Research:**

| Vendor | Min Found | Max Found | Model Examples |
|---|---:|---:|---|
| **Dell** | 0 | 8 | R7725: Up to 8 GPUs (2x DW, 6x SW)<br>XE9680: 8 GPUs (NVIDIA H100/H200)<br>XE9640: 4 GPUs<br>R9825: Up to 8 GPUs |
| **HPE** | 0 | 8 | DL380 Gen11: Up to 8 NVIDIA GPUs |
| **Lenovo** | 0 | 8 | SR670 V2: 4-DW or 8-DW GPU models<br>SR675 V3: Up to 8 GPUs |

**Justification for Max = 16:**
- Maximum in current single-node servers: 8 GPUs (Dell XE9680, HPE DL380 Gen11, Lenovo SR670 V2)
- Dell IR7000 series supports up to 144 GPUs, but this is a multi-rack AI system, not a single node
- Setting max to 16 provides 2x headroom for future single-node GPU-rich servers
- Prevents malicious values like 1,000 GPUs

**Justification for Min = 0:**
- Many HPC nodes have no GPUs (CPU-only nodes)
- 0 is a valid and common configuration

---

## Summary Table: Proposed vs Vendor Actuals

| Attribute | Proposed Min | Vendor Min | Proposed Max | Vendor Max | Headroom |
|---|---:|---:|---:|---:|---:|
| Sockets | 1 | 1 | 16 | 4 (standard), 32 (scale-up) | 4x standard, covers scale-up edge cases |
| CoresPerSocket | 1 | 8 | 160 | 144 | ~11% headroom |
| ThreadsPerCore | 1 | 1 | 2 | 2 | Exact match (architectural limit) |
| RealMemory (MB) | 8,192 | 16,384 | 8,000,000,000 (8TB) | 8,000,000,000 (8TB) | Exact match for single-node |
| GPU count | 0 | 0 | 16 | 8 | 2x headroom |

---

## Additional Validation Rules

1. **Type validation:** All values must be integers (not bool, float, or string)
2. **Range validation:** Values must be within min-max bounds above
3. **Special character rejection:** Reject newlines, equals signs, and shell metacharacters in all fields
4. **Fallback behavior:** If a value fails validation, use the provided default and log a warning
5. **NodeName validation:** Must be a valid hostname (alphanumeric, hyphens, dots only)

---

## Key Design Principles

1. **Conservative upper bounds:** Max values are set based on actual vendor maximums with reasonable headroom (10-100%), not arbitrary large numbers
2. **Inclusive lower bounds:** Min values are set lower than current vendor minimums to accommodate edge cases, older hardware, and specialized configurations
3. **Future-proof:** Headroom is included for next-generation hardware (e.g., Intel Xeon 6, AMD EPYC 9005)
4. **Security-focused:** Bounds still reject obviously malicious values (negative, huge, non-numeric) that could break Slurm
5. **Vendor-agnostic:** Ranges cover Dell, HPE, Lenovo, and other major x86 server vendors

---

## References and Documentation

### Dell PowerEdge Servers

- [Dell PowerEdge Rack Servers Quick Reference Guide](https://www.content.shi.com/cms-content/accelerator/media/pdfs/dell/servers/dell-poweredge-rack-servers-032025.pdf)
- [Dell PowerEdge R7615 Technical Guide](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-r7615-technical-guide.pdf)
- [Dell PowerEdge R760 Technical Guide](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-r760-technical-guide.pdf)
- [Dell PowerEdge R760xd2 Technical Guide](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-r760xd2-technical-guide.pdf)
- [Dell PowerEdge R7725 Specification Sheet](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-r7725-spec-sheet.pdf)
- [Dell PowerEdge R770 Spec Sheet](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-r770-spec-sheet.pdf)
- [Dell PowerEdge R660 Technical Guide](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-r660-technical-guide.pdf)
- [Dell PowerEdge R760xs Technical Guide](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-r760xs-technical-guide.pdf)
- [Dell PowerEdge XE9680 Specification Sheet](https://www.dokmeha.com/wp-content/uploads/2025/02/poweredge-xe9680-spec-sheet_Dokmeha.pdf)
- [Dell PowerEdge XE9640 Specification Sheet](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe9640-spec-sheet.pdf)
- [Dell PowerEdge Server GPU Matrix](https://www.delltechnologies.com/asset/fi-fi/products/servers/briefs-summaries/poweredge-server-gpu-matrix.pdf)
- [Dell PowerEdge Data Center Compute Servers](https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/poweredge-datacenter-servers)
- [Dell PowerEdge AI Acceleration Announcements at NVIDIA GTC](https://www.dell.com/en-us/blog/dell-poweredge-xe9680-ai-acceleration-announcements-at-nvidia-gtc/)
- [Dell PowerEdge Server and Networking Announcements at NVIDIA GTC 2025](https://www.dell.com/en-ie/blog/poweredge-server-and-networking-announcements-at-nvidia-gtc-2025/)

### HPE ProLiant Servers

- [HPE ProLiant Compute](https://www.hpe.com/int/en/products/compute/proliant.html)
- [HPE ProLiant DL320 Gen12 QuickSpecs](https://www.hpe.com/us/en/collaterals/collateral.a50004283enw.html)
- [HPE ProLiant DL345 Gen11](https://cdn.blueally.com/servercomputeworks/datasheets/gen11-servers/hpe_proliant_dl345_gen11-quickspec-05-2024.pdf)
- [HPE ProLiant DL560 Gen10 Server Data Sheet](https://www.fsys.ch/wp-content/uploads/2024/04/HPE-ProLiant-DL560-Gen10-server-PSN1010026837UKEN.pdf)
- [HPE Compute Scale-up Server 3200 QuickSpecs](https://www.hpe.com/us/en/collaterals/collateral.a50004268enw.html)
- [HPE introduces next-generation ProLiant servers](https://www.hpe.com/us/en/newsroom/press-release/2025/02/hpe-introduces-next-generation-proliant-servers-engineered-for-advanced-security-ai-automation-and-greater-performance.html)
- [TPCx-AI 2.0.0 HPE Report - ProLiant DL380 Gen11](https://www.tpc.org/results/individual_results/HPE/hpe~tpcxai~100~hpe_proliant_dl380_gen11~es~2025-03-13~v02.pdf)

### Lenovo ThinkSystem Servers

- [Lenovo ThinkSystem SR630 V4 Technical Specifications](https://pubs.lenovo.com/sr630-v4/server_specifications_technical)
- [Lenovo ThinkSystem SR630 V4 Server Product Guide](https://lenovopress.lenovo.com/lp1971-thinksystem-sr630-v4-server)
- [Lenovo ThinkSystem SR850 V4 Server Product Guide](https://lenovopress.lenovo.com/lp2230-thinksystem-sr850-v4-server)
- [Lenovo ThinkSystem SR675 V3 Technical Specifications](https://pubs.lenovo.com/sr675-v3/server_specifications_technical)
- [Lenovo ThinkSystem Servers with 5th Gen AMD EPYC "Turin" Processors](https://lenovopress.lenovo.com/lp2038-lenovo-thinksystem-servers-with-5th-gen-amd-epyc)
- [Lenovo ThinkSystem SR670 V2 4-DW GPU Model / 8-DW GPU Model Specification](https://pubs.lenovo.com/sr670-v2/server_specifications_pcie_gpu_model)
- [Lenovo ThinkSystem SR675 V3 Datasheet](https://techtoday.lenovo.com/sites/default/files/2025-09/ThinkSystem-SR675-V3-Datasheet.pdf)

### Additional Comparisons

- [Technical Comparison: Dell PowerEdge R750, HPE ProLiant DL380 Gen10 and Lenovo ThinkSystem SR650 Servers](https://www.server-parts.eu/post/dell-poweredge-r750-hpe-proliant-dl380-gen10-lenovo-thinksystem-sr650-server-comparison)
- [Server Data Sheets: Dell, HPE & Lenovo](https://www.servnetuk.com/datasheet)
- [Compare Dell PowerEdge & HPE ProLiant Servers](https://newserverlife.com/articles/guide-to-dell-and-hpe-servers-features-use-cases-and-best-models)
- [HPE, Dell, Lenovo, and Supermicro detail new server offerings featuring AMD's new MI325X GPUs and Epyc CPUs](https://www.datacenterdynamics.com/en/news/hpe-dell-lenovo-and-supermicro-detail-new-server-offerings-featuring-amds-new-mi325x-gpus-and-epyc-cpus)

---

## Implementation Approach

The validation will be applied in both discovery modes:

1. **Heterogeneous mode (`_discover_single_node`):** Validate each node's discovered attributes before building `node_params`
2. **Homogeneous mode (`_discover_group`):** Validate the sample node's discovered attributes before replicating to the group

Validation failures will:
- Log a warning with the hostname, attribute name, invalid value, and reason
- Use the provided default value from the `defaults` parameter
- Continue discovery (soft failure) to avoid blocking entire cluster provisioning
- Optionally add the node to `failed_nodes` if strict mode is enabled

---

## Contact

For questions or adjustments to these ranges, please contact the Omnia security team.
