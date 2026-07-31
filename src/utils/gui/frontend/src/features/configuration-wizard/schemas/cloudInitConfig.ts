// Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
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
