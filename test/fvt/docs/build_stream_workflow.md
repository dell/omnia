# Omnia Deployment Workflow with Build Stream

## Complete Omnia Deployment Flow

This document describes the complete Omnia deployment workflow including the updated build_stream integration with automatic triggering and aarch64 OS installation support.

## Full Workflow Diagram

```
                                ┌─────────────────────┐
                                │   Start Omnia       │
                                │   Deployment        │
                                └──────────┬──────────┘
                                           │
                                           ▼
                                ┌─────────────────────┐
                                │ aarch64 OS Install  │
                                │ (if user chooses)   │
                                │ ┌─────────────────┐ │
                                │ │ Check if user   │ │
                                │ │ has aarch64     │ │
                                │ │ requirement     │ │
                                │ └─────────────────┘ │
                                └──────────┬──────────┘
                                           │
                                           ▼
                    ┌─────────────────────────────────────────────┐
                    │        Build Omnia Project from             │
                    │      Omnia artifactory repo:               │
                    │   https://github.com/dell/omnia/           │
                    │   artifactory-omnia-container              │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │    Run the omnia.sh script to create the   │
                    │         Omnia core container               │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │      Log in to the Omnia core container    │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │    Update the input.yml file in            │
                    │  /opt/omnia/input/project_default directory │
                    │  depending on Service K8S, Slurm, BuildStream, │
                    │  Telemetry, Discovery, Storage              │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ Create PXE      │◄──────┐
                              │ mapping file    │       │
                              │ manually        │       │
                              └─────────┬───────┘       │
                                        │               │
                                        ▼               │
                              ┌─────────────────┐       │
                              │ Generate PXE    │       │
                              │ mapping using   │       │
                              │ BMC Discovery   │       │
                              │ using discovery.yml │   │
                              └─────────┬───────┘       │
                                        │               │
                                        ▼               │
                              ┌─────────────────┐       │
                              │ Run input       │       │
                              │ validation to   │       │
                              │ validate the    │       │
                              │ input files     │       │
                              └─────────┬───────┘       │
                                        │               │
                                        └───────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │              Build Stream Flow              │
                    │         (if BuildStream enabled)           │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                         ┌─────────────────────────┐      ┌─────────────────────────┐
                         │   Update Catalog and    │ Yes  │   Run playbook.yml to   │
                         │   Trigger Build         │─────▶│   deploy the BuildStream│
                         │   Pipeline Automatically│      │   on instance           │
                         └─────────────────────────┘      └───────────┬─────────────┘
                                       │                              │
                                    No │                              ▼
                                       │                  ┌─────────────────────────┐
                                       │                  │   Run phase.yml to      │
                                       │                  │   deploy the BuildStream│
                                       │                  │   GitLab instance       │
                                       │                  └───────────┬─────────────┘
                                       │                              │
                                       │                              ▼
                                       │                  ┌─────────────────────────┐
                                       │                  │   Update the catalog to │
                                       │                  │   the BuildStream GitLab│
                                       │                  │   instance              │
                                       │                  └───────────┬─────────────┘
                                       │                              │
                                       │                              ▼
                                       │                  ┌─────────────────────────┐
                                       │                  │   Automated GitLab      │
                                       │                  │   CI/CD Pipeline        │
                                       │                  └───────────┬─────────────┘
                                       │                              │
                                       │                              ▼
                                       │                  ┌─────────────────────────┐
                                       │                  │   Update PXE mapping    │
                                       │                  │   file and trigger      │
                                       │                  │   Deploy Pipeline       │
                                       │                  └───────────┬─────────────┘
                                       │                              │
                                       │                              ▼
                                       │                  ┌─────────────────────────┐
                                       │                  │   Run Telemetry         │
                                       │                  │   Directly              │
                                       │                  │   (No PXE boot in       │
                                       │                  │   build_stream flow)    │
                                       │                  └───────────┬─────────────┘
                                       │                              │
                                       └──────────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │              Regular Flow                   │
                    │         (Non-BuildStream)                  │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │   Run provision.yml playbook to deploy the │
                    │   containers on OIM                         │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │   First boot the nodes' device images from │
                    │   Pulp repository                           │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │   Run telemetry.yml playbook to enable     │
                    │   DCGM telemetry                           │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │              End of deployment              │
                    └─────────────────────────────────────────────┘
```

## Key Changes in Updated Workflow

### 1. **aarch64 OS Installation Moved to Top**
- aarch64 OS installation check is now at the beginning of the workflow
- User can choose to install aarch64 OS if they have the requirement
- This happens before any other Omnia deployment steps

### 2. **Build Stream Flow Changes**
- **Catalog Update**: Automatically triggers build pipeline via GitLab webhook
- **PXE Mapping Update**: Automatically triggers deploy pipeline via GitLab webhook  
- **No PXE Boot**: PXE boot is handled by deploy pipeline, not build_stream
- **Direct to Telemetry**: After deploy pipeline, flow goes directly to telemetry

### 3. **Automatic Pipeline Triggering**
- Build Pipeline: Triggered by catalog file commit to GitLab
- Deploy Pipeline: Triggered by PXE mapping file commit to GitLab
- No manual intervention required between pipelines

## Configuration Details

### aarch64 OS Installation Configuration

```yaml
# omnia_test_config.yml - Top Level Configuration
# ================================================
# OS Installation Architecture Options (moved to top)
install_os_arch:
  - x86_64    # Always included (default)
  - aarch64   # Optional - add if user has aarch64 requirement

# build_stream_config.yml - BuildStream Specific
# ==============================================
# AArch64 inventory host (required for aarch64 builds)
aarch64_inventory_host_ip: "192.168.1.100"  # Admin IP where aarch64 OS is installed
```

### Build Stream Pipeline Configuration

```yaml
# build_stream_config.yml
enable_build_stream: true
build_stream_host_ip: "<OIM_IP>"
build_stream_port: 8010

# GitLab Configuration for Automatic Triggering
gitlab_config:
  webhook_enabled: true
  catalog_trigger: true    # Catalog commit → Build Pipeline
  pxe_trigger: true       # PXE mapping commit → Deploy Pipeline
```

## Detailed Pipeline Flows

### Build Pipeline (Automated via Catalog Update)

```
┌─────────────────────────────────────────────────────────────────┐
│                     BUILD PIPELINE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. TRIGGER: CATALOG UPDATE                                     │
│     ├─ User/System updates catalog file                        │
│     ├─ Commit pushed to GitLab repository                      │
│     ├─ GitLab webhook automatically triggers build pipeline    │
│     └─ Pipeline ID generated and tracked in database           │
│                                                                 │
│  2. BUILD STAGES (Sequential Execution)                        │
│     ├─ upload           (upload catalog to build system)       │
│     ├─ parse-catalog    (parse roles and architectures)        │
│     ├─ generate-input-files (create input configurations)      │
│     ├─ create-local-repository (setup local package repo)      │
│     ├─ build-image-x86_64 (always executed)                   │
│     └─ build-image-aarch64 (conditional - if aarch64 enabled)  │
│                                                                 │
│  3. OUTPUT ARTIFACTS                                           │
│     ├─ Container images → Registry (Harbor/Docker)             │
│     ├─ Boot images (rootfs + EFI) → S3 Storage                │
│     ├─ Image groups → PostgreSQL Database                     │
│     └─ Build metadata → Database for tracking                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Deploy Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     DEPLOY PIPELINE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. PXE MAPPING UPDATE                                         │
│     ├─ Update PXE mapping file columns                        │
│     ├─ Commit changes to GitLab                               │
│     └─ GitLab webhook triggers deploy pipeline automatically   │
│                                                                 │
│  2. DEPLOY STAGES (Sequential)                                 │
│     ├─ validate-images                                        │
│     ├─ update-pxe-mapping                                     │
│     └─ deploy-nodes                                           │
│                                                                 │
│  3. OUTPUT                                                     │
│     ├─ Nodes PXE booted with new images                       │
│     ├─ PXE mapping updated in database                        │
│     └─ Deployment status recorded                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4. Post-Deploy Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   POST-DEPLOY FLOW                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │  Deploy         │───▶│  Run Telemetry  │                    │
│  │  Complete       │    │  Directly       │                    │
│  └─────────────────┘    └─────────────────┘                    │
│           │                       │                            │
│           ▼                       ▼                            │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │  Nodes Ready    │    │  Metrics        │                    │
│  │  (PXE Booted)   │    │  Collected      │                    │
│  └─────────────────┘    └─────────────────┘                    │
│                                                                 │
│  NOTE: PXE boot is NOT part of build_stream flow               │
│        - Handled by deploy pipeline                            │
│        - Build stream focuses on image building only           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Key Changes from Previous Flow

### 1. Removed from Build Stream
- ❌ PXE boot operations (moved to deploy pipeline)
- ❌ Manual pipeline triggering (now automatic via webhooks)

### 2. Added to Build Stream
- ✅ Automatic catalog update → triggers build pipeline
- ✅ aarch64 OS installation option in common block
- ✅ Conditional aarch64 build stage

### 3. Enhanced Deploy Pipeline
- ✅ PXE mapping file update → triggers deploy pipeline
- ✅ Automatic pipeline triggering via GitLab webhooks
- ✅ Direct flow to telemetry after deploy

### 4. Configuration Structure

```yaml
# build_stream_config.yml
enable_build_stream: true
build_stream_host_ip: "<OIM_IP>"
build_stream_port: 8010
aarch64_inventory_host_ip: "<AArch64_HOST_IP>"  # Optional

# omnia_test_config.yml
install_os_arch:
  - x86_64    # Always included
  - aarch64   # Optional, requires aarch64_inventory_host_ip
```

## Implementation Notes

### aarch64 Support
- aarch64 builds are conditional based on `aarch64_inventory_host_ip`
- When set, aarch64 stage is added to build pipeline
- Requires aarch64 host with OS pre-installed
- Build images stored in registry with aarch64 tags

### Automatic Triggering
- Catalog file commit → GitLab webhook → build pipeline
- PXE mapping commit → GitLab webhook → deploy pipeline
- No manual intervention required after initial setup

### Database Tracking
- All stages tracked in PostgreSQL database
- Job IDs link build and deploy pipelines
- Stage states: PENDING, RUNNING, COMPLETED, FAILED

### Error Handling
- Failed stages stop subsequent stages in same pipeline
- Deploy pipeline waits for build pipeline completion
- Telemetry runs only after successful deploy

## Flow Decision Tree

```
┌─────────────────────────────────────────┐
│         Start Build Stream              │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│    Is aarch64_inventory_host_ip set?    │
└─────────────────┬───────────────────────┘
                  │
         Yes ┌────┴────┐ No
              ▼         ▼
┌─────────────────┐ ┌─────────────────┐
│ Include aarch64 │ │ x86_64 only     │
│ in build stages │ │ build stages    │
└─────────────────┘ └─────────────────┘
         │                   │
         └───────┬───────────┘
                 ▼
┌─────────────────────────────────────────┐
│    Upload catalog to GitLab            │
│    (triggers build pipeline)           │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│    Build Pipeline Runs                  │
│    (all stages sequential)              │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│    Update PXE mapping file              │
│    (triggers deploy pipeline)           │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│    Deploy Pipeline Runs                 │
│    (includes PXE boot)                  │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│    Run Telemetry Directly               │
└─────────────────────────────────────────┘
```
