# Repo Manager Non-Functional Tests

This document is the authoritative test-case registry for
`test/repo_manager/nft/`. It describes what each test validates and the
condition required for the test to pass.

Non-functional tests validate operational properties (idempotency,
performance, security) rather than correctness of business logic. They
require a deployed Pulp service and valid credentials on the target.

## Test-case ID standard

IDs use `RM_NFT_<SEQ>`:

| Segment | Meaning | Values or example |
|---------|---------|-------------------|
| `RM` | Repo Manager domain | Fixed domain code |
| `NFT` | Non-Functional Test level | Fixed test-level code |
| `SEQ` | Stable sequence | Three digits, starting at `001` |

## Test cases

### Idempotency (`test_idempotency.py`)

| TC ID | Test | Markers | Validation | Pass criteria |
|-------|------|---------|------------|---------------|
| RM_NFT_001 | `test_status_is_semantically_idempotent` | nft, idempotency | Repeated status generation preserves its published contract. | Running status generation twice produces semantically equivalent `repo_status.yml`. |

### Performance (`test_performance.py`)

| TC ID | Test | Markers | Validation | Pass criteria |
|-------|------|---------|------------|---------------|
| RM_NFT_002 | `test_pulp_status_response_time` | nft, performance | The local Pulp health command completes promptly. | Pulp status command returns within the configured timeout. |

### Security (`test_security.py`)

| TC ID | Test | Markers | Validation | Pass criteria |
|-------|------|---------|------------|---------------|
| RM_NFT_003 | `test_credentials_are_encrypted_and_private` | nft, security | Credentials are vaulted and credential files are private. | Credential files use Ansible Vault encryption and have restricted file permissions. |
| RM_NFT_004 | `test_private_keys_and_log_directories_are_restricted` | nft, security | Pulp private keys and Repo Manager logs deny public access. | Private key files and log directories deny world-readable access. |
| RM_NFT_005 | `test_pulp_tls_certificate_is_current` | nft, security | The Pulp TLS certificate remains valid for at least one day. | TLS certificate has not expired and is valid for at least one more day. |

## Registry summary

| Category | IDs | Total |
|----------|-----|-------|
| Idempotency | `RM_NFT_001` | 1 |
| Performance | `RM_NFT_002` | 1 |
| Security | `RM_NFT_003`--`005` | 3 |
| **Total NFT** | | **5** |

## Execution commands

Run from `test/repo_manager/`:

```bash
# Run all NFT tests
./run_validation.sh nft_repo_manager test

# Run by category
./run_validation.sh nft_repo_manager test --marker idempotency
./run_validation.sh nft_repo_manager test --marker performance
./run_validation.sh nft_repo_manager test --marker security
```
