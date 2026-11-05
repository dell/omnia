# Image Build Manager -- Security

## S3 Bucket Access in Airgap Deployments

The `efi` and `boot-images` S3 buckets are configured with public-read access to enable PXE boot clients to fetch kernel, initramfs, and EFI artifacts without authentication. Boot images contain OS packages and configurations but are not sensitive data.

In air-gapped deployments, the OIM (Omnia Infrastructure Manager) environment is isolated from external networks, and the S3 service is accessible only within the internal provisioning network. The security boundary is established through network isolation, which ensures that boot artifacts remain protected from unauthorized external access. This approach enables seamless PXE boot functionality while leveraging the airgap environment's inherent security.
