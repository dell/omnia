# Build Stream Test Suite

Comprehensive tests for all Build Stream workflows including Jobs API, Catalog
Processing, Local Repository, Image Building, Deploy, Restart, Cleanup, Upload,
and Validation.

All tests (including former "integration" tests that exercise full API request/
response cycles with a real FastAPI `TestClient` and SQLite-backed DB) now live
under `tests/unit/`. Each test subpackage carries its own `conftest.py` with the
fixtures it needs (mocked auth, temp SQLite DB, etc.) so tests remain isolated
and fast without any external services.

## Test Structure

```
tests/
├── unit/                              # All tests (isolated, no external services required)
│   ├── api/
│   │   ├── auth/                      # Registration & token tests
│   │   ├── build_image/               # POST /build_image route + API tests
│   │   ├── catalog_roles/             # GET /catalog_roles route + service tests
│   │   ├── deploy/                    # Deploy route error handler tests
│   │   ├── generate_input_files/      # Generate input files route + API tests
│   │   ├── images/                    # Images route tests
│   │   ├── jobs/                      # Jobs CRUD, schema & dependency tests
│   │   ├── local_repo/                # Local repo route + API tests
│   │   ├── parse_catalog/             # Parse catalog route + API tests
│   │   ├── restart/                   # Restart stage route + API tests
│   │   ├── upload/                    # Upload route tests
│   │   └── validate/                  # Validate route + API tests
│   ├── core/
│   │   ├── catalog/                   # Parser, adapter, generator, policy, diff regression
│   │   ├── cleanup/                   # Cleanup exceptions, S3 service interface
│   │   ├── deploy/                    # Deploy entities, services, exceptions
│   │   ├── image_group/               # ImageGroup entities & value objects
│   │   ├── jobs/                      # Job entities, value objects, state machine
│   │   └── localrepo/                 # Local repo entities
│   ├── infra/
│   │   ├── artifact_store/            # File artifact store tests
│   │   └── db/                        # SQL repository tests (skips if no live PostgreSQL)
│   └── orchestrator/
│       ├── catalog/                   # Catalog use case & command tests
│       ├── common/                    # ResultPoller tests (build-image, deploy/restart failure)
│       ├── local_repo/                # Local repo use case tests
│       └── validate/                  # Validate use case (retry lifecycle, guard edge cases)
├── others/                            # Design rule enforcement tests
├── performance/                       # Performance/load tests
└── conftest.py                        # Shared fixtures (auth, client, DB session)
```

## Prerequisites

Install test dependencies:

```bash
pip install -r requirements.txt
```

Required packages:
- pytest>=7.4.0
- pytest-asyncio>=0.21.0
- httpx>=0.24.0
- pytest-cov>=4.1.0

## Running Tests

### Run All Tests

```bash
# Run all tests (ENV=test prevents debugpy from attaching)
ENV=test python -m pytest tests/ -v

# Run with coverage
ENV=test python -m pytest tests/ --cov=api --cov=orchestrator --cov=core --cov-report=html
```

### Run Specific Test Suites

```bash
# All tests (fast — no external services required)
python -m pytest tests/unit/ -v

# API tests only
python -m pytest tests/unit/api/ -v
```

### Run Specific Test Files

```bash
# Jobs API tests
pytest tests/unit/api/jobs/test_create_job_api.py -v

# Catalog processing tests
pytest tests/unit/api/catalog_roles/ -v

# Local repository tests
pytest tests/unit/api/local_repo/ -v

# Image building tests
pytest tests/unit/api/build_image/ -v

# Validation tests
pytest tests/unit/api/validate/ -v

# Schema validation tests
pytest tests/unit/api/jobs/test_schemas.py -v

# Use case tests
pytest tests/unit/orchestrator/ -v
```

### Run Specific Test Classes or Functions

```bash
# Run specific test class
pytest tests/unit/api/jobs/test_create_job_api.py::TestCreateJobSuccess -v

# Run specific test function
pytest tests/unit/api/jobs/test_create_job_api.py::TestCreateJobSuccess::test_create_job_returns_201_with_valid_request -v

# Run tests matching pattern
pytest tests/unit/ -k idempotency -v
```

## Test Types

### Unit Tests
Test individual components in isolation:
- **API Layer**: Route handlers, schemas, dependencies
- **Core Layer**: Entities, value objects, domain services
- **Orchestrator Layer**: Use cases and business logic
- **Infrastructure Layer**: Repositories, external integrations

### API/Workflow Tests
Full HTTP request/response cycles against a real FastAPI `TestClient`, backed
by a temporary SQLite database and mocked authentication (no live external
services required):
- Full job creation and execution
- Catalog parsing through role generation
- Repository creation and package sync
- Image building request handling

### Performance Tests
Test system performance and scalability:
- Load testing for concurrent requests
- Stress testing for resource limits
- Benchmark tests for critical operations

## Workflow-Specific Tests

### Jobs Workflow Tests
```bash
# All jobs tests
pytest tests/unit/api/jobs/ tests/unit/orchestrator/jobs/ -v

# Job creation and idempotency
pytest tests/unit/api/jobs/test_create_job_api.py -v

# Job lifecycle management
pytest tests/unit/api/jobs/test_get_job_api.py -v
```

### Catalog Workflow Tests
```bash
# All catalog tests
pytest tests/unit/api/catalog_roles/ tests/unit/core/catalog/ -v

# Catalog parsing
pytest tests/unit/api/parse_catalog/ -v

# Role generation
pytest tests/unit/orchestrator/catalog/ -v
```

### Local Repository Workflow Tests
```bash
# All local repo tests
pytest tests/unit/api/local_repo/ tests/unit/core/localrepo/ -v

# Repository creation
pytest tests/unit/api/local_repo/test_create_local_repo_api.py -v
```

### Image Building Workflow Tests
```bash
# All build image tests
pytest tests/unit/api/build_image/ -v

# Multi-architecture builds
pytest tests/unit/api/build_image/ -k multi_arch -v
```

### Validation Workflow Tests
```bash
# All validation tests
pytest tests/unit/api/validate/ tests/unit/core/validate/ -v

# Schema validation
pytest tests/unit/core/validate/ -k schema -v
```

## Test Fixtures

### Catalog Fixtures

Tests use the **real examples catalog** shipped with the repo:

```
../examples/catalog/catalog_rhel.json   # Primary catalog fixture (RHEL 10.0)
core/catalog/test_fixtures/             # Remaining domain-specific fixtures:
  ├── adapter_policy_test.json          #   Policy config for adapter_policy tests
  └── functional_layer.json             #   Functional layer for generator tests
```

The stale `core/catalog/test_fixtures/catalog_rhel.json` was removed; all tests
now reference `examples/catalog/catalog_rhel.json` and skip gracefully if the
file is not present (e.g. in a shallow CI clone).

### Shared Fixtures (conftest.py)

**Authentication & Authorization:**
- `client`: FastAPI TestClient with dev container
- `auth_headers`: Standard authentication headers

**Idempotency & Correlation:**
- `unique_idempotency_key`: Unique key per test
- `unique_correlation_id`: Unique correlation ID per test

**Database & Storage:**
- `db_session`: Database session for tests
- `artifact_store`: Test artifact storage

**Mock Services:**
- `mock_vault_client`: Mocked Vault integration
- `mock_pulp_client`: Mocked Pulp integration
- `mock_registry_client`: Mocked container registry

### Usage Example

```python
def test_create_job(client, auth_headers, unique_idempotency_key):
    """Test job creation with idempotency."""
    payload = {
        "catalog_uri": "s3://bucket/catalog.json",
        "idempotency_key": unique_idempotency_key
    }
    response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)
    assert response.status_code == 201
    assert "job_id" in response.json()
```

## Known Skips & Pre-existing Issues

- `tests/unit/infra/db/test_sql_repositories.py` — skips/errors when no
  PostgreSQL dialect is available (no live DB in local dev)
- `test_adapter_cli_defaults::test_generate_omnia_json_with_defaults_writes_output`
  — skipped: legacy `generate_all_configs` adapter path is unused in production;
  the current production path is `adapter_policy.generate_configs_from_policy`
- `tests/others/test_dependency_rules.py` — 2 pre-existing architectural
  violation failures in `api/jobs/routes.py` (not test bugs)
- `tests/performance/test_local_repo_performance.py` — 3 pre-existing failures;
  tests expect `202` from `POST /local_repo` but get `412` because the job
  has no completed upstream stages

## Coverage Report

Generate HTML coverage report:

```bash
pytest tests/ --cov=api --cov=orchestrator --cov-report=html
```

View report:
```bash
# Open htmlcov/index.html in browser
```

## CI/CD Integration

Add to GitHub Actions workflow:

```yaml
- name: Run Tests
  run: |
    pip install -r requirements.txt
    pytest tests/ --cov=api --cov=orchestrator --cov-report=xml

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Test Best Practices

### Test Design Principles

1. **Isolation**: Each test is independent and can run in any order
   - Use unique idempotency keys and correlation IDs
   - Clean up resources after each test
   - Avoid shared mutable state

2. **Fast Execution**: Tests should complete quickly
   - Unit tests: <100ms each
   - Integration tests: <5 seconds each
   - Use mocks for external dependencies

3. **Deterministic**: Tests produce consistent results
   - No flaky tests or race conditions
   - Avoid time-dependent logic
   - Use fixed test data

4. **Clear Naming**: Follow descriptive naming conventions
   - Pattern: `test_<action>_<condition>_<expected_result>`
   - Example: `test_create_job_with_invalid_catalog_returns_400`

5. **Comprehensive Coverage**: Test all scenarios
   - Happy path (success cases)
   - Error cases (validation failures, exceptions)
   - Edge cases (boundary conditions)
   - Security (authentication, authorization)

### Test Organization

**Arrange-Act-Assert Pattern:**
```python
def test_example():
    # Arrange: Set up test data and preconditions
    payload = {"catalog_uri": "s3://bucket/catalog.json"}
    
    # Act: Execute the operation being tested
    response = client.post("/api/v1/jobs", json=payload)
    
    # Assert: Verify the expected outcome
    assert response.status_code == 201
    assert "job_id" in response.json()
```

**Test Grouping:**
- Group related tests in classes
- Use descriptive class names (e.g., `TestCreateJobSuccess`, `TestCreateJobValidation`)
- Share setup/teardown logic within classes

### Security Testing

**Authentication Tests:**
- Test endpoints without authentication (should return 401)
- Test with invalid tokens (should return 401)
- Test with expired tokens (should return 401)

**Authorization Tests:**
- Test with insufficient permissions (should return 403)
- Test role-based access control
- Verify resource ownership checks

**Input Validation:**
- Test SQL injection attempts
- Test XSS payloads
- Test path traversal attempts
- Test oversized inputs

### Mocking Guidelines

**When to Mock:**
- External HTTP APIs (Vault, Pulp, registries)
- File system operations (for unit tests)
- Time-dependent operations
- Expensive computations

**When NOT to Mock:**
- Database operations (use test database)
- Core business logic
- Internal service calls
- Simple utility functions

### Code Coverage Goals

- **Overall**: >80% code coverage
- **Core Domain**: >90% coverage
- **API Routes**: >85% coverage
- **Use Cases**: >90% coverage
- **Critical Paths**: 100% coverage

## Troubleshooting

### Tests Fail with "Module not found"

```bash
# Ensure you're in the correct directory
cd build_stream/

# Run with Python path
PYTHONPATH=. pytest tests/
```

### Tests Fail with Container Issues

```bash
# Set ENV to dev
export ENV=dev  # Linux/Mac
set ENV=dev     # Windows CMD
$env:ENV = "dev"  # Windows PowerShell

pytest tests/
```

### Slow Test Execution

```bash
# Run tests in parallel
pip install pytest-xdist
pytest tests/ -n auto
```

### Database Connection Issues

```bash
# Ensure PostgreSQL is running
# Check connection settings in environment variables

# For Windows PowerShell
$env:DATABASE_URL = "postgresql://user:password@localhost:5432/build_stream_test"

# For Linux/Mac
export DATABASE_URL="postgresql://user:password@localhost:5432/build_stream_test"

# Run migrations
alembic upgrade head

# Run tests
pytest tests/
```

### Authentication Failures

```bash
# Verify Vault is accessible (if using real Vault)
# Or ensure mock Vault is configured

# Check JWT token configuration
# Verify environment variables are set correctly
```

## Environment Configuration

### Required Environment Variables

For running tests, configure the following environment variables:

**Windows PowerShell:**
```powershell
$env:ENV = "dev"
$env:HOST = "0.0.0.0"
$env:PORT = "8000"
$env:DATABASE_URL = "postgresql://user:password@localhost:5432/build_stream_test"
$env:LOG_LEVEL = "DEBUG"
```

**Linux/Mac:**
```bash
export ENV=dev
export HOST=0.0.0.0
export PORT=8000
export DATABASE_URL=postgresql://user:password@localhost:5432/build_stream_test
export LOG_LEVEL=DEBUG
```

### Test Database Setup

```bash
# Create test database
createdb build_stream_test

# Run migrations
alembic upgrade head

# Verify database
psql build_stream_test -c "\dt"
```

## Writing New Tests

### Adding a New Unit Test

1. Create test file in appropriate `tests/unit/` subdirectory
2. Import required modules and fixtures
3. Write test functions following naming conventions
4. Use mocks for external dependencies
5. Run tests to verify

**Example:**
```python
# tests/unit/core/jobs/test_job_entity.py
import pytest
from core.jobs.entities import Job
from core.jobs.value_objects import JobId, StageName

def test_job_creation_with_valid_data():
    """Test job entity creation with valid data."""
    job_id = JobId.generate()
    job = Job(job_id=job_id, client_id="test-client")
    
    assert job.job_id == job_id
    assert job.client_id == "test-client"
    assert job.status == "pending"
```

### Adding a New API/Workflow Test

1. Create test file in the appropriate `tests/unit/api/<feature>/` subdirectory
2. Add a `conftest.py` in that subdirectory if it needs its own `client`
   fixture (mocked auth + temp SQLite DB) — see existing subdirectories
   (e.g. `tests/unit/api/jobs/conftest.py`) for the pattern
3. Test full request/response cycles
4. Verify database state changes
5. Clean up test data (handled automatically via `tmp_path` fixture)

**Example:**
```python
# tests/unit/api/jobs/test_create_job_integration.py
def test_create_job_integration(client, auth_headers, unique_idempotency_key):
    """Test complete job creation flow."""
    payload = {
        "catalog_uri": "s3://test-bucket/catalog.json",
        "idempotency_key": unique_idempotency_key
    }
    
    response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)
    
    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: build_stream_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests
        env:
          ENV: dev
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/build_stream_test
        run: |
          pytest tests/ -v --cov=api --cov=orchestrator --cov=core --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Additional Resources

- [Main Build Stream README](../README.md) - Architecture and getting started
- [Developer Guide](../doc/developer-guide.md) - Comprehensive development guide
- [Workflow Documentation](../doc/) - Detailed workflow guides
- [pytest Documentation](https://docs.pytest.org/) - pytest framework reference
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/) - FastAPI testing guide
