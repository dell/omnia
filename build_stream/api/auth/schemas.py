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

"""Pydantic schemas for OAuth2 authentication API request and response models."""

import re
from datetime import datetime
from enum import Enum
from typing import List, Optional

from fastapi import Form, HTTPException, status
from pydantic import BaseModel, Field, field_validator


class ClientRegistrationRequest(BaseModel):  # pylint: disable=too-few-public-methods
    """Request model for client registration."""

    client_name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique identifier for the client (alphanumeric, hyphens, max 64 chars)",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Human-readable description (max 256 chars)",
    )
    allowed_scopes: Optional[List[str]] = Field(
        default=None,
        description="Requested OAuth scopes (default: ['catalog:read'])",
    )

    @field_validator("client_name")
    @classmethod
    def validate_client_name(cls, v: str) -> str:
        """Validate client_name contains only allowed characters."""
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "client_name must start with alphanumeric and contain only "
                "alphanumeric characters, hyphens, and underscores"
            )
        return v

    @field_validator("allowed_scopes")
    @classmethod
    def validate_scopes(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate that requested scopes are valid."""
        valid_scopes = {"catalog:read", "catalog:write", "admin:read", "admin:write"}
        if v is not None:
            for scope in v:
                if scope not in valid_scopes:
                    raise ValueError(f"Invalid scope: {scope}")
        return v


class ClientRegistrationResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """Response model for successful client registration."""

    client_id: str = Field(
        ...,
        description="Unique client identifier (prefix: bld_)",
    )
    client_secret: str = Field(
        ...,
        description="Client secret (prefix: bld_s_) - shown only once",
    )
    client_name: str = Field(
        ...,
        description="The registered client name",
    )
    allowed_scopes: List[str] = Field(
        ...,
        description="Granted OAuth scopes",
    )
    created_at: datetime = Field(
        ...,
        description="Registration timestamp",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Credential expiration (null = no expiry)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "client_id": "bld_<32_hex_characters>",
                    #"client_secret": "", #Commented out for security
                    "client_name": "example-client-name",
                    "allowed_scopes": ["catalog:read", "catalog:write"],
                    "created_at": "2026-01-21T07:31:00Z",
                    "expires_at": None,
                }
            ]
        }
    }


class AuthErrorResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """OAuth2 error response model following RFC 6749."""

    error: str = Field(
        ...,
        description="Error code (machine-readable)",
    )
    error_description: str = Field(
        ...,
        description="Human-readable error description",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "invalid_credentials",
                    "error_description": "Invalid Basic Auth credentials",
                },
                {
                    "error": "client_exists",
                    "error_description": "Client name already registered",
                },
            ]
        }
    }


class GrantType(str, Enum):
    """Supported OAuth2 grant types."""

    CLIENT_CREDENTIALS = "client_credentials"


class TokenRequest:  # pylint: disable=too-few-public-methods
    """Request model for OAuth2 token endpoint (application/x-www-form-urlencoded)."""

    def __init__(
        self,
        grant_type: GrantType = Form(..., description="OAuth2 grant type"),
        client_id: Optional[str] = Form(default=None, description="Client identifier"),
        client_secret: Optional[str] = Form(default=None, description="Client secret"),
        scope: Optional[str] = Form(default=None, description="Requested scopes"),
    ):
        """Initialize token request from form data."""
        self.grant_type = grant_type
        self.client_id = self._validate_client_id(client_id)
        self.client_secret = self._validate_client_secret(client_secret)
        self.scope = scope

    @staticmethod
    def _validate_client_id(v: Optional[str]) -> Optional[str]:
        """Validate client_id format if provided."""
        if v is not None and not v.startswith("bld_"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=[{
                    "type": "value_error",
                    "loc": ["body", "client_id"],
                    "msg": "client_id must start with 'bld_' prefix",
                }],
            )
        return v

    @staticmethod
    def _validate_client_secret(v: Optional[str]) -> Optional[str]:
        """Validate client_secret format if provided."""
        if v is not None and not v.startswith("bld_s_"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=[{
                    "type": "value_error",
                    "loc": ["body", "client_secret"],
                    "msg": "client_secret must start with 'bld_s_' prefix",
                }],
            )
        return v


class TokenResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """Response model for successful token generation (RFC 6749 compliant)."""

    access_token: str = Field(
        ...,
        description="JWT access token",
    )
    token_type: str = Field(
        default="Bearer",
        description="Token type (always 'Bearer')",
    )
    expires_in: int = Field(
        ...,
        description="Token lifetime in seconds",
    )
    scope: str = Field(
        ...,
        description="Granted scopes (space-separated)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "catalog:read catalog:write",
                }
            ]
        }
    }
