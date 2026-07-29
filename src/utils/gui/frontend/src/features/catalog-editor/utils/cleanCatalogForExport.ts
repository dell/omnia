import type { CatalogRoot, DriverPackage } from '../schemas/catalogSchema';

const cleanPackage = (pkg: any, keepVersion = false, includeSupportedOS = true) => {
  const cleaned: Record<string, any> = {
    Name: pkg.Name,
    Type: pkg.Type,
    Architecture: pkg.Architecture,
  };
  
  if (keepVersion || pkg.Version != null) cleaned.Version = pkg.Version;
  if (pkg.Tag != null) cleaned.Tag = pkg.Tag;
  if (pkg.Uri != null) cleaned.Uri = pkg.Uri;
  
  if (includeSupportedOS && pkg.SupportedOS != null) cleaned.SupportedOS = pkg.SupportedOS;
  
  if (pkg.Sources?.length) {
    cleaned.Sources = pkg.Sources
      .filter((s: any) => s.RepoName != null || s.Uri != null)
      .map(({ RepoName, Uri }: any) => {
        const src: Record<string, string> = {};
        if (RepoName != null) src.RepoName = RepoName;
        if (Uri != null) src.Uri = Uri;
        return src;
      });
    if (cleaned.Sources.length === 0) delete cleaned.Sources;
  }
  
  return cleaned;
};

export function cleanCatalogForExport(catalog: CatalogRoot): CatalogRoot {
  if (!catalog) return catalog;

  const cleaned = JSON.parse(JSON.stringify(catalog));

  // Clean FunctionalPackages
  if (cleaned.Catalog?.FunctionalPackages) {
    Object.keys(cleaned.Catalog.FunctionalPackages).forEach(pkgId => {
      cleaned.Catalog.FunctionalPackages[pkgId] = cleanPackage(
        cleaned.Catalog.FunctionalPackages[pkgId]
      );
    });
  }

  // Clean OSPackages
  if (cleaned.Catalog?.OSPackages) {
    Object.keys(cleaned.Catalog.OSPackages).forEach(pkgId => {
      cleaned.Catalog.OSPackages[pkgId] = cleanPackage(
        cleaned.Catalog.OSPackages[pkgId]
      );
    });
  }

  // Clean InfrastructurePackages
  if (cleaned.Catalog?.InfrastructurePackages) {
    Object.keys(cleaned.Catalog.InfrastructurePackages).forEach(pkgId => {
      cleaned.Catalog.InfrastructurePackages[pkgId] = cleanPackage(
        cleaned.Catalog.InfrastructurePackages[pkgId],
        true,
        false, // InfrastructurePackages don't have SupportedOS
      );
    });
  }

  // Clean DriverPackages (different schema - only required fields)
  if (cleaned.Catalog?.DriverPackages) {
    Object.keys(cleaned.Catalog.DriverPackages).forEach(pkgId => {
      const pkg = cleaned.Catalog.DriverPackages[pkgId];
      // Build explicitly with only required fields
      cleaned.Catalog.DriverPackages[pkgId] = {
        Name: pkg.Name,
        Type: pkg.Type,
        Architecture: pkg.Architecture,
        Version: pkg.Version,
        Uri: pkg.Uri,
        Config: pkg.Config,
      };
    });
  }

  // Auto-derive BaseOS from OSPackages
  if (cleaned.Catalog?.OSPackages) {
    const osPackageIds = Object.keys(cleaned.Catalog.OSPackages).sort();
    
    // Extract OS family and version from first package (or use defaults)
    let osFamily = 'RHEL';
    let osVersion = '10.0';
    
    if (osPackageIds.length > 0) {
      const firstPkg = cleaned.Catalog.OSPackages[osPackageIds[0]];
      if (firstPkg?.SupportedOS && firstPkg.SupportedOS.length > 0) {
        osFamily = firstPkg.SupportedOS[0].Name;
        osVersion = firstPkg.SupportedOS[0].Version;
      }
    }

    // Update BaseOS to match OSPackages
    cleaned.Catalog.BaseOS = [{
      Name: osFamily,
      Version: osVersion,
      osPackages: osPackageIds
    }];
  }

  // Auto-derive Infrastructure from InfrastructurePackages
  if (cleaned.Catalog?.InfrastructurePackages) {
    const infraPackageIds = Object.keys(cleaned.Catalog.InfrastructurePackages).sort();

    // Update Infrastructure to match InfrastructurePackages
    cleaned.Catalog.Infrastructure = [{
      Name: 'csi',
      InfrastructurePackages: infraPackageIds
    }];
  }

  // Auto-derive Drivers from DriverPackages
  if (cleaned.Catalog?.DriverPackages) {
    const driverPackages = cleaned.Catalog.DriverPackages;
    
    // Group driver packages by DriverBrand and DriverType
    // Use null character as separator to avoid conflicts with brand/type values
    const driverGroups = new Map<string, string[]>();
    
    Object.entries(driverPackages).forEach(([pkgId, pkg]) => {
      const driverPkg = pkg as DriverPackage;
      const brand = driverPkg.Config?.DriverBrand || 'unknown';
      const type = driverPkg.Config?.DriverType || 'unknown';
      const key = `${brand}\0${type}`;
      
      if (!driverGroups.has(key)) {
        driverGroups.set(key, []);
      }
      driverGroups.get(key)!.push(pkgId);
    });

    // Create Drivers array from grouped packages
    const drivers = Array.from(driverGroups.entries()).map(([key, packageIds]) => {
      const [brand, type] = key.split('\0');
      return {
        Name: `${brand} ${type}`,
        DriverPackages: packageIds.sort()
      };
    });

    // Update Drivers section
    cleaned.Catalog.Drivers = drivers;
  }

  return cleaned as CatalogRoot;
}
