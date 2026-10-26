# prepare_base

| Order | TC ID | Test | Suite | Phase |
|---:|---|---|---|---|
| 1001 | `TC_PB_001` | `test_precheck_prepare_base` | root | exec |
| 1002 | `TC_PB_002` | `test_prepare_base` | root | exec |
| 1101 | `TC_PB_003` | `test_repo_manager_ready` | `readiness` | verify |
| 1102 | `TC_PB_004` | `test_image_build_manager_ready` | `readiness` | verify |
| 1103 | `TC_PB_005` | `test_orchestrator_ready` | `readiness` | verify |

Prepares the BuildStream prerequisites: `./omnia.sh --prepare-base` from
`src/main` validates the inputs of, collects credentials for and prepares
`repo_manager`, `image_build_manager` and `orchestrator` in that order
(fail-fast). Output is streamed live and there is no timeout.

**Precheck:** omnia.env sets `OMNIA_DATA_PATH`, `OMNIA_PROJECT_NAME` and
`OMNIA_VENV_PATH`; the venv and `omnia.sh` exist; the three domain credential
stores exist, so omnia.sh never prompts. Save them with
`./setup_env.sh --set-domain-creds`.

**Readiness (verify):** each domain's prepare output, every item listed with
a check or cross mark:

| Domain | Checked |
|---|---|
| repo_manager | Pulp quadlet, `pulp.service`, `pulp` container |
| image_build_manager | `minio-server`, `registry` containers; `minio.service`, `registry.service`; ports 9000, 9001, 5000 |
| orchestrator | `openchami.target`; `acme-deploy`, `acme-register`, `boot-service`, `coresmd-coredhcp`, `coresmd-coredns`, `haproxy`, `metadata-service`, `openchami-cert-trust`, `postgres`, `smd-init`, `smd`, `step-ca`, `tokensmith` services; `openchami-cert-renewal.timer`; containers `boot-service`, `coresmd-coredhcp`, `coresmd-coredns`, `haproxy`, `metadata-service`, `postgres`, `smd`, `step-ca`, `tokensmith` (healthcheck honoured); volumes `boot-service-data`, `metadata-service-data`, `postgres-data`, `haproxy-certs`; OpenLDAP (`omnia_auth` quadlet, service, healthy container) when `orchestrator_state.yml` sets `openldap_support` |

The OpenCHAMI lists come from the product's component specification
(`roles/cleanup/components/openchami/vars/component_spec.yml`); one-shot
units (`acme-*`, `smd-init`, `openchami-cert-trust`) stay `active (exited)`.

```bash
./run_validation.sh e2e_build_stream prepare_base test
./run_validation.sh e2e_build_stream prepare_base verify      # readiness only
```
