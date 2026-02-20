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

"""API router that aggregates all API modules."""

from fastapi import APIRouter

from api.auth.routes import router as auth_router
from api.generate_input_files.routes import router as generate_input_files_router
from api.jobs.routes import router as jobs_router
from api.local_repo.routes import router as local_repo_router
from api.parse_catalog.routes import router as parse_catalog_router
from api.build_image.routes import router as build_image_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(parse_catalog_router)
api_router.include_router(generate_input_files_router)
api_router.include_router(jobs_router)
api_router.include_router(local_repo_router)
api_router.include_router(build_image_router)
