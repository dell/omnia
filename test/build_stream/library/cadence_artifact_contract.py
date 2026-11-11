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

"""Image-engine filename contracts used by cadence FVT verification."""

import re
from pathlib import PurePosixPath


def artifact_basenames_match_engine(engine, artifacts):
    """Return whether artifact paths match the selected producer engine."""
    basenames = {
        key: PurePosixPath(str(artifacts.get(key, ""))).name
        for key in ("image", "kernel", "initrd")
    }

    if engine == "image-builder":
        return bool(
            re.fullmatch(r"rhel[^/]*", basenames["image"])
            and re.fullmatch(r"vmlinuz[^/]*", basenames["kernel"])
            and re.fullmatch(r"initramfs[^/]*", basenames["initrd"])
        )

    if engine != "image-thrillhouse":
        return False
    if basenames["image"] != "rootfs.squashfs":
        return False

    legacy_pair = (
        basenames["kernel"] == "vmlinuz"
        and basenames["initrd"] == "initramfs.img"
    )
    versioned_kernel = re.fullmatch(
        r"vmlinuz-(.+)", basenames["kernel"]
    )
    versioned_pair = bool(
        versioned_kernel
        and basenames["initrd"]
        == f"initramfs-{versioned_kernel.group(1)}.img"
    )
    return legacy_pair or versioned_pair
