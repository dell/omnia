# Orchestrator Testing Framework Documentation

## Overview

The Orchestrator Testing Framework provides comprehensive testing utilities for the Omnia Orchestrator component, following the same patterns established in the main module testing infrastructure. This framework enables testing of Ansible modules, roles, and playbooks with a consistent, structured approach.

## Architecture

The framework is integrated into the existing orchestrator test structure:

```
test/orchestrator/
├── library/
│   ├── functions/
│   │   ├── orchestrator_module_tester.py    # Module testing utilities
│   │   ├── orchestrator_role_tester.py      # Role testing utilities
│   │   ├── orchestrator_playbook_tester.py  # Playbook testing utilities
│   │   ├── orchestrator_func.py             # Existing orchestrator verification
│   │   ├── slurm_func.py                    # Slurm verification
│   │   └── validation_func.py               # Validation utilities
│   ├── messages/
│   │   ├── orchestrator_msgs.py             # Existing orchestrator messages
│   │   ├── orchestrator_test_msgs.py       # New framework messages
│   │   └── slurm_msgs.py                    # Slurm messages
│   └── vars/
│       ├── common_vars.py                   # Common variables
│       ├── domain_vars.py                   # Domain variables
│       └── slurm_vars.py                    # Slurm variables
├── fvt/
│   ├── modules/                             # Module tests
│   │   ├── test_validate_orchestrator_config.py
│   │   └── __init__.py
│   ├── roles/                               # Role tests
│   │   ├── test_orchestrator_setup.py
│   │   └── __init__.py
│   ├── playbooks/                           # Playbook tests
│   │   ├── test_orchestrator_yml.py
│   │   └── __init__.py
│   ├── validate/                            # Existing validation tests
│   ├── prepare/                             # Existing prepare tests
│   ├── provision/                           # Existing provision tests
│   └── cleanup/                             # Existing cleanup tests
└── conftest.py                              # Pytest configuration
```

## Testing Utilities

### Module Testing (`orchestrator_module_tester.py`)

Functions for testing Ansible modules in isolation:

- `test_module_validation(module_name, test_data)` - Test module structure and validation
- `test_validate_orchestrator_config_module(host, test_config)` - Test the config validation module
- `test_generate_functional_groups_module(host, mapping_data)` - Test functional groups module
- `test_slurm_conf_module(host, slurm_config)` - Test Slurm configuration module
- `test_module_schema_validation(module_name, schema_file)` - Validate module against JSON schema
- `check_module_dependencies(module_name)` - Check if module dependencies are available

### Role Testing (`orchestrator_role_tester.py`)

Functions for testing Ansible roles:

- `check_role_structure(role_name)` - Check if role has proper directory structure
- `check_role_tasks(role_name)` - Check if role has valid task files
- `check_role_vars(role_name)` - Check if role has valid variable files
- `check_role_defaults(role_name)` - Check if role has defaults file
- `check_role_metadata(role_name)` - Check if role has valid metadata
- `test_role_dependencies(role_name, host)` - Test if role dependencies can be satisfied
- `validate_role_syntax(role_name)` - Validate role YAML syntax

### Playbook Testing (`orchestrator_playbook_tester.py`)

Functions for testing Ansible playbooks following the deploy/verify pattern:

- `check_playbook_exists(playbook_name)` - Check if playbook exists
- `check_playbook_syntax(playbook_name)` - Validate playbook syntax
- `get_playbook_tags(playbook_name)` - Extract available tags from playbook
- `deploy_playbook_tag(host, playbook_name, tag, extra_vars)` - Deploy playbook with specific tag
- `verify_playbook_execution(host, playbook_name, tag)` - Verify playbook execution results
- `check_playbook_dependencies(playbook_name)` - Check playbook dependencies
- `test_playbook_dry_run(host, playbook_name, tag)` - Test playbook with dry-run mode
- `measure_playbook_execution_time(host, playbook_name, tag)` - Measure execution time for performance testing

## Usage Examples

### Testing a Module

```python
import pytest
from library.functions import TestLogger, test_module_validation, check_module_dependencies
from library.messages import TEST_FRAMEWORK_NAMES, TEST_FRAMEWORK_LOG_MSGS as LOG

@pytest.mark.sanity
def test_module_structure():
    """Test validate_orchestrator_config module structure."""
    module_name = "validate_orchestrator_config"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["module_validation"].format(module_name=module_name),
        "TC_MO_001"
    )
    
    test_data = {
        "input_project_dir": "/opt/omnia/orchestrator/input/project_default",
        "schema_dir": "src/orchestrator/plugins/module_utils/orchestrator_validation/schema"
    }
    
    result = test_module_validation(module_name, test_data)
    
    if result["success"]:
        tl.passed(LOG["module_validation_ok"].format(module_name=module_name), result["details"])
    else:
        tl.failed(LOG["module_validation_failed"].format(module_name=module_name), result["error"])
    
    assert result["success"]
```

### Testing a Role

```python
import pytest
from library.functions import TestLogger, check_role_structure, check_role_tasks
from library.messages import TEST_FRAMEWORK_NAMES, TEST_FRAMEWORK_LOG_MSGS as LOG

@pytest.mark.sanity
def test_role_structure():
    """Test orchestrator_setup role structure."""
    role_name = "orchestrator_setup"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["role_structure"].format(role_name=role_name),
        "TC_RO_001"
    )
    
    result = check_role_structure(role_name)
    
    if result["success"]:
        tl.passed(LOG["role_structure_ok"].format(role_name=role_name), result["details"])
    else:
        tl.failed(LOG["role_structure_failed"].format(role_name=role_name), result["error"])
    
    assert result["success"]
```

### Testing a Playbook

```python
import pytest
from library.functions import TestLogger, check_playbook_syntax, get_playbook_tags
from library.messages import TEST_FRAMEWORK_NAMES, TEST_FRAMEWORK_LOG_MSGS as LOG

@pytest.mark.sanity
def test_playbook_syntax():
    """Test orchestrator.yml playbook syntax."""
    playbook_name = "orchestrator.yml"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["playbook_syntax"].format(playbook_name=playbook_name),
        "TC_PB_002"
    )
    
    result = check_playbook_syntax(playbook_name)
    
    if result["success"]:
        tl.passed(LOG["playbook_syntax_ok"].format(playbook_name=playbook_name), result["details"])
    else:
        tl.failed(LOG["playbook_syntax_failed"].format(playbook_name=playbook_name), result["error"])
    
    assert result["success"]
```

### Deploy/Verify Pattern for Playbooks

```python
import pytest
from library.functions import TestLogger, deploy_playbook_tag, verify_playbook_execution
from library.messages import TEST_FRAMEWORK_NAMES, TEST_FRAMEWORK_LOG_MSGS as LOG

@pytest.mark.deploy
@pytest.mark.order(1)
def test_deploy_prepare(host):
    """Deploy orchestrator with prepare tag."""
    playbook_name = "orchestrator.yml"
    tag = "prepare"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["playbook_deploy"].format(playbook_name=playbook_name, tag=tag),
        "TC_PB_DEPLOY_001"
    )
    
    result = deploy_playbook_tag(host, playbook_name, tag)
    
    if result["success"]:
        tl.passed(LOG["playbook_deploy_ok"].format(playbook_name=playbook_name), result["details"])
    else:
        tl.failed(LOG["playbook_deploy_failed"].format(playbook_name=playbook_name), result["error"])
    
    assert result["success"]

@pytest.mark.order(2)
def test_verify_prepare(host):
    """Verify prepare deployment."""
    playbook_name = "orchestrator.yml"
    tag = "prepare"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["playbook_verify"].format(playbook_name=playbook_name, tag=tag),
        "TC_PB_VERIFY_001"
    )
    
    result = verify_playbook_execution(host, playbook_name, tag)
    
    if result["success"]:
        tl.passed(LOG["playbook_verify_ok"].format(playbook_name=playbook_name), result["details"])
    else:
        tl.failed(LOG["playbook_verify_failed"].format(playbook_name=playbook_name), result["error"])
    
    assert result["success"]
```

## Running Tests

### Run All Tests

```bash
cd test/orchestrator
source ../.venv/bin/activate  # or source .venv/bin/activate if using local venv
pytest fvt/ -v
```

### Run Specific Test Categories

```bash
# Run module tests only
pytest fvt/modules/ -v

# Run role tests only
pytest fvt/roles/ -v

# Run playbook tests only
pytest fvt/playbooks/ -v
```

### Run with Markers

```bash
# Run only sanity tests
pytest fvt/ -v -m sanity

# Run only functional tests
pytest fvt/ -v -m functional

# Run only deploy tests
pytest fvt/ -v -m deploy
```

### Run Specific Test Files

```bash
# Run specific module test
pytest fvt/modules/test_validate_orchestrator_config.py -v

# Run specific role test
pytest fvt/roles/test_orchestrator_setup.py -v

# Run specific playbook test
pytest fvt/playbooks/test_orchestrator_yml.py -v
```

## Test Organization

### Test Case Naming Convention

- **Module Tests**: `TC_MO_XXX` (e.g., TC_MO_001, TC_MO_002)
- **Role Tests**: `TC_RO_XXX` (e.g., TC_RO_001, TC_RO_002)
- **Playbook Tests**: `TC_PB_XXX` (e.g., TC_PB_001, TC_PB_002)

### Markers

- `@pytest.mark.sanity` - Baseline must-pass tests
- `@pytest.mark.functional` - Functional verification tests
- `@pytest.mark.deploy` - Tests that change system state (playbook execution)
- `@pytest.mark.order(n)` - Specify test execution order

### Test Structure

Each test should follow this pattern:

1. **Setup**: Create TestLogger with test name and TC ID
2. **Execution**: Call the appropriate testing function
3. **Logging**: Log success/failure with appropriate messages
4. **Assertion**: Assert the result with meaningful error messages

## Integration with Existing Tests

The new framework utilities are designed to work alongside existing orchestrator tests:

- **Existing tests** in `fvt/validate/`, `fvt/prepare/`, `fvt/provision/`, `fvt/cleanup/` continue to work as before
- **New framework tests** in `fvt/modules/`, `fvt/roles/`, `fvt/playbooks/` provide additional coverage
- **Shared utilities** from `omnia_auto` package are used by both old and new tests
- **Consistent patterns** ensure maintainability across the test suite

## Best Practices

1. **Use TestLogger**: Always use TestLogger for consistent output formatting
2. **Follow naming conventions**: Use TC_MO_XXX, TC_RO_XXX, TC_PB_XXX for test IDs
3. **Add appropriate markers**: Use @pytest.mark.sanity for critical tests
4. **Order tests appropriately**: Use @pytest.mark.order(n) when sequence matters
5. **Provide meaningful messages**: Use the message templates from TEST_FRAMEWORK_LOG_MSGS
6. **Handle errors gracefully**: Always check result["success"] before assertions
7. **Document tests**: Add docstrings explaining what each test validates

## Extending the Framework

To add new testing utilities:

1. **Add function** to the appropriate tester file (`orchestrator_module_tester.py`, `orchestrator_role_tester.py`, or `orchestrator_playbook_tester.py`)
2. **Follow the pattern**: Return dict with `success`, `details`, `error` keys
3. **Add messages** to `orchestrator_test_msgs.py` for logging and assertions
4. **Update imports** in `library/functions/__init__.py`
5. **Write tests** in the appropriate `fvt/` subdirectory

## Troubleshooting

### Import Errors

If you encounter import errors:
```bash
cd test/orchestrator
python -c "from library.functions import test_module_validation"
```

### Path Issues

Ensure you're running tests from the correct directory:
```bash
cd /root/modern-omnia/omnia/test/orchestrator
```

### Dependency Issues

Check that all dependencies are installed:
```bash
pip list | grep -E "pytest|testinfra|ansible"
```

## Future Enhancements

Potential areas for framework expansion:

1. **Mock utilities**: Add mocking support for external dependencies
2. **Performance testing**: Enhanced performance measurement and benchmarking
3. **Coverage reporting**: Integration with coverage.py for code coverage
4. **Parallel execution**: Support for parallel test execution
5. **Test data management**: Enhanced test dataset management and fixtures
6. **API testing**: Expanded API endpoint testing capabilities

## Conclusion

The Orchestrator Testing Framework provides a structured, maintainable approach to testing the Omnia Orchestrator component. By following the patterns established in the main module and using the provided utilities, you can create comprehensive tests for modules, roles, and playbooks that integrate seamlessly with the existing test infrastructure.