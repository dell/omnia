import type { CatalogRoot } from '../schemas/catalogSchema';

export const EMPTY_CATALOG: CatalogRoot = {
  Catalog: {
    Name: 'Catalog',
    Version: '1.0',
    Identifier: 'image-build',
    FunctionalLayer: [],
    BaseOS: [{ Name: 'RHEL', Version: '10.0', osPackages: [] }],
    Infrastructure: [{ Name: 'csi', InfrastructurePackages: [] }],
    Drivers: [],
    DriverPackages: {},
    FunctionalPackages: {},
    OSPackages: {},
    InfrastructurePackages: {},
    Miscellaneous: [],
  },
};
