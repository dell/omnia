import { z } from 'zod';

const ABSOLUTE_PATH_PATTERN = /^\/\S+$/;
const OCTAL_PERMS_PATTERN = /^[0-7]{3,4}$/;

// --- write_files entry ---
const writeFileEntrySchema = z.object({
  path: z.string().regex(ABSOLUTE_PATH_PATTERN, 'Must be an absolute path'),
  content: z.string().min(1, 'Content is required'),
  permissions: z.string().regex(OCTAL_PERMS_PATTERN, 'Octal 3-4 digits, e.g. 0644').optional(),
});

// --- runcmd entry ---
const runcmdEntrySchema = z.object({
  command: z.string(),
});

// --- Cloud-init section (common or per-group) ---
const cloudInitSectionSchema = z.object({
  write_files: z.array(writeFileEntrySchema).optional().default([]),
  runcmd: z.array(runcmdEntrySchema).optional().default([]),
}).strict(); // Strict mode to reject additional properties like bootcmd, network, etc.

// --- Top-level schema ---
export const cloudInitConfigSchema = z.object({
  cloud_init_common: cloudInitSectionSchema.optional().default({ write_files: [], runcmd: [] }),
  cloud_init_groups: z.array(z.object({
    group_name: z.string().min(1, 'Group name is required'),
    write_files: z.array(writeFileEntrySchema).optional().default([]),
    runcmd: z.array(runcmdEntrySchema).optional().default([]),
  })).optional().default([]),
});

export type CloudInitConfigFormData = z.infer<typeof cloudInitConfigSchema>;
