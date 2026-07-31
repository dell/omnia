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
import { IPV4_PATTERN } from './common';

// Combined schema for both GitLab and Build Stream
export const buildStreamGitLabSchema = z.object({
  // Build Stream fields
  enable_build_stream: z.boolean().default(false),
  build_stream_host_ip: z.union([
    z.literal(''),
    z.string().regex(IPV4_PATTERN, 'Must be a valid IPv4 address'),
  ]).default(''),
  build_stream_port: z.coerce.number().min(1).max(65535).default(8010),
  aarch64_inventory_host_ip: z.union([
    z.literal(''),
    z.string().regex(IPV4_PATTERN, 'Must be a valid IPv4 address'),
  ]).optional(),

  // GitLab fields (with defaults matching input/gitlab_config.yml)
  enable_gitlab: z.boolean().default(false),
  gitlab_host: z.string().default(''),
  gitlab_project_name: z.string().default('omnia-catalog'),
  gitlab_project_visibility: z.enum(['private', 'internal', 'public']).default('private'),
  gitlab_default_branch: z.string().default('main'),
  gitlab_https_port: z.coerce.number().min(1).max(65535).default(443),
  gitlab_min_storage_gb: z.coerce.number().min(20).default(20),
  gitlab_min_memory_gb: z.coerce.number().min(1).default(4),
  gitlab_min_cpu_cores: z.coerce.number().min(1).default(2),
  gitlab_puma_workers: z.coerce.number().min(1).default(2),
  gitlab_sidekiq_concurrency: z.coerce.number().min(1).default(10),
})
  .refine(
    (data) => {
      if (!data.enable_build_stream) return true;
      return !!data.build_stream_host_ip && data.build_stream_host_ip.length > 0;
    },
    { message: 'Build Stream Host IP is required', path: ['build_stream_host_ip'] }
  )
  .refine(
    (data) => {
      if (!data.enable_gitlab) return true;
      return !!data.gitlab_host && IPV4_PATTERN.test(data.gitlab_host);
    },
    { message: 'GitLab Host IP is required and must be valid IPv4', path: ['gitlab_host'] }
  )
  .refine(
    (data) => {
      if (!data.enable_gitlab) return true;
      return !!data.gitlab_project_name && data.gitlab_project_name.trim().length > 0;
    },
    { message: 'GitLab Project Name is required', path: ['gitlab_project_name'] }
  );

export type BuildStreamGitLabFormData = z.infer<typeof buildStreamGitLabSchema>;
