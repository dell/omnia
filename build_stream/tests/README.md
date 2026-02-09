# Test Suite for JobId Feature

This directory contains the unit and integration tests for the Jobs API (JobId, correlation/idempotency, CRUD flows).

## Test Structure

```
tests/
├── integration/
│   └── api/
│       └── jobs/
│           ├── conftest.py                    # Shared fixtures
│           ├── test_create_job_api.py         # POST /jobs tests
│           ├── test_get_job_api.py            # GET /jobs/{id} tests
│           └── test_delete_job_api.py         # DELETE /jobs/{id} tests
└── unit/
    └── api/
        └── jobs/
            ├── test_schemas.py                # Pydantic schema tests
            └── test_dependencies.py           # Dependency injection tests
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
# Create Job API tests
pytest tests/integration/api/jobs/test_create_job_api.py -v

# Schema validation tests
pytest tests/unit/api/jobs/test_schemas.py -v

# Dependency injection tests
pytest tests/unit/api/jobs/test_dependencies.py -v
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

## Test Fixtures

### Shared Fixtures (conftest.py)

- `client`: FastAPI TestClient with dev container
- `auth_headers`: Standard authentication headers
- `unique_idempotency_key`: Unique key per test
- `unique_correlation_id`: Unique correlation ID per test

### Usage Example

```python
def test_example(client, auth_headers):
    payload = {"catalog_uri": "s3://bucket/catalog.json"}
    response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)
    assert response.status_code == 201
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

1. **Isolation**: Each test is independent (unique idempotency keys)
2. **Fast**: Integration tests complete in <5 seconds each
3. **Deterministic**: No flaky tests, no time-dependent logic
4. **Clear**: Descriptive test names following pattern `test_<action>_<condition>_<expected_result>`
5. **Comprehensive**: Cover happy path, error cases, edge cases, and security

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
