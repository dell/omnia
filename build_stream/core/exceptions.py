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

"""Core exceptions for the Build Stream API."""


class ClientDisabledError(Exception):
    """Exception raised when client account is disabled."""


class InvalidClientError(Exception):
    """Exception raised when client credentials are invalid."""


class InvalidScopeError(Exception):
    """Exception raised when requested scope is not allowed."""


class TokenCreationError(Exception):
    """Exception raised when token creation fails."""
