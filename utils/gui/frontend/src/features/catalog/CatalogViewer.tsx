import { useState, useRef, ChangeEvent, DragEvent } from 'react';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import type { CatalogRoot } from '../catalog-editor/schemas/catalogSchema';

interface CatalogSectionProps {
  title: string;
  count: number;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  collapsedItems: string[];
}

const CatalogSection = ({ title, count, expanded, onToggle, children, collapsedItems }: CatalogSectionProps) => (
  <div className="catalog-section">
    <div className="section-header-expandable">
      <h3>{title} ({count})</h3>
      <button className="button-expand" onClick={onToggle}>
        {expanded ? '▼' : '▶'}
      </button>
    </div>
    {expanded ? children : (
      <div className="collapsed-view">
        {collapsedItems.map((item, idx) => (
          <span key={idx} className="collapsed-item">{item}</span>
        ))}
      </div>
    )}
  </div>
);

const CatalogViewer = () => {
  const [catalogData, setCatalogData] = useState<CatalogRoot | null>(null);
  const [catalogFileName, setCatalogFileName] = useState<string>('');
  const [parseError, setParseError] = useState<string | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Expand/collapse state for each section
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  const processFile = async (file: File) => {
    if (!file.name.endsWith('.json')) {
      setParseError('Please upload a JSON file');
      return;
    }

    setIsParsing(true);
    setParseError(null);

    try {
      const text = await file.text();
      
      if (!text.trim()) {
        setParseError('File is empty');
        return;
      }

      const json = JSON.parse(text);
      
      // Validate catalog structure
      if (!json.Catalog) {
        setParseError('Invalid catalog file: Missing "Catalog" object');
        return;
      }
      
      if (!json.Catalog.Name) {
        setParseError('Invalid catalog file: Missing "Name" field in Catalog');
        return;
      }
      
      if (!json.Catalog.Version) {
        setParseError('Invalid catalog file: Missing "Version" field in Catalog');
        return;
      }
      
      if (!json.Catalog.Identifier) {
        setParseError('Invalid catalog file: Missing "Identifier" field in Catalog');
        return;
      }
      
      setCatalogData(json);
      setCatalogFileName(file.name.replace('.json', ''));
    } catch (error) {
      if (error instanceof SyntaxError) {
        setParseError('Invalid JSON file: File contains malformed JSON syntax');
      } else {
        setParseError(error instanceof Error ? error.message : 'Failed to parse catalog file');
      }
    } finally {
      setIsParsing(false);
    }
  };

  const handleFileUpload = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragEnter = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  };

  const renderFunctionalLayer = (catalog: CatalogRoot['Catalog']) => {
    const sectionId = 'functional-layer';
    const isExpanded = expandedSections.has(sectionId);
    return (
      <CatalogSection
        title="Functional Layer"
        count={catalog.FunctionalLayer?.length || 0}
        expanded={isExpanded}
        onToggle={() => toggleSection(sectionId)}
        collapsedItems={catalog.FunctionalLayer?.map(layer => layer.Name) || []}
      >
        {catalog.FunctionalLayer?.map((layer, idx) => (
          <div key={idx} className="layer-item">
            <h4>{layer.Name}</h4>
            <div className="functional-packages-list">
              {layer.FunctionalPackages?.map((pkg, pkgIdx) => (
                <span key={pkgIdx} className="package-tag">{pkg}</span>
              ))}
            </div>
          </div>
        ))}
      </CatalogSection>
    );
  };

  const renderBaseOS = (catalog: CatalogRoot['Catalog']) => {
    const sectionId = 'base-os';
    const isExpanded = expandedSections.has(sectionId);
    return (
      <CatalogSection
        title="Base OS"
        count={catalog.BaseOS?.length || 0}
        expanded={isExpanded}
        onToggle={() => toggleSection(sectionId)}
        collapsedItems={catalog.BaseOS?.map(os => `${os.Name} ${os.Version}`) || []}
      >
        {catalog.BaseOS?.map((os, idx) => (
          <div key={idx} className="os-item">
            <strong>{os.Name} {os.Version}</strong>
            <div className="os-packages-list">
              {os.osPackages?.map((pkg, pkgIdx) => (
                <span key={pkgIdx} className="package-tag">{pkg}</span>
              ))}
            </div>
          </div>
        ))}
      </CatalogSection>
    );
  };

  const renderInfrastructure = (catalog: CatalogRoot['Catalog']) => {
    const sectionId = 'infrastructure';
    const isExpanded = expandedSections.has(sectionId);
    return (
      <CatalogSection
        title="Infrastructure"
        count={catalog.Infrastructure?.length || 0}
        expanded={isExpanded}
        onToggle={() => toggleSection(sectionId)}
        collapsedItems={catalog.Infrastructure?.map(infra => infra.Name) || []}
      >
        {catalog.Infrastructure?.map((infra, idx) => (
          <div key={idx} className="infra-item">
            <h4>{infra.Name}</h4>
            <div className="infra-packages-list">
              {infra.InfrastructurePackages?.map((pkg, pkgIdx) => (
                <span key={pkgIdx} className="package-tag">{pkg}</span>
              ))}
            </div>
          </div>
        ))}
      </CatalogSection>
    );
  };

  const renderFunctionalPackages = (catalog: CatalogRoot['Catalog']) => {
    const sectionId = 'functional-packages';
    const isExpanded = expandedSections.has(sectionId);
    const packages = Object.entries(catalog.FunctionalPackages || {});
    return (
      <CatalogSection
        title="Functional Packages"
        count={packages.length}
        expanded={isExpanded}
        onToggle={() => toggleSection(sectionId)}
        collapsedItems={packages.map(([id]) => id)}
      >
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Version</th>
              <th>Type</th>
              <th>Architecture</th>
            </tr>
          </thead>
          <tbody>
            {packages.map(([id, pkg]) => (
              <tr key={id}>
                <td>{id}</td>
                <td>{pkg.Name}</td>
                <td>{pkg.Version || '—'}</td>
                <td>{pkg.Type}</td>
                <td>{pkg.Architecture?.join(', ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CatalogSection>
    );
  };

  const renderOSPackages = (catalog: CatalogRoot['Catalog']) => {
    const sectionId = 'os-packages';
    const isExpanded = expandedSections.has(sectionId);
    const packages = Object.entries(catalog.OSPackages || {});
    return (
      <CatalogSection
        title="OS Packages"
        count={packages.length}
        expanded={isExpanded}
        onToggle={() => toggleSection(sectionId)}
        collapsedItems={packages.map(([id]) => id)}
      >
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Version</th>
              <th>Type</th>
              <th>Architecture</th>
            </tr>
          </thead>
          <tbody>
            {packages.map(([id, pkg]) => (
              <tr key={id}>
                <td>{id}</td>
                <td>{pkg.Name}</td>
                <td>{pkg.Version || '—'}</td>
                <td>{pkg.Type}</td>
                <td>{pkg.Architecture?.join(', ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CatalogSection>
    );
  };

  const renderInfrastructurePackages = (catalog: CatalogRoot['Catalog']) => {
    const sectionId = 'infrastructure-packages';
    const isExpanded = expandedSections.has(sectionId);
    const packages = Object.entries(catalog.InfrastructurePackages || {});
    return (
      <CatalogSection
        title="Infrastructure Packages"
        count={packages.length}
        expanded={isExpanded}
        onToggle={() => toggleSection(sectionId)}
        collapsedItems={packages.map(([id]) => id)}
      >
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Version</th>
              <th>Type</th>
              <th>Architecture</th>
            </tr>
          </thead>
          <tbody>
            {packages.map(([id, pkg]) => (
              <tr key={id}>
                <td>{id}</td>
                <td>{pkg.Name}</td>
                <td>{pkg.Version || '—'}</td>
                <td>{pkg.Type}</td>
                <td>{pkg.Architecture?.join(', ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CatalogSection>
    );
  };

  const renderDriverPackages = (catalog: CatalogRoot['Catalog']) => {
    const sectionId = 'driver-packages';
    const isExpanded = expandedSections.has(sectionId);
    const packages = Object.entries(catalog.DriverPackages || {});
    return (
      <CatalogSection
        title="Driver Packages"
        count={packages.length}
        expanded={isExpanded}
        onToggle={() => toggleSection(sectionId)}
        collapsedItems={packages.map(([id]) => id)}
      >
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Version</th>
              <th>Type</th>
              <th>Architecture</th>
            </tr>
          </thead>
          <tbody>
            {packages.map(([id, pkg]) => (
              <tr key={id}>
                <td>{id}</td>
                <td>{pkg.Name}</td>
                <td>{pkg.Version}</td>
                <td>{pkg.Type}</td>
                <td>{pkg.Architecture?.join(', ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CatalogSection>
    );
  };

  const renderDrivers = (catalog: CatalogRoot['Catalog']) => {
    if (!catalog.Drivers || catalog.Drivers.length === 0) return null;
    const sectionId = 'drivers';
    const isExpanded = expandedSections.has(sectionId);
    return (
      <CatalogSection
        title="Drivers Layer"
        count={catalog.Drivers.length}
        expanded={isExpanded}
        onToggle={() => toggleSection(sectionId)}
        collapsedItems={catalog.Drivers.map(driver => driver.Name)}
      >
        {catalog.Drivers.map((driver, idx) => (
          <div key={idx} className="layer-item">
            <h4>{driver.Name}</h4>
            <div className="functional-packages-list">
              {driver.DriverPackages?.map((pkg, pkgIdx) => (
                <span key={pkgIdx} className="package-tag">{pkg}</span>
              ))}
            </div>
          </div>
        ))}
      </CatalogSection>
    );
  };

  const renderMiscellaneous = (catalog: CatalogRoot['Catalog']) => {
    if (!catalog.Miscellaneous || catalog.Miscellaneous.length === 0) return null;
    const sectionId = 'miscellaneous';
    const isExpanded = expandedSections.has(sectionId);
    return (
      <CatalogSection
        title="Miscellaneous"
        count={catalog.Miscellaneous.length}
        expanded={isExpanded}
        onToggle={() => toggleSection(sectionId)}
        collapsedItems={catalog.Miscellaneous}
      >
        <ul>
          {catalog.Miscellaneous.map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
      </CatalogSection>
    );
  };

  return (
    <Layout>
      <h1>Catalog Parser & Viewer</h1>
      <p className="mb-6">Upload a catalog JSON file to parse and view its structure and contents.</p>

      {!catalogData ? (
        <div className="card">
          <h2>Upload Catalog File</h2>
          <div
            className={`dropzone ${isDragging ? 'dropzone-active' : ''}`}
            onDragOver={handleDragOver}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              className="visually-hidden"
              onChange={handleFileUpload}
            />
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <h3>Drag & Drop or Click to Upload</h3>
            <p>Supported format: JSON catalog file</p>
          </div>

          {isParsing && (
            <div className="catalog-details-loading">
              <LoadingSpinner size="small" />
              <p>Parsing catalog file...</p>
            </div>
          )}

          {parseError && (
            <div className="catalog-error">
              {parseError}
            </div>
          )}
        </div>
      ) : (
        <div className="card">
          <div className="catalog-details-header">
            <h2>Catalog: {catalogFileName}</h2>
            <div className="catalog-meta">
              <span className="catalog-version">v{catalogData.Catalog.Version}</span>
              <span className="catalog-id">{catalogData.Catalog.Identifier}</span>
            </div>
            <button className="button button-secondary" onClick={() => {
              setCatalogData(null);
              setCatalogFileName('');
            }}>
              Upload New File
            </button>
          </div>

          {renderFunctionalLayer(catalogData.Catalog)}
          {renderBaseOS(catalogData.Catalog)}
          {renderInfrastructure(catalogData.Catalog)}
          {renderDrivers(catalogData.Catalog)}
          {renderFunctionalPackages(catalogData.Catalog)}
          {renderOSPackages(catalogData.Catalog)}
          {renderInfrastructurePackages(catalogData.Catalog)}
          {renderDriverPackages(catalogData.Catalog)}
          {renderMiscellaneous(catalogData.Catalog)}
        </div>
      )}
    </Layout>
  );
};

export default CatalogViewer;
