import { z } from 'zod';

// Filter Config Schema
const filterConfigSchema: z.ZodType<{
  type?: 'substring' | 'allowlist' | 'field_in' | 'any_of';
  field?: string;
  values?: string[];
  case_sensitive?: boolean;
  filters?: any[];
}> = z.object({
  type: z.enum(['substring', 'allowlist', 'field_in', 'any_of']).optional(),
  field: z.string().optional().default('package'),
  values: z.array(z.string()).optional(),
  case_sensitive: z.boolean().optional().default(false),
  filters: z.array(z.any()).min(1, 'At least one filter is required for any_of type').optional(),
}).refine((data) => {
  // If filter type is any_of, filters must be provided
  if (data.type === 'any_of' && (!data.filters || data.filters.length === 0)) {
    return false;
  }
  // If filter type is any_of, values should not be used
  if (data.type === 'any_of' && data.values && data.values.length > 0) {
    return false;
  }
  // If filter type is not any_of, values must be provided when type is provided
  if (data.type && data.type !== 'any_of' && (!data.values || data.values.length === 0)) {
    return false;
  }
  // If filters array is provided, it must have at least one item
  if (data.filters && data.filters.length === 0) {
    return false;
  }
  return true;
}, {
  message: 'Invalid filter configuration',
});

// Pull Config Schema
const pullConfigSchema = z.object({
  source_key: z.string().min(1, 'Source key is required'),
  target_key: z.string().optional(),
  filter: filterConfigSchema.optional(),
  transform: z.object({
    exclude_fields: z.array(z.string()).optional(),
    rename_fields: z.record(z.string(), z.string()).optional(),
  }).optional(),
}).refine((data) => {
  // If filter type is provided, validate target_key is also provided
  if (data.filter?.type && !data.target_key) {
    return false;
  }
  return true;
}, {
  message: 'Target key is required when filter is applied',
});

// Source Config Schema
const sourceConfigSchema = z.object({
  source_file: z.string().min(1, 'Source file is required'),
  pulls: z.array(pullConfigSchema).min(1, 'At least one pull is required'),
});

// Derived Operation Schema
const derivedSchema = z.object({
  target_key: z.string(),
  operation: z.object({
    type: z.literal('extract_common'),
    from_keys: z.array(z.string()).min(2, 'At least 2 keys are required for comparison'),
    min_occurrences: z.number().default(2),
    remove_from_sources: z.boolean().default(true),
  }),
});

// Target Config Schema
const targetConfigSchema = z.object({
  transform: z.object({
    exclude_fields: z.array(z.string()).optional(),
    rename_fields: z.record(z.string(), z.string()).optional(),
  }).optional(),
  sources: z.array(sourceConfigSchema).min(1, 'At least one source is required'),
  derived: z.array(derivedSchema).optional(),
  conditions: z.object({
    architectures: z.array(z.string()).optional(),
    os_versions: z.array(z.string()).optional(),
    os_families: z.array(z.string()).optional(),
  }).optional(),
});

// Adapter Policy Schema
export const adapterPolicySchema = z.object({
  version: z.string().default('2.0.0'),
  description: z.string().optional(),
  architectures: z.array(z.string()).min(1).optional().refine((arr) => {
    if (!arr) return true;
    const unique = new Set(arr);
    return unique.size === arr.length;
  }, {
    message: 'Architectures must be unique',
  }),
  targets: z.record(z.string(), targetConfigSchema),
}).refine((data) => {
  // Ensure at least one target is defined
  if (!data.targets || Object.keys(data.targets).length === 0) {
    return false;
  }
  return true;
}, {
  message: 'At least one target is required',
});

export type AdapterPolicyFormData = z.infer<typeof adapterPolicySchema>;






