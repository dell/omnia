import { useCatalogStore } from '../catalogStore';

const CatalogOverview = () => {
  const catalogRoot = useCatalogStore((s) => s.catalogRoot);
  const setCatalogRoot = useCatalogStore((s) => s.setCatalogRoot);

  if (!catalogRoot) return <p>No catalog loaded</p>;

  const inner = catalogRoot.Catalog;

  const updateMetadata = (
    field: 'Name' | 'Version' | 'Identifier',
    value: string,
  ) => {
    setCatalogRoot({
      ...catalogRoot,
      Catalog: { ...inner, [field]: value },
    });
  };

  return (
    <div className="p-8">
      <h2>Catalog Overview</h2>

      <div className="mb-4">
        <h3>Metadata</h3>
        <div className="grid-2-col">
          <div className="form-group">
            <label className="form-label">Name:</label>
            <input
              type="text"
              value={inner.Name}
              onChange={(e) =>
                updateMetadata('Name', e.target.value)
              }
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Version:</label>
            <input
              type="text"
              value={inner.Version}
              onChange={(e) =>
                updateMetadata('Version', e.target.value)
              }
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Identifier:</label>
            <input
              type="text"
              value={inner.Identifier}
              onChange={(e) =>
                updateMetadata('Identifier', e.target.value)
              }
              className="form-input"
            />
          </div>
        </div>
      </div>

      <div className="mb-4">
        <h3>Statistics</h3>
        <div className="grid-2-col">
          <div className="text-small-muted">
            Functional Layers:{' '}
            {inner.FunctionalLayer.length}
          </div>
          <div className="text-small-muted">
            Functional Packages:{' '}
            {Object.keys(inner.FunctionalPackages).length}
          </div>
          <div className="text-small-muted">
            OS Packages:{' '}
            {Object.keys(inner.OSPackages).length}
          </div>
          <div className="text-small-muted">
            Infrastructure Packages:{' '}
            {
              Object.keys(inner.InfrastructurePackages)
                .length
            }
          </div>
        </div>
      </div>
    </div>
  );
};

export default CatalogOverview;
