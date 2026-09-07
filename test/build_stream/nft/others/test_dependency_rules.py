# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests to enforce design constraints and dependency injection rules.

These tests ensure that API routes use FastAPI's dependency injection
instead of directly accessing the container, which would cause production
code to use InMemory repositories instead of SQL repositories.
"""

import ast
from pathlib import Path
from typing import List, Tuple

import pytest


def get_python_files(directory: str, pattern: str = "*.py") -> List[Path]:
    """Get all Python files in directory matching pattern."""
    path = Path(directory)
    if not path.exists():
        return []
    return list(path.rglob(pattern))


def check_forbidden_imports(file_path: Path, forbidden_modules: List[str]) -> List[str]:
    """Check if file contains forbidden imports.

    Returns:
        List of forbidden import statements found.
    """
    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return []  # Skip files that can't be parsed

    for node in ast.walk(tree):
        # Check "from container import ..."
        if isinstance(node, ast.ImportFrom):
            if node.module in forbidden_modules:
                violations.append(f"from {node.module} import ...")

        # Check "import container"
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in forbidden_modules:
                    violations.append(f"import {alias.name}")

    return violations


def check_forbidden_calls(file_path: Path, forbidden_patterns: List[str]) -> List[Tuple[int, str]]:
    """Check if file contains forbidden function/method calls.

    Returns:
        List of (line_number, code_snippet) tuples for violations.
    """
    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line_num, line in enumerate(lines, start=1):
            for pattern in forbidden_patterns:
                if pattern in line and not line.strip().startswith('#'):
                    violations.append((line_num, line.strip()))
    except (UnicodeDecodeError, IOError):
        return []

    return violations


class TestDesignRules:
    """Enforce design constraints across the codebase."""

    def test_api_routes_dont_import_container(self):
        """API routes MUST use dependency injection, not direct container access.

        This test prevents the bug where routes use container.X() which returns
        InMemory repositories instead of SQL repositories, causing data loss.

        Related: Issue #1874 - Generate Input files hangs
        """
        # Get all route files in api/
        api_dir = Path(__file__).parent.parent.parent / "api"
        route_files = get_python_files(str(api_dir), "routes.py")

        assert len(route_files) > 0, "No route files found - check test setup"

        violations = {}
        for route_file in route_files:
            imports = check_forbidden_imports(route_file, ["container"])
            if imports:
                violations[str(route_file.relative_to(api_dir.parent))] = imports

        assert not violations, (
            "\nERROR: API routes importing 'container' (should use Depends() instead):\n"
            + "\n".join(
                f"  {file}:\n    " + "\n    ".join(imports)
                for file, imports in violations.items()
            )
            + "\n\nINFO: Fix: Use FastAPI dependency injection via Depends(get_X_use_case)"
        )

    def test_api_routes_dont_call_container_methods(self):
        """API routes MUST NOT call container methods directly.

        Even if container is imported for other reasons, routes should not
        call container.X() to instantiate services or use cases.
        """
        api_dir = Path(__file__).parent.parent.parent / "api"
        route_files = get_python_files(str(api_dir), "routes.py")

        assert len(route_files) > 0, "No route files found - check test setup"

        forbidden_patterns = [
            "container.",
            "_get_container()",
        ]

        violations = {}
        for route_file in route_files:
            calls = check_forbidden_calls(route_file, forbidden_patterns)
            if calls:
                violations[str(route_file.relative_to(api_dir.parent))] = calls

        assert not violations, (
            "\nERROR: API routes calling container methods directly:\n"
            + "\n".join(
                f"  {file}:\n    " + "\n    ".join(
                    f"Line {line_num}: {code}"
                    for line_num, code in calls
                )
                for file, calls in violations.items()
            )
            + "\n\nINFO: Fix: Use dependency injection via Depends()"
        )

    def test_use_cases_dont_import_infra_db(self):
        """Use cases MUST NOT depend on infrastructure layer (Clean Architecture).

        Use cases should depend on repository interfaces, not concrete
        database implementations. This ensures proper layering.
        """
        orchestrator_dir = Path(__file__).parent.parent.parent / "orchestrator"
        if not orchestrator_dir.exists():
            pytest.skip("Orchestrator directory not found")

        use_case_files = get_python_files(str(orchestrator_dir), "*.py")

        violations = {}
        for uc_file in use_case_files:
            imports = check_forbidden_imports(uc_file, ["infra.db"])
            if imports:
                violations[str(uc_file.relative_to(orchestrator_dir.parent))] = imports

        assert not violations, (
            "\nERROR: Use cases importing infrastructure layer (violates Clean Architecture):\n"
            + "\n".join(
                f"  {file}:\n    " + "\n    ".join(imports)
                for file, imports in violations.items()
            )
            + "\n\nINFO: Fix: Use repository interfaces, inject concrete implementations via DI"
        )

    def test_core_domain_has_no_infra_dependencies(self):
        """Core domain MUST NOT depend on infrastructure or API layers.

        The core domain (entities, value objects, exceptions) should be
        pure business logic with no external dependencies.
        """
        core_dir = Path(__file__).parent.parent.parent / "core"
        if not core_dir.exists():
            pytest.skip("Core directory not found")

        core_files = get_python_files(str(core_dir), "*.py")

        forbidden_modules = ["infra", "api", "container"]
        violations = {}

        for core_file in core_files:
            imports = check_forbidden_imports(core_file, forbidden_modules)
            if imports:
                violations[str(core_file.relative_to(core_dir.parent))] = imports

        assert not violations, (
            "\nERROR: Core domain importing infrastructure/API layers:\n"
            + "\n".join(
                f"  {file}:\n    " + "\n    ".join(imports)
                for file, imports in violations.items()
            )
            + "\n\nINFO: Fix: Core domain should be pure business logic"
        )

    def test_all_route_files_have_dependency_providers(self):
        """Each API module with routes SHOULD have a dependencies.py file.

        This ensures consistent dependency injection patterns across all APIs.
        """
        api_dir = Path(__file__).parent.parent.parent / "api"
        route_files = get_python_files(str(api_dir), "routes.py")

        missing_dependencies = []
        for route_file in route_files:
            # Skip auth routes as they don't need use cases
            if "auth" in str(route_file):
                continue

            # Check if dependencies.py exists in same directory
            dep_file = route_file.parent / "dependencies.py"
            if not dep_file.exists():
                missing_dependencies.append(
                    str(route_file.relative_to(api_dir.parent))
                )

        # This is a warning, not a hard failure
        if missing_dependencies:
            pytest.skip(
                "WARNING:  Some API modules missing dependencies.py:\n"
                + "\n".join(f"  - {file}" for file in missing_dependencies)
                + "\n\nINFO: Consider adding dependencies.py for consistent DI patterns"
            )


class TestDependencyInjectionPatterns:
    """Test that dependency injection is used correctly."""

    def test_routes_use_depends_for_use_cases(self):
        """Routes should use Depends() to inject use cases, not instantiate them.

        This is a positive test - we check that routes follow the correct pattern.
        """
        api_dir = Path(__file__).parent.parent.parent / "api"
        route_files = get_python_files(str(api_dir), "routes.py")

        routes_with_di = []
        for route_file in route_files:
            try:
                with open(route_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Check for Depends() pattern
                    if "Depends(get_" in content and "use_case" in content:
                        routes_with_di.append(route_file.name)
            except (UnicodeDecodeError, IOError):
                continue

        # At least some routes should use DI (we know generate_input_files does)
        assert len(routes_with_di) > 0, (
            "No routes found using Depends() for use case injection. "
            "This might indicate a test setup issue."
        )


if __name__ == "__main__":
    # Allow running this file directly for quick checks
    pytest.main([__file__, "-v"])
