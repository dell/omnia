"""
Custom exception classes for Config Editor Module

Provides domain-specific exceptions for better error handling and user feedback.
"""

from typing import Optional, Any


class ConfigEditorException(Exception):
    """Base exception for Config Editor errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AdapterPolicyNotFoundError(ConfigEditorException):
    """Raised when an adapter policy is not found."""
    
    def __init__(self, policy_type: str = "custom", details: Optional[dict[str, Any]] = None):
        super().__init__(
            f"Adapter policy not found: {policy_type}",
            status_code=404,
            details=details
        )
        self.policy_type = policy_type


class GenerationError(ConfigEditorException):
    """Raised when configuration generation fails."""
    
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            f"Configuration generation failed: {message}",
            status_code=500,
            details=details
        )



