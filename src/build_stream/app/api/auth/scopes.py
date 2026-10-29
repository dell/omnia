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

"""OAuth scope vocabulary shared by registration, token issue and route guards.

Only scopes that at least one route enforces are grantable, so a client can
never hold a scope whose meaning is undefined.
"""

CATALOG_READ = "catalog:read"
CATALOG_WRITE = "catalog:write"
JOB_READ = "job:read"
JOB_WRITE = "job:write"

GRANTABLE_SCOPES = frozenset({CATALOG_READ, CATALOG_WRITE, JOB_READ, JOB_WRITE})
