"""
Adapter Policy Service for Config Editor Module

Provides business logic for adapter policy management.
"""

from pathlib import Path
from typing import Dict, Optional, Any
import logging

from ..config.settings import get_settings
from ..utils.file_io import read_json, write_json
from ..core.exceptions import AdapterPolicyNotFoundError

logger = logging.getLogger(__name__)


class AdapterPolicyService:
    """Service for managing adapter policies."""
    
    def __init__(self, settings=None):
        """Initialize the service.
        
        Args:
            settings: Optional settings instance. If None, uses default.
        """
        self.settings = settings or get_settings()
        self.gui_dir = self.settings.gui_dir
        self.build_stream_dir = self.settings.build_stream_dir
        
        self.custom_policy_path = self.gui_dir / "backend" / "resources" / "adapter_policy_custom.json"
        self.default_policy_path = self.build_stream_dir / "core" / "catalog" / "resources" / "adapter_policy_default.json"
        
        logger.debug("AdapterPolicyService initialized with custom=%s, default=%s",
                    self.custom_policy_path, self.default_policy_path)

    def __repr__(self) -> str:
        return f"AdapterPolicyService(custom={self.custom_policy_path})"
    
    def get_adapter_policy(self) -> Dict[str, Any]:
        """Get the current adapter policy (custom or default).
        
        Returns:
            Dictionary containing policy data and source
        """
        for source, policy_path in [("custom", self.custom_policy_path),
                                     ("default", self.default_policy_path)]:
            try:
                policy_data = read_json(policy_path)
                logger.debug("Loaded %s adapter policy from %s (%d keys)",
                             source, policy_path,
                             len(policy_data) if isinstance(policy_data, dict) else 0)
                return {"policy": policy_data, "source": source}
            except FileNotFoundError:
                continue
            except (OSError, ValueError) as e:
                logger.exception("Failed to load %s adapter policy", source)
                raise AdapterPolicyNotFoundError(source, details={"error": str(e)})

        raise AdapterPolicyNotFoundError("default", details={"error": "No policy file found"})
    
    def save_adapter_policy(self, policy: Dict[str, Any]) -> None:
        """Save adapter policy to custom policy file.
        
        Args:
            policy: Policy data to save
        """
        self.custom_policy_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            write_json(self.custom_policy_path, policy)
            logger.info("Saved adapter policy to %s", self.custom_policy_path)
        except Exception as e:
            logger.exception("Failed to save adapter policy")
            raise
    
    def delete_adapter_policy(self) -> None:
        """Delete custom adapter policy (reverts to default)."""
        try:
            self.custom_policy_path.unlink()
            logger.info("Deleted custom adapter policy: %s", self.custom_policy_path)
        except FileNotFoundError:
            logger.warning("Custom adapter policy does not exist, nothing to delete")
