# cleanup_build_artifacts

Cleans up build artifacts, temporary files, MinIO data, registry storage, and credentials from the image build process.

## Requirements

- Root privileges for file and service cleanup

## Role Variables

See `vars/main.yml` for the full list.

## Dependencies

None.

## Example

```yaml
- hosts: localhost
  roles:
    - cleanup_build_artifacts
```
