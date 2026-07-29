import { z } from 'zod';
import { IPV4_PATTERN, URL_PATTERN } from './common';

// --- Reusable patterns ---
const MOUNT_NAME_PATTERN = /^[a-zA-Z0-9_-]{1,64}$/;
const ABSOLUTE_PATH_PATTERN = /^\/\S+$/;
const DUMP_FREQ_PATTERN = /^[0-2]$/;
const FSCK_PASS_PATTERN = /^[0-9]$/;
const OCTAL_MODE_PATTERN = /^[0-7]{3,4}$/;
const HEX_PATTERN = /^[a-fA-F0-9]+$/;
const IQN_PATTERN = /^iqn\.\d{4}-\d{2}\.[a-zA-Z0-9.-]+:[a-zA-Z0-9._:-]+$/;
const SWAP_SIZE_PATTERN = /^(auto|\d+|[1-9]\d*[GMK])$/;
const SWAP_MAXSIZE_PATTERN = /^(\d+|[1-9]\d*[GMK])$/;

const FS_TYPES = ['auto','ext2','ext3','ext4','xfs','nfs','nfs4','cifs',
                  'tmpfs','cephfs','vfat','ntfs','none','fuse.s3fs'] as const;
const PV_FS_TYPES = ['xfs','ext4','ext3','ext2','nfs','nfs4','cifs','ntfs','auto'] as const;
const NODE_KEY_VALUES = ['local_hostname','local_ipv4','instance_id'] as const;

// --- Permissions sub-schema ---
const permissionsSchema = z.object({
  owner: z.string().default('root'),
  group: z.string().default('root'),
  mode: z.string().default('0755').refine(val => !val || val === '' || OCTAL_MODE_PATTERN.test(val), { message: 'Octal 3-4 digits, e.g. 0755' }),
}).optional();

// --- Helper to convert comma-separated string to array ---
const commaStringToArray = (value: any) => {
  if (typeof value === 'string') {
    return value.split(',').map(s => s.trim()).filter(s => s.length > 0);
  }
  if (Array.isArray(value)) {
    return value;
  }
  return [];
};

// --- Mount entry (loose for disabled state; strict validation applied via superRefine when _ui_showMounts is true)
const mountEntrySchema = z.object({
  name: z.string().optional(),
  source: z.string().optional(),
  mount_point: z.string().optional(),
  mount_params: z.string().optional(),                       // profile name reference
  fs_type: z.enum(FS_TYPES).or(z.literal('')).optional(),
  mnt_opts: z.string().optional(),
  dump_freq: z.string().optional().refine(val => !val || val === '' || DUMP_FREQ_PATTERN.test(val), { message: 'Must be 0, 1, or 2' }),
  fsck_pass: z.string().optional().refine(val => !val || val === '' || FSCK_PASS_PATTERN.test(val), { message: 'Must be 0-9' }),
  mount_on_oim: z.boolean().default(false),
  node_key: z.union([z.enum(NODE_KEY_VALUES), z.literal('')]).default('').optional().transform(val => val === '' ? undefined : val),
  node_mount_point: z.any().transform(commaStringToArray).pipe(z.array(z.string().regex(ABSOLUTE_PATH_PATTERN, 'Absolute path'))).optional(),
  functional_group_prefix: z.any().transform(commaStringToArray).pipe(z.array(z.string())).optional(),
  groups: z.any().transform(commaStringToArray).pipe(z.array(z.string())).optional(),
  permissions: permissionsSchema,
});

// Strict mount entry schema for validation when Mounts is enabled
const strictMountEntrySchema = z.object({
  name: z.string().regex(MOUNT_NAME_PATTERN, 'Alphanumeric/underscore/dash, 1-64 chars'),
  source: z.string().min(1, 'Source is required'),
  mount_point: z.string().regex(ABSOLUTE_PATH_PATTERN, 'Must be an absolute path'),
  mount_params: z.string().optional(),
  fs_type: z.enum(FS_TYPES).or(z.literal('')).optional(),
  mnt_opts: z.string().optional(),
  dump_freq: z.string().optional().refine(val => !val || val === '' || DUMP_FREQ_PATTERN.test(val), { message: 'Must be 0, 1, or 2' }),
  fsck_pass: z.string().optional().refine(val => !val || val === '' || FSCK_PASS_PATTERN.test(val), { message: 'Must be 0-9' }),
  mount_on_oim: z.boolean().default(false),
  node_key: z.union([z.enum(NODE_KEY_VALUES), z.literal('')]).default('').optional().transform(val => val === '' ? undefined : val),
  node_mount_point: z.any().transform(commaStringToArray).pipe(z.array(z.string().regex(ABSOLUTE_PATH_PATTERN, 'Absolute path'))).optional(),
  functional_group_prefix: z.any().transform(commaStringToArray).pipe(z.array(z.string().min(1))).optional(),
  groups: z.any().transform(commaStringToArray).pipe(z.array(z.string().min(1))).optional(),
  permissions: permissionsSchema,
})
.refine(d => !(d.functional_group_prefix?.length && d.groups?.length),
  { message: 'functional_group_prefix and groups are mutually exclusive', path: ['groups'] })
.refine(d => (d.functional_group_prefix?.length ?? 0) > 0 || (d.groups?.length ?? 0) > 0,
  { message: 'Either functional_group_prefix or groups is required', path: ['functional_group_prefix'] })
.refine(d => !d.node_key || (d.node_mount_point && d.node_mount_point.length > 0),
  { message: 'node_mount_point is required when node_key is set', path: ['node_mount_point'] });

// --- Mount params profile ---
const mountParamProfileSchema = z.object({
  fs_type: z.enum(FS_TYPES),                                // mandatory in profile
  mnt_opts: z.string().min(1, 'Mount options required'),     // mandatory in profile
  dump_freq: z.string().optional().refine(val => !val || val === '' || DUMP_FREQ_PATTERN.test(val), { message: 'Must be 0, 1, or 2' }),
  fsck_pass: z.string().optional().refine(val => !val || val === '' || FSCK_PASS_PATTERN.test(val), { message: 'Must be 0-9' }),
});

// --- Mount params profile entry (loose for disabled state; strict validation applied via superRefine when _ui_showMountParams is true)
const mountParamProfileEntrySchema = z.object({
  profile_name: z.string().optional(),
  fs_type: z.enum(FS_TYPES).optional(),
  mnt_opts: z.string().optional(),
  dump_freq: z.string().optional().refine(val => !val || val === '' || DUMP_FREQ_PATTERN.test(val), { message: 'Must be 0, 1, or 2' }),
  fsck_pass: z.string().optional().refine(val => !val || val === '' || FSCK_PASS_PATTERN.test(val), { message: 'Must be 0-9' }),
});

// Strict mount params profile entry schema for validation when Mount Params is enabled
const strictMountParamProfileEntrySchema = z.object({
  profile_name: z.string().min(1, 'Profile name is required'),
  fs_type: z.enum(FS_TYPES),
  mnt_opts: z.string().min(1, 'Mount options required'),
  dump_freq: z.string().optional().refine(val => !val || val === '' || DUMP_FREQ_PATTERN.test(val), { message: 'Must be 0, 1, or 2' }),
  fsck_pass: z.string().optional().refine(val => !val || val === '' || FSCK_PASS_PATTERN.test(val), { message: 'Must be 0-9' }),
});

// --- PowerVault entry (loose for disabled state; strict validation applied via superRefine when _ui_showPowerVault is true)
const powervaultEntrySchema = z.object({
  name: z.string().optional(),
  ip: z.any().transform(commaStringToArray).pipe(z.array(z.string())).optional(),
  port: z.coerce.number().optional().refine(val => val === undefined || val === null || val === 0 || (typeof val === 'number' && val >= 1 && val <= 65535), { message: 'Port must be between 1 and 65535' }).default(3260),
  iscsi_initiator: z.string().optional(),
  volume_id: z.string().optional(),
  mount_point: z.string().optional(),
  mount_params: z.string().optional(),
  fs_type: z.enum(PV_FS_TYPES).or(z.literal('')).optional(),
  mnt_opts: z.string().optional(),
  dump_freq: z.string().optional().refine(val => !val || val === '' || DUMP_FREQ_PATTERN.test(val), { message: 'Must be 0, 1, or 2' }),
  fsck_pass: z.string().optional().refine(val => !val || val === '' || FSCK_PASS_PATTERN.test(val), { message: 'Must be 0-9' }),
  node_key: z.union([z.enum(NODE_KEY_VALUES), z.literal('')]).default('').optional().transform(val => val === '' ? undefined : val),
  node_mount_point: z.any().transform(commaStringToArray).pipe(z.array(z.string().regex(ABSOLUTE_PATH_PATTERN))).optional(),
  functional_group_prefix: z.any().transform(commaStringToArray).pipe(z.array(z.string())).optional(),
  permissions: permissionsSchema,
});

// Strict PowerVault entry schema for validation when PowerVault is enabled
const strictPowervaultEntrySchema = z.object({
  name: z.string().regex(MOUNT_NAME_PATTERN, 'Alphanumeric/underscore/dash, 1-64 chars'),
  ip: z.any().transform(commaStringToArray).pipe(z.array(z.string().regex(IPV4_PATTERN)).min(1, 'At least 1 IP required')),
  port: z.coerce.number().optional().refine(val => val === undefined || val === null || val === 0 || (typeof val === 'number' && val >= 1 && val <= 65535), { message: 'Port must be between 1 and 65535' }).default(3260),
  iscsi_initiator: z.string().regex(IQN_PATTERN, 'IQN format: iqn.YYYY-MM.domain:id'),
  volume_id: z.string().regex(HEX_PATTERN, 'Hex string'),
  mount_point: z.string().regex(ABSOLUTE_PATH_PATTERN, 'Absolute path'),
  mount_params: z.string().optional(),
  fs_type: z.enum(PV_FS_TYPES).or(z.literal('')).optional(),
  mnt_opts: z.string().optional(),
  dump_freq: z.string().optional().refine(val => !val || val === '' || DUMP_FREQ_PATTERN.test(val), { message: 'Must be 0, 1, or 2' }),
  fsck_pass: z.string().optional().refine(val => !val || val === '' || FSCK_PASS_PATTERN.test(val), { message: 'Must be 0-9' }),
  node_key: z.union([z.enum(NODE_KEY_VALUES), z.literal('')]).default('').optional().transform(val => val === '' ? undefined : val),
  node_mount_point: z.any().transform(commaStringToArray).pipe(z.array(z.string().regex(ABSOLUTE_PATH_PATTERN))).optional(),
  functional_group_prefix: z.any().transform(commaStringToArray).pipe(z.array(z.string().min(1))).refine(d => d.length > 0, { message: 'Functional Group Prefix is required' }),
  permissions: permissionsSchema,
})
.refine(d => !d.node_key || (d.node_mount_point && d.node_mount_point.length > 0),
  { message: 'node_mount_point required when node_key is set', path: ['node_mount_point'] });

// --- Swap entry (loose for disabled state; strict validation applied via superRefine when _ui_showSwap is true)
const swapEntrySchema = z.object({
  name: z.string().optional(),
  filename: z.string().optional(),
  size: z.string().optional(),
  maxsize: z.string().optional(),
  functional_group_prefix: z.any().transform(commaStringToArray).pipe(z.array(z.string())).optional(),
});

// Strict Swap entry schema for validation when Swap is enabled
const strictSwapEntrySchema = z.object({
  name: z.string().optional().refine(val => !val || val === '' || MOUNT_NAME_PATTERN.test(val), { message: 'Alphanumeric/underscore/dash, 1-64 chars' }),
  filename: z.string().regex(ABSOLUTE_PATH_PATTERN, 'Absolute path to swap file'),
  size: z.string().regex(SWAP_SIZE_PATTERN, '"auto", byte integer, or human-readable e.g. "2G"'),
  maxsize: z.string().optional().refine(val => !val || val === '' || SWAP_MAXSIZE_PATTERN.test(val), { message: 'Byte integer or human-readable e.g. "4G"' }),
  functional_group_prefix: z.any().transform(commaStringToArray).pipe(z.array(z.string().min(1))).optional(),
})
.refine(d => (d.functional_group_prefix?.length ?? 0) > 0,
  { message: 'functional_group_prefix is required', path: ['functional_group_prefix'] })
.refine(d => d.size !== 'auto' || (d.maxsize && d.maxsize.length > 0),
  { message: 'maxsize is required when size is "auto"', path: ['maxsize'] });

// --- S3 configuration (always required; strict validation applied via superRefine)
const s3ConfigSchema = z.object({
  provider: z.enum(['powerscale', 'minio']).default('powerscale'),
  endpoint_url: z.string().optional().or(z.literal('')),
});

// Strict S3 configuration schema for validation when S3 is enabled
const strictS3ConfigSchema = z.object({
  provider: z.enum(['powerscale', 'minio']).default('powerscale'),
  endpoint_url: z.string().regex(URL_PATTERN, 'Must be a valid URL (e.g., https://10.43.1.11:9021)').optional().or(z.literal('')),
})
.refine(d => d.provider !== 'powerscale' || (d.endpoint_url && d.endpoint_url.length > 0),
  { message: 'endpoint_url is required when provider is powerscale', path: ['endpoint_url'] });

// --- Top-level schema ---
export const storageConfigSchema = z.object({
  mounts: z.array(mountEntrySchema).optional().default([]),
  mount_params: z.record(z.string(), mountParamProfileSchema).optional().default({}),
  _mount_params_entries: z.array(mountParamProfileEntrySchema).optional().default([]), // UI helper array
  powervault_config: z.array(powervaultEntrySchema).optional().default([]),
  swap: z.array(swapEntrySchema).optional().default([]),
  s3_configurations: s3ConfigSchema.optional().default({ provider: 'powerscale', endpoint_url: '' }),
  _ui_showMounts: z.boolean().optional(),
  _ui_showMountParams: z.boolean().optional(),
  _ui_showPowerVault: z.boolean().optional(),
  _ui_showSwap: z.boolean().optional(),
}).superRefine((data, ctx) => {
  if (data._ui_showMounts) {
    data.mounts?.forEach((mount, index) => {
      const result = strictMountEntrySchema.safeParse(mount);
      if (!result.success && result.error) {
        result.error.issues.forEach((issue) => {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: issue.message,
            path: ['mounts', index, ...issue.path],
          });
        });
      }
    });
  }

  if (data._ui_showMountParams) {
    data._mount_params_entries?.forEach((entry, index) => {
      const result = strictMountParamProfileEntrySchema.safeParse(entry);
      if (!result.success && result.error) {
        result.error.issues.forEach((issue) => {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: issue.message,
            path: ['_mount_params_entries', index, ...issue.path],
          });
        });
      }
    });
  }

  if (data._ui_showPowerVault) {
    data.powervault_config?.forEach((entry, index) => {
      const result = strictPowervaultEntrySchema.safeParse(entry);
      if (!result.success && result.error) {
        result.error.issues.forEach((issue) => {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: issue.message,
            path: ['powervault_config', index, ...issue.path],
          });
        });
      }
    });
  }

  if (data._ui_showSwap) {
    data.swap?.forEach((entry, index) => {
      const result = strictSwapEntrySchema.safeParse(entry);
      if (!result.success && result.error) {
        result.error.issues.forEach((issue) => {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: issue.message,
            path: ['swap', index, ...issue.path],
          });
        });
      }
    });
  }

  if (data.s3_configurations) {
    const result = strictS3ConfigSchema.safeParse(data.s3_configurations);
    if (!result.success && result.error) {
      result.error.issues.forEach((issue) => {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: issue.message,
          path: ['s3_configurations', ...issue.path],
        });
      });
    }
  }

  // Storage Configuration is mandatory: at least one option must be configured
  const hasConfiguredStorage =
    data._ui_showMounts ||
    data._ui_showMountParams ||
    data._ui_showPowerVault ||
    data._ui_showSwap ||
    data.s3_configurations != null ||
    data.mounts?.some((m: any) => m.name?.trim() || m.source?.trim() || m.mount_point?.trim()) ||
    data._mount_params_entries?.some((e: any) => e.profile_name?.trim()) ||
    Object.keys(data.mount_params || {}).length > 0 ||
    data.powervault_config?.some((p: any) => p.name?.trim()) ||
    data.swap?.some((s: any) => s.filename?.trim());

  if (!hasConfiguredStorage) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Please configure at least one storage option (Mounts, Mount Params, PowerVault, Swap, or S3)',
      path: ['storage'],
    });
  }
});

export type StorageConfigFormData = z.infer<typeof storageConfigSchema>;
