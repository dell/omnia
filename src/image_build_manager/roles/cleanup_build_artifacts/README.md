# cleanup_build_artifacts

Cleans up image-build infrastructure and local data. The normal `cleanup` flow
removes local MinIO (unless PowerScale is selected), the local registry,
project output, work/data directories, logs, credentials, and `/root/.s3cfg`.

The full cleanup removes the shared domain `output/` and `log/` roots, so it
affects all projects that use that domain data path.

The separate `cleanup_images.yml` task file deletes matching objects from the
`boot-images` bucket when `s3cmd` and `/root/.s3cfg` exist, and matching
registry tags when `regctl` and managed registry state exist, without removing
services. It supports `cleanup_image_pattern` and the approval bypass
`skip_approval=true`.

The top-level `image_build_manager.yml` validator accepts only the public
`cleanup` and `cleanup_images` tags. The standalone
`playbooks/cleanup/cleanup_image_build_manager.yml` playbook additionally
supports role sub-tags such as `minio`, `registry`, `output`, `s3cmd`,
`credentials`, `data`, and `logs`.

Full cleanup does not delete objects from external PowerScale S3.

## Requirements

- Root privileges for file and service cleanup

## Role Variables

See `vars/main.yml` for the full list.

## Dependencies

No automatic role dependencies are declared. The top-level cleanup playbook
runs `image_build_setup` first to resolve paths and provider configuration.

## Examples

```bash
# Public full cleanup
ansible-playbook image_build_manager.yml --tags cleanup

# Standalone selective cleanup
ansible-playbook cleanup/cleanup_image_build_manager.yml --tags registry
```
