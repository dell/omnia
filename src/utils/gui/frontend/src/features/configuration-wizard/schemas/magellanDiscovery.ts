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
