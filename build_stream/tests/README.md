# Build Stream Test Suite

This directory contains comprehensive unit and integration tests for all Build Stream workflows including Jobs API, Catalog Processing, Local Repository, Image Building, and Validation.

## Test Structure

```
tests/
├── integration/                # Integration tests for end-to-end workflows
│   ├── api/                   # API endpoint integration tests
│   │   ├── jobs/              # Jobs API tests
│   │   │   ├── conftest.py                    # Shared fixtures
│   │   │   ├── test_create_job_api.py         # POST /jobs tests
│   │   │   ├── test_get_job_api.py            # GET /jobs/{id} tests
│   │   │   └── test_delete_job_api.py         # DELETE /jobs/{id} tests
│   │   ├── catalog_roles/     # Catalog processing tests
│   │   │   ├── conftest.py                    # Shared fixtures
│   │   │   ├── test_get_roles_api.py          # GET /catalog_roles tests
│   │   │   └── test_catalog_workflow.py       # End-to-end catalog tests
│   │   ├── parse_catalog/     # Catalog parsing tests
│   │   │   ├── conftest.py                    # Shared fixtures
│   │   │   └── test_parse_catalog_api.py      # POST /parse_catalog tests
│   │   ├── local_repo/        # Local repository tests
│   │   │   ├── conftest.py                    # Shared fixtures
│   │   │   ├── test_create_local_repo_api.py  # POST /local_repo tests
│   │   │   └── test_repo_workflow.py          # End-to-end repo tests
│   │   ├── build_image/       # Image building tests
│   │   │   ├── conftest.py                    # Shared fixtures
│   │   │   ├── test_build_image_api.py        # POST /build_image tests
│   │   │   └── test_multi_arch_build.py       # Multi-architecture tests
│   │   └── validate/          # Validation tests
│   │       ├── conftest.py                    # Shared fixtures
│   │       └── test_validate_api.py           # POST /validate tests
│   ├── core/                  # Core domain integration tests
│   │   ├── jobs/              # Job entity integration tests
│   │   ├── catalog/           # Catalog entity integration tests
│   │   └── localrepo/         # Repository entity integration tests
│   └── infra/                 # Infrastructure integration tests
│       ├── repositories/      # Repository integration tests
│       └── external/          # External service integration tests
├── unit/                      # Unit tests for individual components
│   ├── api/                   # API layer unit tests
│   │   ├── jobs/              # Jobs API unit tests
│   │   │   ├── test_schemas.py                # Pydantic schema tests
│   │   │   ├── test_dependencies.py           # Dependency injection tests
│   │   │   └── test_routes.py                 # Route handler tests
│   │   ├── catalog_roles/     # Catalog API unit tests
│   │   ├── local_repo/        # Local repo API unit tests
│   │   └── validate/          # Validation API unit tests
│   ├── core/                  # Core domain unit tests
│   │   ├── jobs/              # Job entity and value object tests
│   │   ├── catalog/           # Catalog entity tests
│   │   ├── localrepo/         # Repository entity tests
│   │   └── validate/          # Validation entity tests
│   ├── orchestrator/          # Use case unit tests
│   │   ├── jobs/              # Job use case tests
│   │   ├── catalog/           # Catalog use case tests
│   │   ├── local_repo/        # Repository use case tests
│   │   └── validate/          # Validation use case tests
│   └── infra/                 # Infrastructure unit tests
│       ├── repositories/      # Repository implementation tests
│       ├── artifact_store/    # Artifact store tests
│       └── db/                # Database layer tests
├── end_to_end/                # Complete workflow tests
│   ├── test_full_job_workflow.py              # Complete job lifecycle
│   └── test_catalog_to_image.py               # Catalog to image workflow
├── performance/               # Performance and load tests
│   └── test_load.py           # Load testing scenarios
├── fixtures/                  # Shared test fixtures
│   ├── job_fixtures.py        # Job test data
│   └── repo_fixtures.py       # Repository test data
├── mocks/                     # Mock objects and data
│   ├── mock_vault.py          # Vault mock
│   └── mock_registry.py       # Registry mock
└── utils/                     # Test utilities and helpers
    ├── assertions.py          # Custom assertions
    └── helpers.py             # Test helper functions
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
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=api --cov=orchestrator --cov-report=html
```

### Run Specific Test Suites

```bash
# Integration tests only
pytest tests/integration/ -v

# Unit tests only
pytest tests/unit/ -v

# API tests only
pytest tests/integration/api/ tests/unit/api/ -v
```

### Run Specific Test Files

```bash
# Jobs API tests
pytest tests/integration/api/jobs/test_create_job_api.py -v

# Catalog processing tests
pytest tests/integration/api/catalog_roles/ -v

# Local repository tests
pytest tests/integration/api/local_repo/ -v

# Image building tests
pytest tests/integration/api/build_image/ -v

# Validation tests
pytest tests/integration/api/validate/ -v

# Schema validation tests
pytest tests/unit/api/jobs/test_schemas.py -v

# Use case tests
pytest tests/unit/orchestrator/ -v
```

### Run Specific Test Classes or Functions

```bash
# Run specific test class
pytest tests/integration/api/jobs/test_create_job_api.py::TestCreateJobSuccess -v

# Run specific test function
pytest tests/integration/api/jobs/test_create_job_api.py::TestCreateJobSuccess::test_create_job_returns_201_with_valid_request -v

# Run tests matching pattern
pytest tests/integration/ -k idempotency -v
```

## Test Types

### Unit Tests
Test individual components in isolation:
- **API Layer**: Route handlers, schemas, dependencies
- **Core Layer**: Entities, value objects, domain services
- **Orchestrator Layer**: Use cases and business logic
- **Infrastructure Layer**: Repositories, external integrations

### Integration Tests
Test component interactions:
- **API Integration**: Full HTTP request/response cycles
- **Database Integration**: Repository operations with real DB
- **External Services**: Vault, Pulp, container registries
- **Cross-Layer**: API → Use Case → Repository flows

### End-to-End Tests
Test complete workflows from start to finish:
- Full job creation and execution
- Catalog parsing through role generation
- Repository creation and package sync
- Image building and registry push

### Performance Tests
Test system performance and scalability:
- Load testing for concurrent requests
- Stress testing for resource limits
- Benchmark tests for critical operations

## Workflow-Specific Tests

### Jobs Workflow Tests
```bash
# All jobs tests
pytest tests/integration/api/jobs/ tests/unit/orchestrator/jobs/ -v

# Job creation and idempotency
pytest tests/integration/api/jobs/test_create_job_api.py -v

# Job lifecycle management
pytest tests/integration/api/jobs/test_get_job_api.py -v
```

### Catalog Workflow Tests
```bash
# All catalog tests
pytest tests/integration/api/catalog_roles/ tests/unit/core/catalog/ -v

# Catalog parsing
pytest tests/integration/api/parse_catalog/ -v

# Role generation
pytest tests/unit/orchestrator/catalog/ -v
```

### Local Repository Workflow Tests
```bash
# All local repo tests
pytest tests/integration/api/local_repo/ tests/unit/core/localrepo/ -v

# Repository creation
pytest tests/integration/api/local_repo/test_create_local_repo.py -v
```

### Image Building Workflow Tests
```bash
# All build image tests
pytest tests/integration/api/build_image/ tests/unit/core/build_image/ -v

# Multi-architecture builds
pytest tests/integration/api/build_image/ -k multi_arch -v
```

### Validation Workflow Tests
```bash
# All validation tests
pytest tests/integration/api/validate/ tests/unit/core/validate/ -v

# Schema validation
pytest tests/unit/core/validate/ -k schema -v
```

## Test Fixtures

### Shared Fixtures (conftest.py)

**Authentication & Authorization:**
- `client`: FastAPI TestClient with dev container
- `auth_headers`: Standard authentication headers
- `admin_auth_headers`: Admin-level authentication

**Idempotency & Correlation:**
- `unique_idempotency_key`: Unique key per test
- `unique_correlation_id`: Unique correlation ID per test

**Database & Storage:**
- `db_session`: Database session for tests
- `clean_db`: Fresh database for each test
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

### Adding a New Integration Test

1. Create test file in appropriate `tests/integration/` subdirectory
2. Use shared fixtures from conftest.py
3. Test full request/response cycles
4. Verify database state changes
5. Clean up test data

**Example:**
```python
# tests/integration/api/jobs/test_create_job_integration.py
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
