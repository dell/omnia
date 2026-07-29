import { z } from 'zod';

// PXE Mapping Row schema
const pxeMappingRowSchema = z.object({
  FUNCTIONAL_GROUP_NAME: z.string().regex(
    /^[A-Za-z][A-Za-z0-9_]{1,}_(x86_64|aarch64)$/,
    'Functional group name must start with a letter, contain only letters/numbers/underscores, and end with _x86_64 or _aarch64'
  ),
  GROUP_NAME: z.string().min(1, 'GROUP_NAME is required'),
  SERVICE_TAG: z.string().min(1, 'SERVICE_TAG is required'),
  PARENT_SERVICE_TAG: z.string().optional().default(''),
  HOSTNAME: z.string().min(1, 'HOSTNAME is required'),
  ADMIN_MAC: z.string().min(1, 'ADMIN_MAC is required'),
  ADMIN_IP: z.string().min(1, 'ADMIN_IP is required'),
  BMC_MAC: z.string().min(1, 'BMC_MAC is required'),
  BMC_IP: z.string().min(1, 'BMC_IP is required'),
  IB_NIC_NAME: z.string().optional().default(''),
  IB_IP: z.string().optional().default(''),
});

// PXE Functional Groups Schema (based on provision_config.yml)
export const pxeFunctionalGroupsSchema = z.object({
  pxe_mapping_file_path: z.string().min(1, 'PXE mapping file path is required'),
  pxe_mapping_data: z.array(pxeMappingRowSchema)
    .min(1, 'At least one PXE mapping row is required'),
  language: z.string().default('en_US.UTF-8').transform(() => 'en_US.UTF-8' as const),
  default_lease_time: z.coerce
    .number()
    .int('Lease time must be a whole number')
    .min(21600, 'Lease time must be at least 21600 seconds (6 hours)')
    .max(31536000, 'Lease time must be at most 31536000 seconds (1 year)')
    .transform(String)
    .default('86400'),
  dns_enabled: z.boolean().optional(),
  kernel_version_override: z.string().optional(),
  additional_cloud_init_config_file: z.union([
    z.literal(''),
    z.string().regex(/\.(yml|yaml)$/, 'File path must end with .yml or .yaml'),
  ]).optional(),
});

export type PxeFunctionalGroupsFormData = z.infer<typeof pxeFunctionalGroupsSchema>;
