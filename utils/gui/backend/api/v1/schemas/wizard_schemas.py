"""Schemas for wizard configuration API."""

from pydantic import BaseModel


class DownloadFilesRequest(BaseModel):
    """Request model for download-files endpoint."""
    input_dir: str
