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

"""SVT test case registry: stable IDs, titles and order.

ID format ``SVT_<THEME>_<SEQ>`` (theme upper-case); IDs are never reused.
Order: theme base + position (build_stream 1000).
"""

TEST_CASES = {
    # build_stream theme
    "build_stream_build_deploy": {
        "id": "SVT_BUILD_STREAM_001", "order": 1001,
        "title": "BuildStream build and deploy: base domains, BuildStream, GitLab, "
                 "build pipeline and the deploy of its image",
    },
    "build_stream_cadence": {
        "id": "SVT_BUILD_STREAM_002", "order": 1002,
        "title": "BuildStream cadence: new image, cadence cycle and cadence pipeline",
    },
    "build_stream_automatic_cleanup": {
        "id": "SVT_BUILD_STREAM_003", "order": 1003,
        "title": "BuildStream automatic cleanup of the cadence image (S3, registry, NFS)",
    },
}
