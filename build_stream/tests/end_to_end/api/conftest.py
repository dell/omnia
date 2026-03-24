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

"""Pytest fixtures for integration tests with real Ansible Vault."""

# pylint: disable=redefined-outer-name,consider-using-with

import base64
import logging
import os
import secrets
import shutil
import signal
import socket
import string
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Generator, Optional

import httpx
import pytest
import yaml
from argon2 import PasswordHasher, Type  # noqa: E0611 pylint: disable=no-name-in-module

# Configure logging for integration tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("integration_tests")


def generate_secure_test_password(length: int = 24) -> str:
    """Generate a secure password for integration tests.

    Args:
        length: Length of the password (default: 24 for extra security)

    Returns:
        Secure random password
    """
    # Use stronger character set for integration tests
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # Ensure minimum security requirements
    if length < 16:
        raise ValueError("Password length must be at least 16 characters")

    # Start with one of each required character type
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special),
    ]

    # Fill remaining length
    all_chars = lowercase + uppercase + digits + special
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))

    # Shuffle to avoid predictable pattern
    secrets.SystemRandom().shuffle(password)

    return ''.join(password)


def generate_test_client_secret(length: int = 32) -> str:
    """Generate a test client secret with proper bld_s_ prefix.

    Args:
        length: Total length of the secret including prefix (default: 32)

    Returns:
        Test client secret with bld_s_ prefix
    """
    if length < 8:
        raise ValueError("Client secret length must be at least 8 characters")

    # Generate random part (subtract 6 for "bld_s_" prefix)
    random_part_length = max(8, length - 6)
    random_part = generate_secure_test_password(random_part_length)

    return f"bld_s_{random_part}"


def generate_invalid_client_id() -> str:
    """Generate an invalid client ID for testing (missing bld_ prefix).

    Returns:
        Invalid client ID without proper prefix
    """
    return (
        "invalid_client_id_" + 
        ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    )


def generate_invalid_client_secret() -> str:
    """Generate an invalid client secret for testing (missing bld_s_ prefix).

    Returns:
        Invalid client secret without proper prefix
    """
    return (
        "invalid_secret_" + 
        ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    )


class IntegrationTestConfig:
    """Configuration for integration tests."""

    # Username is not a secret
    AUTH_USERNAME = "build_stream_registrar"
    SERVER_HOST = "127.0.0.1"
    SERVER_PORT = 18443  # Use different port to avoid conflicts
    SERVER_STARTUP_TIMEOUT = 30

    @classmethod
    def get_vault_password(cls) -> str:
        """Get a dynamically generated vault password.

        Returns:
            Secure random vault password
        """
        return generate_secure_test_password(24)

    @classmethod
    def get_auth_password(cls) -> str:
        """Get a dynamically generated auth password.

        Returns:
            Secure random auth password
        """
        return generate_secure_test_password(24)


class VaultManager:  # noqa: R0902 pylint: disable=too-many-instance-attributes
    """Manages Ansible Vault setup and teardown for integration tests."""

    def __init__(self, base_dir: str):
        """Initialize vault manager.

        Args:
            base_dir: Base directory for test vault files.
        """
        self.base_dir = Path(base_dir)
        self.vault_dir = self.base_dir / "vault"
        self.vault_file = self.vault_dir / "build_stream_oauth_credentials.yml"
        self.vault_pass_file = self.base_dir / ".vault_pass"
        self.keys_dir = self.base_dir / "keys"
        self.private_key_file = self.keys_dir / "jwt_private.pem"
        self.public_key_file = self.keys_dir / "jwt_public.pem"
        self._hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )

    def setup(self, username: str, password: str) -> None:
        """Set up vault with initial credentials.

        Args:
            username: Registration username.
            password: Registration password.
        """
        logger.info("Setting up Ansible Vault...")
        logger.info("  Vault directory: %s", self.vault_dir)
        logger.info("  Vault file: %s", self.vault_file)
        logger.info("  Vault password file: %s", self.vault_pass_file)

        self.vault_dir.mkdir(parents=True, exist_ok=True)
        logger.info("  Created vault directory")

        self.vault_pass_file.write_text(IntegrationTestConfig.get_vault_password())
        self.vault_pass_file.chmod(0o600)
        logger.info("  Created vault password file")

        logger.info("  Generating Argon2id password hash...")
        password_hash = self._hasher.hash(password)

        vault_content = {
            "auth_registration": {
                "username": username,
                "password_hash": password_hash,
            },
            "oauth_clients": {},
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as temp_file:
            yaml.safe_dump(vault_content, temp_file, default_flow_style=False)
            temp_path = temp_file.name

        try:
            logger.info("  Encrypting vault with ansible-vault...")
            subprocess.run(
                [
                    "ansible-vault",
                    "encrypt",
                    temp_path,
                    "--vault-password-file",
                    str(self.vault_pass_file),
                    "--encrypt-vault-id",
                    "default",
                ],
                check=True,
                capture_output=True,
            )

            shutil.move(temp_path, str(self.vault_file))
            self.vault_file.chmod(0o600)
            logger.info("  Vault encrypted and saved successfully")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        logger.info("Vault setup complete")

        # Generate JWT keys for token signing
        self._generate_jwt_keys()

    def _generate_jwt_keys(self) -> None:
        """Generate RSA key pair for JWT signing in e2e tests."""
        logger.info("Generating JWT keys for e2e tests...")
        logger.info("  Keys directory: %s", self.keys_dir)

        self.keys_dir.mkdir(parents=True, exist_ok=True)

        # Generate RSA private key (2048-bit for faster tests)
        subprocess.run(
            [
                "openssl", "genrsa",
                "-out", str(self.private_key_file),
                "2048",
            ],
            check=True,
            capture_output=True,
        )
        self.private_key_file.chmod(0o600)
        logger.info("  Generated private key: %s", self.private_key_file)

        # Extract public key
        subprocess.run(
            [
                "openssl", "rsa",
                "-in", str(self.private_key_file),
                "-pubout",
                "-out", str(self.public_key_file),
            ],
            check=True,
            capture_output=True,
        )
        self.public_key_file.chmod(0o644)
        logger.info("  Generated public key: %s", self.public_key_file)
        logger.info("JWT keys generated successfully")

    def cleanup(self) -> None:
        """Clean up vault files."""
        logger.info("Cleaning up vault files at: %s", self.base_dir)
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
        logger.info("Vault cleanup complete")


class ServerManager:
    """Manages FastAPI server lifecycle for integration tests."""

    REQUIRED_PACKAGES = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "PyJWT",
        "argon2-cffi",
        "pyyaml",
        "httpx",
        "python-multipart",
        "jsonschema",
        "ansible",
        "cryptography",
        "dependency-injector",
    ]

    def __init__(  # noqa: R0913,R0917 pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        host: str,
        port: int,
        vault_manager: VaultManager,  # noqa: W0621
        project_dir: str,  # noqa: W0621
        venv_dir: str,  # noqa: W0621
    ):
        """Initialize server manager.

        Args:
            host: Server host.
            port: Server port.
            vault_manager: Vault manager instance.
            project_dir: Path to build_stream project directory.
            venv_dir: Path to virtual environment directory.
        """
        self.host = host
        self.port = port
        self.vault_manager = vault_manager
        self.project_dir = project_dir
        self.venv_dir = Path(venv_dir)
        self.process: Optional[subprocess.Popen] = None

    def _setup_venv(self) -> None:
        """Create virtual environment and install dependencies."""
        logger.info("Setting up Python virtual environment...")
        logger.info("  Venv directory: %s", self.venv_dir)

        if not self.venv_dir.exists():
            logger.info("  Creating virtual environment...")
            subprocess.run(
                ["python3", "-m", "venv", str(self.venv_dir)],
                check=True,
                capture_output=True,
            )
            logger.info("  Virtual environment created")
        else:
            logger.info("  Virtual environment already exists")

        pip_path = self.venv_dir / "bin" / "pip"
        logger.info("  Upgrading pip...")
        subprocess.run(
            [str(pip_path), "install", "--upgrade", "pip", "-q"],
            check=True,
            capture_output=True,
        )

        logger.info("  Installing dependencies: %s", ", ".join(self.REQUIRED_PACKAGES))
        subprocess.run(
            [str(pip_path), "install", "-q"] + self.REQUIRED_PACKAGES,
            check=True,
            capture_output=True,
        )
        logger.info("  Dependencies installed successfully")

    @property
    def python_path(self) -> str:
        """Get path to Python executable in virtual environment."""
        return str(self.venv_dir / "bin" / "python")

    def _is_port_in_use(self) -> bool:
        """Check if the port is already in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((self.host, self.port)) == 0

    def _free_port(self) -> None:
        """Free the port if it's in use."""
        if self._is_port_in_use():
            try:
                result = subprocess.run(
                    ["lsof", "-t", f"-i:{self.port}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.stdout.strip():
                    for pid in result.stdout.strip().split("\n"):
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except (ProcessLookupError, ValueError):
                            pass
                    time.sleep(1)
            except FileNotFoundError:
                pass

    def start(self) -> None:
        """Start the FastAPI server."""
        logger.info("Starting FastAPI server...")
        self._setup_venv()

        logger.info("  Freeing port %d if in use...", self.port)
        self._free_port()

        logger.info("  Configuring server environment variables...")
        env = os.environ.copy()
        env.update({
            "HOST": self.host,
            "PORT": str(self.port),
            "ANSIBLE_VAULT_PASSWORD_FILE": str(self.vault_manager.vault_pass_file),
            "OAUTH_CLIENTS_VAULT_PATH": str(self.vault_manager.vault_file),
            "AUTH_CONFIG_VAULT_PATH": str(self.vault_manager.vault_file),
            "JWT_PRIVATE_KEY_PATH": str(self.vault_manager.private_key_file),
            "JWT_PUBLIC_KEY_PATH": str(self.vault_manager.public_key_file),
            "LOG_LEVEL": "DEBUG",
            "PYTHONPATH": str(self.project_dir),
        })
        logger.info("    HOST=%s", self.host)
        logger.info("    PORT=%s", self.port)
        logger.info("    ANSIBLE_VAULT_PASSWORD_FILE=%s", self.vault_manager.vault_pass_file)
        logger.info("    OAUTH_CLIENTS_VAULT_PATH=%s", self.vault_manager.vault_file)
        logger.info("    AUTH_CONFIG_VAULT_PATH=%s", self.vault_manager.vault_file)
        logger.info("    JWT_PRIVATE_KEY_PATH=%s", self.vault_manager.private_key_file)
        logger.info("    JWT_PUBLIC_KEY_PATH=%s", self.vault_manager.public_key_file)
        logger.info("    LOG_LEVEL=DEBUG")
        logger.info("    PYTHONPATH=%s", self.project_dir)

        logger.info("  Starting uvicorn server...")
        logger.info("    Python: %s", self.python_path)
        logger.info("    Working directory: %s", self.project_dir)

        # Process needs to be managed separately for start/stop lifecycle
        # Cannot use 'with' statement as process must persist after method returns
        self.process = subprocess.Popen(  # noqa: R1732
            [
                self.python_path,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                self.host,
                "--port",
                str(self.port),
            ],
            cwd=self.project_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger.info("  Server process started with PID: %d", self.process.pid)

        self._wait_for_server()

    def _wait_for_server(self) -> None:
        """Wait for server to be ready."""
        logger.info("  Waiting for server to be ready (timeout: %ds)...",
                    IntegrationTestConfig.SERVER_STARTUP_TIMEOUT)

        start_time = time.time()
        while time.time() - start_time < IntegrationTestConfig.SERVER_STARTUP_TIMEOUT:
            try:
                response = httpx.get(
                    f"http://{self.host}:{self.port}/health",
                    timeout=1.0,
                )
                if response.status_code == 200:
                    elapsed = time.time() - start_time
                    logger.info("  Server is ready! (took %.1fs)", elapsed)
                    logger.info("  Server URL: http://%s:%d", self.host, self.port)
                    return
            except httpx.RequestError:
                pass
            time.sleep(0.5)

        # Log server output before stopping
        if self.process:
            logger.error("Server failed to start. Checking process output...")
            if self.process.stdout:
                stdout_output = self.process.stdout.read().decode()
                logger.error("Server STDOUT:\n%s", stdout_output)
            if self.process.stderr:
                stderr_output = self.process.stderr.read().decode()
                logger.error("Server STDERR:\n%s", stderr_output)

            # Check process return code
            self.process.poll()
            if self.process.returncode is not None:
                logger.error("Server process exited with code: %s", self.process.returncode)

        self.stop()
        raise RuntimeError(
            f"Server failed to start within {IntegrationTestConfig.SERVER_STARTUP_TIMEOUT}s"
        )

    def stop(self) -> None:
        """Stop the FastAPI server."""
        logger.info("Stopping FastAPI server...")
        if self.process:
            logger.info("  Terminating server process (PID: %d)...", self.process.pid)
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
                logger.info("  Server stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.info("  Server did not stop gracefully, killing...")
                self.process.kill()
                self.process.wait()
                logger.info("  Server killed")
            self.process = None

        self._free_port()
        logger.info("Server shutdown complete")

    @property
    def base_url(self) -> str:
        """Get the server base URL."""
        return f"http://{self.host}:{self.port}"


@pytest.fixture(scope="module")
def integration_test_dir() -> Generator[str, None, None]:
    """Create a temporary directory for integration test files.

    Yields:
        Path to temporary directory.
    """
    temp_dir = tempfile.mkdtemp(prefix="build_stream_integration_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def vault_manager(
    integration_test_dir: str,
    auth_password: str,
) -> Generator[VaultManager, None, None]:  # noqa: W0621
    """Create and configure vault manager.

    Args:
        integration_test_dir: Temporary directory for test files.
        auth_password: The auth password to use for vault setup.

    Yields:
        Configured VaultManager instance.
    """
    manager = VaultManager(integration_test_dir)
    manager.setup(
        username=IntegrationTestConfig.AUTH_USERNAME,
        password=auth_password,
    )
    yield manager
    manager.cleanup()


@pytest.fixture(scope="module")
def project_dir() -> str:
    """Get the build_stream project directory.

    Returns:
        Path to build_stream project directory.
    """
    return str(Path(__file__).parent.parent.parent.parent)


@pytest.fixture(scope="module")
def venv_dir(integration_test_dir: str) -> str:  # noqa: W0621
    """Get path to virtual environment directory.

    Args:
        integration_test_dir: Temporary directory for test files.

    Returns:
        Path to virtual environment directory.
    """
    return os.path.join(integration_test_dir, "venv")


@pytest.fixture(scope="module")
def server_manager(
    vault_manager: VaultManager,  # noqa: W0621
    project_dir: str,  # noqa: W0621
    venv_dir: str,  # noqa: W0621
) -> Generator[ServerManager, None, None]:
    """Create and manage the FastAPI server.

    Args:
        vault_manager: Vault manager fixture.
        project_dir: Project directory fixture.
        venv_dir: Virtual environment directory fixture.

    Yields:
        Running ServerManager instance.
    """
    manager = ServerManager(
        host=IntegrationTestConfig.SERVER_HOST,
        port=IntegrationTestConfig.SERVER_PORT,
        vault_manager=vault_manager,
        project_dir=project_dir,
        venv_dir=venv_dir,
    )
    manager.start()
    yield manager
    manager.stop()


@pytest.fixture(scope="module")
def base_url(server_manager: ServerManager) -> str:  # noqa: W0621
    """Get the server base URL.

    Args:
        server_manager: Server manager fixture.

    Returns:
        Server base URL.
    """
    return server_manager.base_url


@pytest.fixture(scope="module")
def auth_password() -> str:
    """Generate a single auth password for the entire test module.

    Returns:
        Auth password to be used consistently across tests.
    """
    return IntegrationTestConfig.get_auth_password()


@pytest.fixture
def valid_auth_header(auth_password: str) -> Dict[str, str]:  # noqa: W0621
    """Create valid Basic Auth header.

    Args:
        auth_password: The auth password to use.

    Returns:
        Dictionary with Authorization header.
    """
    credentials = base64.b64encode(
        f"{IntegrationTestConfig.AUTH_USERNAME}:{auth_password}".encode()
    ).decode()
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def invalid_auth_header() -> Dict[str, str]:
    """Create invalid Basic Auth header.

    Returns:
        Dictionary with invalid Authorization header.
    """
    credentials = base64.b64encode(b"wrong_user:wrong_password").decode()
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def reset_vault(
    vault_manager: VaultManager,
    auth_password: str,
) -> Generator[None, None, None]:  # noqa: W0621
    """Reset vault to initial state before and after test.

    Args:
        vault_manager: Vault manager fixture.
        auth_password: The auth password to use for vault setup.

    Yields:
        None
    """
    vault_manager.setup(
        username=IntegrationTestConfig.AUTH_USERNAME,
        password=auth_password,
    )
    yield
    vault_manager.setup(
        username=IntegrationTestConfig.AUTH_USERNAME,
        password=auth_password,
    )
