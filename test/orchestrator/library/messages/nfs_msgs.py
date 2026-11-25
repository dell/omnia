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
    "need_root": "emptying an NFS share needs root (mount). HOW TO FIX: run the test as root "
                 "on the execution OIM",
    "no_mount_nfs": "mount.nfs is not installed. HOW TO FIX: install nfs-utils on the OIM",
    "bad_source": "NFS share {name}: {why}. HOW TO FIX: set a source like "
                  "<server ip or name>:/<export path> in the mounts of "
                  "clusters/<cluster>/inputs/orchestrator/storage_config.yml",
    "denied": "NFS share {name}: the export path {export} is a system directory and is never "
              "emptied",
    "protected": "NFS share {name}: the export {export} is on this OIM and contains {path}, "
                 "which Omnia needs; it is not emptied",
    "mount_failed": "NFS share {name}: cannot mount {source}: {reason}. HOW TO FIX: check that "
                    "the server answers, the share is exported to this OIM and nfs-utils is "
                    "installed; or set the matching cleanup_slurm / cleanup_k8s to false in "
                    "test_config.yml",
    "mount_mismatch": "NFS share {name}: {mountpoint} is not the NFS mount of {source} after "
                      "mounting (found {found}); nothing was deleted",
    "empty_failed": "NFS share {name}: {count} entries are still in {source} after {attempts} "
                    "attempts: {first}{hint}",
    "squash_hint": ". The export probably squashes root: it needs no_root_squash for this OIM",
    "unmount_failed": "NFS share {name}: {mountpoint} is still mounted ({reason}). HOW TO FIX: "
                      "umount -l {mountpoint}; then remove the folder",
    "retry": "  {name}: {count} entries are still in the share (attempt {number} of "
             "{total}); emptying it again in {pause}s",
    "clients": "WARNING: {clients} are connected to this NFS server; what they still write "
               "to the share is deleted again, and can make the cleanup fail",
    "clients_hint": ". Still written by a connected client ({clients}): stop what writes to "
                    "the share (on a Kubernetes node, kubelet), then run the scenario again",
    "need_local_root": "the NFS shares are mounted by the execution OIM: run this test "
                       "locally as root on it (oim_server_ip empty or the OIM itself)",
    "flag_off": "{flag} is false in test_config.yml: the data of the {name} share is kept "
                "and nothing is deleted",
    "no_share": "{name} is not an NFS mount of {path}: nothing to empty",
    "config_missing": "storage_config.yml not found at {path}, so the {name} share cannot be "
                      "checked. HOW TO FIX: run ./omnia.sh --init orchestrator (or restore the "
                      "file) and rerun the cleanup scenario",
    "emptied": "emptied {name} ({source}): removed {files} files, {dirs} directories; no "
               "entry left after {attempts} attempt(s)",
    "detached": "{name}: {mount_point} is unmounted and has no fstab entry",
    "still_mounted": "{mount_point} is still mounted",
    "still_in_fstab": "/etc/fstab still has an entry for {mount_point}",
    "source_mounted": "{source} is still mounted at {targets}",
    "source_in_fstab": "/etc/fstab still has an entry for {source}",
    "not_detached": "NFS share {name} is still attached ({problems}). HOW TO FIX: run the "
                    "orchestrator cleanup (--tags cleanup) so that it unmounts the share and "
                    "removes its fstab entry; nothing was deleted",
    "attached_after": "NFS share {name} is attached after it was emptied ({problems}); the "
                      "cleanup must leave it unmounted and out of fstab",
    "all_empty": "{name} has no entry left",
    "left": "{name} still has {count} entries after the cleanup",
    "too_deep": "directory tree deeper than {depth} levels",
}
