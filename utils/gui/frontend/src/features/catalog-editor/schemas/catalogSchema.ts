import { z } from 'zod';
import { URL_PATTERN } from '../../configuration-wizard/schemas/common';

// ─── Enums ─────────────────────────────────────────────────

export const PackageType = z.enum([
  'rpm',
  'rpm_repo',
  'tarball',
  'iso',
  'git',
  'image',
  'pip_module',
  'manifest',
]);

// ─── Sub-schemas ───────────────────────────────────────────

export const SupportedOSSchema = z.object({
  Name: z.string().min(1, 'OS Name is required'),
  Version: z.string().min(1, 'OS Version is required'),
});

const sourceBaseSchema = z.object({
  Architecture: z.string().min(1, 'Architecture is required'),
  RepoName: z.string().optional(),
  Uri: z.string().optional(),
});

const sourcePresenceRefine = (data: {
  RepoName?: string;
  Uri?: string;
}): boolean => Boolean(data.RepoName?.trim() || data.Uri?.trim());

const sourceUrlRefine = (data: {
  Uri?: string;
}): boolean => {
  if (!data.Uri?.trim()) return true;
  return URL_PATTERN.test(data.Uri.trim());
};

export const PackageSourceSchema = sourceBaseSchema
  .refine(sourceUrlRefine, {
    message: 'Uri must be a valid URL starting with http:// or https://',
    path: ['Uri'],
  })
  .refine(sourcePresenceRefine, {
    message: 'Either RepoName or Uri is required',
    path: ['Uri'],
  });

export const PackageSourceWithUrlSchema = PackageSourceSchema;

// ─── Package schemas ───────────────────────────────────────

export const FunctionalPackageSchema = z.object({
  Name: z.string().min(1, 'Name is required'),
  Type: PackageType,
  Architecture: z
    .array(z.string().min(1))
    .min(1, 'At least one architecture is required'),
  SupportedOS: z
    .array(SupportedOSSchema)
    .min(1, 'At least one supported OS is required'),
  Sources: z.array(PackageSourceSchema).optional(),
  Version: z.string().optional(),
  Tag: z.string().optional(),
  // Schema 1.1 fields (to be added later):
  // - ApplicableFunctionalLayers: Maps packages to functional layers
  // - Config: Enhanced package metadata
  // - SupportedFunctions: Function metadata
});
export const OSPackageSchema = FunctionalPackageSchema.extend({
  Sources: z.array(PackageSourceWithUrlSchema).optional(),
});

export const MiscellaneousPackageSchema = OSPackageSchema;

export const InfrastructurePackageSchema = z.object({
  Name: z.string().min(1, 'Name is required'),
  Type: PackageType,
  Architecture: z.array(z.string().min(1)).optional(),
  SupportedFunctions: z
    .array(z.object({ Name: z.string().min(1, 'Function name is required') }))
    .min(1, 'At least one supported function is required'),
  Uri: z.string().optional(),
  Sources: z.array(PackageSourceWithUrlSchema).optional(),
  Version: z.string().nullable().optional(),
  Tag: z.string().optional(),
  // Note: SupportedOS and Sources are NOT in the InfrastructurePackages schema
  // Schema 1.1 fields (to be added later):
  // - ApplicableFunctionalLayers: Maps packages to functional layers
  // - Config: Enhanced package metadata
});

// ─── Driver schemas ───────────────────────────────────────────

export const DriverConfigSchema = z.object({
  DriverBrand: z.string().min(1, 'Driver Brand is required'),
  DriverType: z.string().min(1, 'Driver Type is required'),
});

export const DriverPackageSchema = z.object({
  Name: z.string().min(1, 'Name is required'),
  Type: PackageType,
  Architecture: z
    .array(z.string().min(1))
    .min(1, 'At least one architecture is required'),
  Uri: z
    .string()
    .min(1, 'URI is required')
    .refine((val) => URL_PATTERN.test(val), {
      message: 'Uri must be a valid URL starting with http:// or https://',
    }),
  Config: DriverConfigSchema,
  // Note: Tag, SupportedOS, and Sources are NOT in the DriverPackages schema
  // Schema 1.1 field (to be added later):
  // - ApplicableFunctionalLayers: Maps driver packages to functional layers
  Version: z.string().min(1, 'Version is required'),
});

export const DriverSchema = z.object({
  Name: z.string(),
  DriverPackages: z.array(z.string()),
});

// ─── Structural schemas ────────────────────────────────────

export const FunctionalLayerSchema = z.object({
  Name: z.string(),
  Architecture: z.string().optional(),
  FunctionalPackages: z.array(z.string()),
  // Schema 1.1 field (to be added later):
  // - ApplicableFunctionalLayers: Maps layer to other layers (optional)
});

export const BaseOSSchema = z.object({
  Name: z.string(),
  Version: z.string(),
  osPackages: z.array(z.string()),
});

export const InfrastructureSchema = z.object({
  Name: z.string(),
  InfrastructurePackages: z.array(z.string()),
});

// ─── CatalogInner: everything under "Catalog" ──────────────

export const CatalogInnerSchema = z.object({
  // Schema 1.0: Metadata fields
  Name: z.string().default('Catalog'),
  Version: z.string().default('1.0'),
  Identifier: z.string().default('image-build'),
  // Schema 1.1 field (to be added later):
  // - CatalogSchemaVersion: "1.1" when using Schema 1.1 features

  // Schema 1.0: Structural sections
  FunctionalLayer: z.array(FunctionalLayerSchema),
  BaseOS: z.array(BaseOSSchema),
  Infrastructure: z.array(InfrastructureSchema),
  Drivers: z.array(DriverSchema).default([]),
  DriverPackages: z.record(z.string(), DriverPackageSchema).default({}),
  FunctionalPackages: z.record(z.string(), FunctionalPackageSchema),
  OSPackages: z.record(z.string(), OSPackageSchema),
  InfrastructurePackages: z.record(
    z.string(),
    InfrastructurePackageSchema,
  ),
  Miscellaneous: z.array(z.string()).default([]),
});

// ─── CatalogRoot: top-level { "Catalog": { ... } } ─────────

export const CatalogRootSchema = z.object({
  Catalog: CatalogInnerSchema,
});

// ─── Inferred types ────────────────────────────────────────

export type PackageTypeValue = z.infer<typeof PackageType>;
export type SupportedOS = z.infer<typeof SupportedOSSchema>;
export type PackageSource = z.infer<typeof PackageSourceSchema>;
export type PackageSourceWithUrl = z.infer<typeof PackageSourceWithUrlSchema>;
export type FunctionalPackage = z.infer<typeof FunctionalPackageSchema>;
export type OSPackage = z.infer<typeof OSPackageSchema>;
export type MiscellaneousPackage = z.infer<typeof MiscellaneousPackageSchema>;
export type InfrastructurePackage = z.infer<
  typeof InfrastructurePackageSchema
>;
export type DriverConfig = z.infer<typeof DriverConfigSchema>;
export type DriverPackage = z.infer<typeof DriverPackageSchema>;
export type Driver = z.infer<typeof DriverSchema>;
export type FunctionalLayer = z.infer<typeof FunctionalLayerSchema>;
export type BaseOS = z.infer<typeof BaseOSSchema>;
export type InfrastructureType = z.infer<typeof InfrastructureSchema>;
export type CatalogInner = z.infer<typeof CatalogInnerSchema>;
export type CatalogRoot = z.infer<typeof CatalogRootSchema>;
