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

"""
Functional Verification Tests (FVT) for build_stream.

Tags (run in this order):
    prepare_base  ./omnia.sh --prepare-base (explicit, multi-hour)
    precheck      build_stream.yml --tags precheck
    prepare       build_stream.yml --tags prepare
    execute       build_stream.yml --tags execute, GitLab checks, then the
                  build, deploy, cadence and cleanup pipeline suites
    cleanup       build_stream.yml --tags cleanup (explicit, destructive)
"""
