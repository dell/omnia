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

// Admin Inventory Row schema for Magellan discovery
const adminInventoryRowSchema = z.object({
  SERVICE_TAG: z.string().min(1, 'SERVICE_TAG/BMC_MAC is required'),
  GROUP_NAME: z.string().optional().default(''),
  FUNCTIONAL_GROUP_NAME: z.string().optional().default(''),
  ROW: z.string().optional().default(''),
  RACK: z.string().optional().default(''),
  SLOT: z.string().optional().default(''),
  RANGE: z.string().optional().default(''),
});

// Magellan Discovery Schema
export const magellanDiscoverySchema = z.object({
  admin_inventory_path: z.string().min(1, 'Admin inventory path is required'),
  admin_inventory_data: z.array(adminInventoryRowSchema)
    .min(1, 'At least one inventory row is required'),
});

export type AdminInventoryRow = z.infer<typeof adminInventoryRowSchema>;
export type MagellanDiscoveryFormData = z.infer<typeof magellanDiscoverySchema>;
