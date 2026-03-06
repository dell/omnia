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

"""Database configuration module."""

import os
from typing import Optional


class DatabaseConfig:
    """Database configuration from environment variables."""

    def __init__(self):
        self.database_url: str = os.getenv("DATABASE_URL", "")
        self.pool_size: int = int(os.getenv("DB_POOL_SIZE", "20"))
        self.max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        self.pool_recycle: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))
        self.echo: bool = os.getenv("DB_ECHO", "false").lower() == "true"

    def validate(self) -> None:
        """Validate required configuration."""
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")


# Global config instance
db_config = DatabaseConfig()
