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

"""Ansible Vault client for secure credential storage and retrieval."""

import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class VaultError(Exception):
    """Base exception for vault operations."""


class VaultDecryptError(VaultError):
    """Exception raised when vault decryption fails."""


class VaultEncryptError(VaultError):
    """Exception raised when vault encryption fails."""


class VaultNotFoundError(VaultError):
    """Exception raised when vault file is not found."""


class VaultClient:  # pylint: disable=too-few-public-methods
    """Client for interacting with Ansible Vault encrypted files."""

    def __init__(
        self,
        vault_password_file: Optional[str] = None,
        oauth_clients_vault_path: Optional[str] = None,
        auth_config_vault_path: Optional[str] = None,
    ):
        """Initialize the Vault client.

        Args:
            vault_password_file: Path to the Ansible Vault password file.
            oauth_clients_vault_path: Path to the OAuth clients vault file.
            auth_config_vault_path: Path to the auth configuration vault file.
        """
        self.vault_password_file = vault_password_file or os.getenv(
            "ANSIBLE_VAULT_PASSWORD_FILE", "/etc/omnia/.vault_pass"
        )
        self.oauth_clients_vault_path = oauth_clients_vault_path or os.getenv(
            "OAUTH_CLIENTS_VAULT_PATH",
            "/etc/omnia/input/project_default/build_stream_oauth_credentials.yml"
        )
        self.auth_config_vault_path = auth_config_vault_path or os.getenv(
            "AUTH_CONFIG_VAULT_PATH",
            "/etc/omnia/input/project_default/build_stream_oauth_credentials.yml"
        )

    _ALLOWED_VAULT_COMMANDS = frozenset({"view", "encrypt", "decrypt"})

    def _run_vault_command(
        self,
        command: str,
        vault_path: str,
    ) -> str:
        """Run an ansible-vault command.

        Args:
            command: The vault command (view, encrypt, decrypt).
            vault_path: Path to the vault file.

        Returns:
            Command output as string.

        Raises:
            VaultError: If command is not in allowlist.
            VaultNotFoundError: If vault file doesn't exist.
            VaultDecryptError: If decryption fails.
            VaultEncryptError: If encryption fails.
        """
        if command not in self._ALLOWED_VAULT_COMMANDS:
            raise VaultError("Invalid vault command")

        if command == "view" and not os.path.exists(vault_path):
            raise VaultNotFoundError(f"Vault file not found: {vault_path}")

        if not os.path.exists(self.vault_password_file):
            raise VaultError(f"Vault password file not found: {self.vault_password_file}")

        cmd = [
            "ansible-vault",
            command,
            vault_path,
            "--vault-password-file",
            self.vault_password_file,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            return result.stdout
        except subprocess.CalledProcessError:
            logger.error("Vault command failed: %s", command)
            if command == "view":
                raise VaultDecryptError("Failed to decrypt vault") from None
            raise VaultEncryptError("Failed to encrypt vault") from None
        except subprocess.TimeoutExpired:
            logger.error("Vault command timed out: %s", command)
            raise VaultError("Vault operation timed out") from None

    def read_vault(self, vault_path: str) -> Dict[str, Any]:
        """Read and decrypt a vault file.

        Args:
            vault_path: Path to the vault file.

        Returns:
            Decrypted vault contents as dictionary.

        Raises:
            VaultNotFoundError: If vault file doesn't exist.
            VaultDecryptError: If decryption fails.
        """
        logger.debug("Reading vault: %s", vault_path)
        output = self._run_vault_command("view", vault_path)
        try:
            return yaml.safe_load(output) or {}
        except yaml.YAMLError:
            logger.error("Failed to parse vault YAML")
            raise VaultDecryptError("Invalid vault content format") from None

    def write_vault(self, vault_path: str, data: Dict[str, Any]) -> None:
        """Write data to an encrypted vault file.

        Args:
            vault_path: Path to the vault file.
            data: Data to encrypt and store.

        Raises:
            VaultEncryptError: If encryption fails.
        """
        logger.debug("Writing vault: %s", vault_path)

        yaml_content = yaml.safe_dump(data, default_flow_style=False)

        vault_dir = os.path.dirname(vault_path)
        if vault_dir and not os.path.exists(vault_dir):
            os.makedirs(vault_dir, mode=0o700, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yml",
            delete=False,
            encoding="utf-8",
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = temp_file.name

        try:
            logger.debug("Encrypting temp file: %s", temp_path)
            encrypt_cmd = [
                "ansible-vault",
                "encrypt",
                temp_path,
                "--vault-password-file",
                self.vault_password_file,
                "--encrypt-vault-id",
                "default",
            ]
            subprocess.run(
                encrypt_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            logger.debug("Encryption completed, reading encrypted content")

            with open(temp_path, "r", encoding="utf-8") as f:
                encrypted_content = f.read()

            with open(vault_path, "w", encoding="utf-8") as f:
                f.write(encrypted_content)

            os.chmod(vault_path, 0o600)
            logger.debug("Vault written successfully")

        except subprocess.CalledProcessError:
            raise VaultEncryptError("Failed to encrypt vault") from None
        except subprocess.TimeoutExpired:
            logger.error("Vault encryption timed out")
            raise VaultError("Vault operation timed out") from None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def get_auth_config(self) -> Dict[str, Any]:
        """Get authentication configuration from vault.

        Returns:
            Auth configuration dictionary containing registration credentials.

        Raises:
            VaultNotFoundError: If auth config vault doesn't exist.
            VaultDecryptError: If decryption fails.
        """
        return self.read_vault(self.auth_config_vault_path)

    def get_oauth_clients(self) -> Dict[str, Any]:
        """Get OAuth clients from vault.

        Returns:
            Dictionary of registered OAuth clients.

        Raises:
            VaultNotFoundError: If OAuth clients vault doesn't exist.
            VaultDecryptError: If decryption fails.
        """
        try:
            data = self.read_vault(self.oauth_clients_vault_path)
            return data.get("oauth_clients", {})
        except VaultNotFoundError:
            return {}

    def save_oauth_client(
        self,
        client_id: str,
        client_data: Dict[str, Any],
    ) -> None:
        """Save a new OAuth client to vault.

        Args:
            client_id: The client identifier.
            client_data: Client data including hashed secret and metadata.

        Raises:
            VaultEncryptError: If encryption fails.
        """
        try:
            existing_data = self.read_vault(self.oauth_clients_vault_path)
        except VaultNotFoundError:
            existing_data = {"oauth_clients": {}}

        if "oauth_clients" not in existing_data:
            existing_data["oauth_clients"] = {}

        existing_data["oauth_clients"][client_id] = client_data

        self.write_vault(self.oauth_clients_vault_path, existing_data)
        logger.info("OAuth client saved: %s", client_id[:8] + "...")

    def get_active_client_count(self) -> int:
        """Get the count of active registered clients.

        Returns:
            Number of active clients.
        """
        clients = self.get_oauth_clients()
        return sum(1 for c in clients.values() if c.get("is_active", True))

    def client_exists(self, client_name: str) -> bool:
        """Check if a client with the given name already exists.

        Args:
            client_name: The client name to check.

        Returns:
            True if client exists, False otherwise.
        """
        clients = self.get_oauth_clients()
        for client_data in clients.values():
            if client_data.get("client_name") == client_name:
                return True
        return False
