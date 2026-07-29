"""
Adapter Policy routes for Config Editor Module

Provides API endpoints for adapter policy management.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from ....services.adapter_policy_service import AdapterPolicyService
from ..dependencies import get_adapter_policy_service
from ....core.exceptions import AdapterPolicyNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter()


# Adapter Policy Endpoints
@router.get("/adapter-policy")
async def get_adapter_policy(
    service: AdapterPolicyService = Depends(get_adapter_policy_service)
) -> Dict[str, Any]:
    """Get the current adapter policy (custom or default)."""
    try:
        result = service.get_adapter_policy()
        return result
    except AdapterPolicyNotFoundError as e:
        logger.error("Adapter policy not found: %s", e.policy_type)
        raise HTTPException(404, "Adapter policy not found")
    except Exception:
        logger.exception("Failed to get adapter policy")
        raise HTTPException(500, "Failed to load adapter policy")


@router.post("/adapter-policy")
async def save_adapter_policy(
    policy: Dict[str, Any],
    service: AdapterPolicyService = Depends(get_adapter_policy_service)
) -> Dict[str, str]:
    """Save adapter policy to custom policy file."""
    try:
        service.save_adapter_policy(policy)
        return {"status": "success", "message": "Adapter policy saved successfully"}
    except (OSError, ValueError):
        logger.exception("Failed to save adapter policy")
        raise HTTPException(500, "Failed to save adapter policy")


@router.delete("/adapter-policy")
async def delete_adapter_policy(
    service: AdapterPolicyService = Depends(get_adapter_policy_service)
) -> Dict[str, str]:
    """Delete custom adapter policy (reverts to default)."""
    try:
        service.delete_adapter_policy()
        return {"status": "success", "message": "Custom adapter policy deleted"}
    except (OSError, ValueError):
        logger.exception("Failed to delete adapter policy")
        raise HTTPException(500, "Failed to delete adapter policy")

