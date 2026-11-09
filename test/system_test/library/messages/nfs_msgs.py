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


"""Messages of the NFS share cleanup (library/functions/nfs_func.py)."""

NFS_MSGS = {
    "plan": "    empty NFS share {name} ({source}): everything inside it is deleted "
            "(mounted on a private temporary folder, emptied, unmounted)",
    "not_configured": "NFS share {name}: not in {path}, nothing to empty",
    "not_nfs": "NFS share {name}: source {source!r} of {path} is not host:/export, so it is "
               "not emptied",
    "no_storage_config": "{path} not found: no NFS share to empty",
    "preflight": "checking that every NFS share can be mounted (read-only), before anything "
                 "is deleted",
    "share_ok": "  {name:<12} {source} reachable, {entries} top-level entries",
    "mount": "  mount {source} on {mountpoint} ({mode})",
    "unmount": "  unmounted {mountpoint}",
    "lazy_unmount": "WARNING: umount {mountpoint} failed ({reason}); detaching it lazily",
    "removed": "  {name}: removed {files} files, {dirs} directories, {size} from {source}",
    "skipped_mounts": "  {name}: left {count} directory(ies) that are other mounts inside the "
                      "share",
    "need_root": "emptying an NFS share needs root (mount). HOW TO FIX: run ./setup_env.sh as "
                 "root",
    "no_mount_nfs": "mount.nfs is not installed. HOW TO FIX: install nfs-utils on the OIM",
    "bad_source": "NFS share {name}: {why}. HOW TO FIX: set a source like "
                  "<server ip or name>:/<export path> in storage_config.yml (user_inputs.yml "
                  "orchestrator.storage_config.mounts)",
    "denied": "NFS share {name}: the export path {export} is a system directory and is never "
              "emptied",
    "protected": "NFS share {name}: the export {export} is on this OIM and contains {path}, "
                 "which the SVT needs; it is not emptied",
    "mount_failed": "NFS share {name}: cannot mount {source}: {reason}. HOW TO FIX: check that "
                    "the server answers, the share is exported to this OIM and nfs-utils is "
                    "installed; or set cleanup.nfs.{flag}: false",
    "mount_mismatch": "NFS share {name}: {mountpoint} is not the NFS mount of {source} after "
                      "mounting (found {found}); nothing was deleted",
    "empty_failed": "NFS share {name}: {count} entries could not be removed from {source}: "
                    "{first}{hint}",
    "squash_hint": ". The export probably squashes root: it needs no_root_squash for this OIM",
    "unmount_failed": "NFS share {name}: {mountpoint} is still mounted ({reason}). HOW TO FIX: "
                      "umount -l {mountpoint}; then remove the folder",
    "too_deep": "directory tree deeper than {depth} levels",
}
