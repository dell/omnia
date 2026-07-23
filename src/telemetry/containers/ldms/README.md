# ldms

OVIS LDMS aggregator container (Ubuntu 26.04). Multi-stage build: compiles
libserdes and OVIS LDMS from source, then copies into a slim runner image.

Runs as the LDMS aggregator pod on the service K8s cluster. Compute-node
samplers (embedded RPM) push metrics to this aggregator, which then writes to
VictoriaMetrics.

## Files

| File | Purpose |
|------|---------|
| `Containerfile.bld_n_run.ubuntu26.04` | Multi-stage Containerfile: builds LDMS from source, creates slim runner |
| `configure.aggregator.sh` | Configure script for OVIS LDMS compilation with all required features |
| `README.md` | This file |

## File Details

### Containerfile.bld_n_run.ubuntu26.04
- Multi-stage build:
  - **Builder stage**: Compiles libserdes and OVIS LDMS from source (v4.5.2)
  - **Runner stage**: Slim Ubuntu 26.04 image with compiled binaries copied over
- Uses configure.aggregator.sh during build to enable all LDMS features
- Final image contains only runtime dependencies

### configure.aggregator.sh
- Configure script for OVIS LDMS compilation
- Enables all required features:
  - Slurm integration (--with-slurm, --enable-slurm, --enable-spank-plugin)
  - InfluxDB output (--enable-influx)
  - Kafka storage (--enable-store-avro-kafka)
  - Job info sampler (--enable-jobinfo-sampler)
  - Various HPC fabric support (lustre, infiniband, etc.)
  - Documentation generation (--enable-doc, --enable-doc-html, --enable-doc-man)
- Installs to `/opt/ovis-ldms`

## Build

The LDMS container is built via the main orchestrator script in the parent directory:

```bash
# From src/telemetry/containers/
./build_images.sh ldms

# Or with docker + push to registry
./build_images.sh ldms build_tool=docker build_action=push

# Or with custom tag
./build_images.sh ldms ldms_tag=1.2
```

**Image**: `dellhpcomniaaisolution/ldms`
**Default tag**: `1.1`
