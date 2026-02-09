# GitLab CI/CD Pipeline Implementation Specification

## 1. Objectives
- Provide a consistent `.gitlab-ci.yml` layout that can be reused across Omnia projects.
- Define canonical pipeline stages (Parse → Generate → Repo → Build → Validate → Publish → Cleanup) and how they interact.
- Capture artifact and dependency flow so downstream jobs know which outputs to consume.
- Clarify CI/CD variable strategy (global defaults, masked secrets, environment overrides).
- Detail runner requirements (tags, executors, base images) to ensure jobs land on compatible infrastructure.

## 2. YAML Structure Overview
```yaml
stages:
  - parse
  - generate
  - repo
  - build
  - validate
  - publish
  - cleanup

variables:
  CATALOG_FILE: "catalog.yml"
  OUTPUT_DIR: "dist"
  GIT_STRATEGY: clone
  GIT_DEPTH: 20

workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "push"
    - if: $CI_PIPELINE_SOURCE == "schedule"
    - if: $CI_PIPELINE_SOURCE == "trigger"

.default-job:
  tags:
    - omnia-shared
  interruptible: true
  retry:
    max: 1
    when:
      - runner_system_failure
```
- **`stages`** establishes the execution order.
- **`variables`** contain defaults referenced by jobs (can be overridden per-job or via GitLab UI).
- **`workflow.rules`** prevents unwanted implicit pipelines.
- **`.default-job`** anchor consolidates tags/retry settings and can be re-used with YAML merge (`<<: *default-job`).

## 3. Stage Breakdown
| Stage | Purpose | Typical Image | Key Inputs | Key Outputs |
|-------|---------|---------------|------------|-------------|
| Parse | Lint + schema-validate `catalog.yml` | `python:3.11-slim` | `catalog.yml`, JSON schema | Validation report artifact |
| Generate | Convert catalog → intermediate assets (manifests, charts) | `alpine:3.19` with `yq/jq` | Validated catalog | `generated/` folder with YAML manifests |
| Repo | Commit/push generated assets back to repo or mirror | `alpine/git` | `generated/` artifacts | Tag/commit pushed, optional MR |
| Build | Container/image creation | `docker:24-git` | Generated manifests/templates | Images pushed to registry; SBOMs |
| Validate | Runtime tests, policy checks | `hashicorp/terraform`, `kube-score`, etc. | Build artifacts/images | Test reports, SARIF |
| Publish | Release packaging, notifications | `alpine:latest` | Artifacts from build/validate | Release notes, webhook call |
| Cleanup | Remove temp resources, revoke creds | `alpine:latest` | Nothing new | Confirmation log |

## 4. Stage Dependencies & Artifacts
```yaml
parse_catalog:
  stage: parse
  image: python:3.11-slim
  script:
    - pip install -r requirements.txt
    - python scripts/validate_catalog.py $CATALOG_FILE
  artifacts:
    reports:
      junit: reports/validate.xml
    paths:
      - reports/validation.json
    expire_in: 1 week


generate_assets:
  stage: generate
  needs:
    - job: parse_catalog
      artifacts: true
  image: alpine:3.19
  script:
    - ./scripts/generate.sh --input $CATALOG_FILE --out artifacts/generated
  artifacts:
    paths:
      - artifacts/generated

repo_sync:
  stage: repo
  needs: [generate_assets]
  image: alpine/git
  script:
    - ./scripts/repo_sync.sh artifacts/generated

build_images:
  stage: build
  needs: [generate_assets]
  image: docker:24-git
  services:
    - docker:24-dind
  script:
    - ./scripts/build.sh artifacts/generated
  artifacts:
    paths:
      - artifacts/images

validate_release:
  stage: validate
  needs:
    - build_images
    - repo_sync
  image: alpine:3.19
  script:
    - ./scripts/validate_release.sh artifacts/images
  artifacts:
    reports:
      junit: reports/junit.xml
      dotenv: reports/env.list

publish_release:
  stage: publish
  needs: [validate_release]
  image: alpine:3.19
  script:
    - ./scripts/publish.sh artifacts/images
    - ./scripts/notify.sh

cleanup_pipeline:
  stage: cleanup
  needs: [publish_release]
  when: always
  image: alpine:3.19
  script:
    - ./scripts/cleanup.sh
```
- `needs` allows jobs to start as soon as dependencies finish instead of waiting for entire stages.
- Artifacts expire after one week to avoid storage bloat; adjust per retention requirements.
- `cleanup` runs even if earlier stages fail (`when: always`).

## 5. Variable Management
| Variable | Scope | Source | Notes |
|----------|-------|--------|-------|
| `CATALOG_FILE` | Global | YAML default | Path to catalog; override per branch if a different file should trigger. |
| `CATALOG_SCHEMA_URL` | Project/group variable | GitLab UI → Settings → CI/CD | Masked & protected; used by Parse stage. |
| `GENERATOR_IMAGE` | Project variable | `.gitlab-ci.yml` + `variables` | Points to container image with generator tooling. |
| `REGISTRY_USER` / `REGISTRY_PASSWORD` | Group variable | GitLab UI | Mark as masked + protected; used by Build/Publish. |
| `WEBHOOK_URL` | Project/environ variable | GitLab UI or `.gitlab-ci.yml` with `environment:` | Optional; Publish stage posts completion payload. |
| `DEPLOY_ENVIRONMENT` | Environment variable | `environment:name` block | Drives per-env logic (URLs, credentials). |

**Management guidelines**
- Use **group-level** variables for shared credentials (runner tokens, registry creds).
- Use **project-level** variables for repo-specific values (catalog source URL, release channel).
- Protect variables that should only be available on protected branches/tags.
- Mask secrets so they never appear in job logs.
- For large structured configs, store them in a separate repo and fetch at runtime rather than embedding multi-line variables.

## 6. Runner Requirements
| Aspect | Requirement |
|--------|-------------|
| Executor | Docker or Podman-in-podman for containerized jobs; shell executor for lightweight scripts. |
| Tags | `omnia-shared` for general workloads; `omnia-build` for jobs needing DinD; `omnia-sec` for security tools. Jobs specify `tags` to land on compatible runners. |
| Images | Ensure runner host has network access to Docker Hub or internal registry. Cache frequently used images to reduce pull time. |
| Resources | Baseline: 2 vCPU, 4 GB RAM for parse/generate stages; 4 vCPU, 8 GB RAM for build stages. Configure `concurrent = 2` on runner to avoid resource contention. |
| Certificates | Runners must trust the GitLab HTTPS certificate (place CA file in `/etc/gitlab-runner/certs/<domain>.crt`). |
| Volume Mounts | If jobs need host tooling (e.g., Podman socket), mount `/run/podman/podman.sock` and guard with SELinux labels (`:Z`). |

## 7. Implementation Steps
1. **Copy templates** from `omnia/buildstreaM/` into target repo (`.gitlab-ci.yml`, scripts, catalog template).
2. **Customize variables**: set `CATALOG_FILE`, registry URLs, webhook endpoints.
3. **Register runner** and apply required tags (Docker executor for build stages).
4. **Configure project/group variables** in GitLab UI:
   - `REGISTRY_USER/PASSWORD` (masked, protected)
   - `CATALOG_SCHEMA_URL`
   - `WEBHOOK_URL` (optional)
5. **Commit & push** `.gitlab-ci.yml` plus supporting scripts.
6. **Trigger pipeline** via push or API trigger; monitor at `/root/omnia-catalog/-/pipelines`.
7. **Iterate**: expand from bare-minimum job → add Parse stage → add Generate, etc., verifying artifacts at each step.
8. **Document** release checklist (done above) and update Omnia runbook.

## 8. Validation & Rollout
- Run pipeline on `main` to ensure all stages succeed end-to-end.
- Inspect artifacts (validation reports, generated manifests, images) to ensure naming conventions align with downstream tooling.
- Confirm runner logs show successful job pickups; adjust tags/executors if jobs end up pending.
- Communicate HTTPS/TLS requirements to all automation scripts (update `GITLAB_URL`).
- Maintain rollback plan: keep previous `.gitlab-ci.yml` tagged so you can revert quickly if a new stage introduces regressions.

## 9. References
- GitLab CI/CD pipeline syntax: https://docs.gitlab.com/ee/ci/yaml/
- Runner cert trust: https://docs.gitlab.com/runner/configuration/tls-self-signed.html
- Artifacts best practices: https://docs.gitlab.com/ee/ci/pipelines/job_artifacts.html
