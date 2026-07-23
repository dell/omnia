import {
  useValidateCatalog,
  useImportCatalog,
} from './hooks/useCatalog';
import { useCatalogStore } from './catalogStore';
import { useConfigStore } from '../configuration-wizard/configStore';
import { showConfirm } from '../confirmDialog/confirmDialogStore';
import { useNavigate } from 'react-router-dom';
import Layout from '../../components/Layout';
import CatalogOverview from './components/CatalogOverview';
import FunctionalLayerEditor from './components/FunctionalLayerEditor';
import OSPackageEditor from './components/OSPackageEditor';
import InfrastructureEditor from './components/InfrastructureEditor';
import DriverPackageEditor from './components/DriverPackageEditor';
import MiscellaneousEditor from './components/MiscellaneousEditor';
import ValidationPanel from './components/ValidationPanel';
import { extractUserFriendlyErrorMessage } from './utils/extractErrorMessage';
import { EMPTY_CATALOG } from './constants/emptyCatalog';
import { cleanCatalogForExport } from './utils/cleanCatalogForExport';
import { useMemo } from 'react';
import './CatalogEditor.css';

const CatalogEditor = () => {
  const validateCatalog = useValidateCatalog();
  const importCatalog = useImportCatalog();
  const navigate = useNavigate();
  const setWizardData = useConfigStore((s) => s.setWizardData);
  const setActiveStep = useConfigStore((s) => s.setActiveStep);
  const resetWizard = useConfigStore((s) => s.resetWizard);
  const setConfigSource = useConfigStore((s) => s.setConfigSource);
  const setCatalogRoot = useCatalogStore((s) => s.setCatalogRoot);

  const catalogRoot = useCatalogStore((s) => s.catalogRoot);
  const activeSection = useCatalogStore((s) => s.activeSection);
  const setActiveSection = useCatalogStore((s) => s.setActiveSection);
  const validationErrors = useCatalogStore((s) => s.validationErrors);
  const validationWarnings = useCatalogStore((s) => s.validationWarnings);
  const setValidationResults = useCatalogStore((s) => s.setValidationResults);

  // Convenience: the inner catalog data
  const inner = catalogRoot?.Catalog;

  const handleValidate = async () => {
    if (!catalogRoot) return;
    try {
      const result =
        await validateCatalog.mutateAsync(catalogRoot);
      setValidationResults(result.errors, result.warnings);
      setActiveSection('validation');
    } catch (err: any) {
      console.error('Validation failed:', err);
      
      // Extract user-friendly error message
      const errorMessage = extractUserFriendlyErrorMessage(err);
      
      // Show schema validation errors as L1 errors
      setValidationResults([errorMessage], []);
      setActiveSection('validation');
    }
  };

  const handleExport = () => {
    if (!catalogRoot) return;
    const cleanedCatalog = cleanCatalogForExport(catalogRoot);
    const blob = new Blob(
      [JSON.stringify(cleanedCatalog, null, 2)],
      { type: 'application/json' },
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'catalog_rhel.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const handleImport = (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Add file size limit (100 MB)
    const MAX_IMPORT_SIZE = 100 * 1024 * 1024;
    if (file.size > MAX_IMPORT_SIZE) {
      setValidationResults(['File too large (max 100 MB)'], []);
      setActiveSection('validation');
      return;
    }
    
    const reader = new FileReader();
    reader.onload = async (ev) => {
      try {
        const imported = JSON.parse(
          ev.target?.result as string,
        );
        // Check if this is a catalog file (has "Catalog" key)
        if ('Catalog' in imported) {
          // Validate structure before loading into state
          try {
            const result = await validateCatalog.mutateAsync(imported);
            if (result.errors.length > 0) {
              setValidationResults(result.errors, result.warnings);
              setActiveSection('validation');
              return;
            }
          } catch (validationErr) {
            console.error('Validation during import failed:', validationErr);
            const errMsg = extractUserFriendlyErrorMessage(validationErr);
            setValidationResults(
              [`Import validation failed: ${errMsg}`],
              ['Catalog loaded without validation — please validate manually'],
            );
            setActiveSection('validation');
            // Still load — but user is warned
          }
          
          // Load into catalog editor store for immediate editing
          setCatalogRoot(imported);
          // Also import to backend to sync in-memory catalog
          try {
            await importCatalog.mutateAsync(imported);
          } catch (err) {
            console.error('Failed to import catalog to backend:', err);
            // Don't block UI - local state is still updated
          }
        } else {
          // Load into wizard
          setWizardData(imported);
          setActiveStep(1);
          navigate('/wizard');
        }
      } catch (err) {
        console.error('Import failed:', err);
        setValidationResults(
          [err instanceof Error ? err.message : 'Failed to parse JSON file'],
          [],
        );
        setActiveSection('validation');
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleResetAll = () => {
    showConfirm(
      'Reset All',
      'This will clear the current catalog and all deployment configuration data. This cannot be undone.',
      () => {
        setConfigSource('fresh');
        resetWizard();
        setCatalogRoot(EMPTY_CATALOG);
        setActiveSection('overview');
        setValidationResults([], []);
      }
    );
  };

  const layerCount = inner?.FunctionalLayer.length ?? 0;
  const osPkgCount = Object.keys(
    inner?.OSPackages ?? {},
  ).length;
  const infraPkgCount = Object.keys(
    inner?.InfrastructurePackages ?? {},
  ).length;

  const validationIcon =
    validationErrors.length > 0
      ? '(E)'
      : validationWarnings.length > 0
        ? '(W)'
        : '(OK)';

  const sections = useMemo(() => [
    ['overview', 'Overview'],
    ['layers', `Functional Layers (${layerCount})`],
    ['os', `OS Packages (${osPkgCount})`],
    ['infrastructure', `Infrastructure Packages (${infraPkgCount})`],
    ['driver-packages', 'Driver Packages'],
    ['miscellaneous', 'Miscellaneous'],
    ['validation', `Validation ${validationIcon}`],
  ] as const, [layerCount, osPkgCount, infraPkgCount, validationIcon]);

  return (
    <Layout>
      <div className="catalog-editor-container">
        {/* Header */}
        <div className="catalog-header">
          <h1>Catalog Manager</h1>
        </div>

        {/* Action Bar */}
        <div className="catalog-toolbar">
          <label className="button button-secondary">
            Import JSON
            <input
              type="file"
              accept=".json"
              onChange={handleImport}
              className="hidden"
            />
          </label>
          <button
            type="button"
            onClick={handleResetAll}
            className="button button-secondary"
          >
            Reset all
          </button>
          <button
            onClick={handleValidate}
            disabled={validateCatalog.isPending}
            className="button button-secondary"
          >
            {validateCatalog.isPending
              ? 'Validating…'
              : 'Validate'}
          </button>
          <button onClick={handleExport} className="button button-secondary">Export JSON</button>
        </div>

        {/* Sidebar + Content */}
        <div className="flex">
          <div className="catalog-sidebar">
            <h3>Sections</h3>
            <div className="flex flex-col">
              {sections.map(([section, label]) => (
                <button
                  key={section}
                  onClick={() => setActiveSection(section)}
                  className={`nav-link ${activeSection === section ? 'active' : ''}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="catalog-content">
            {activeSection === 'overview' && (
              <CatalogOverview />
            )}
            {activeSection === 'layers' && (
              <FunctionalLayerEditor />
            )}
            {activeSection === 'os' && <OSPackageEditor />}
            {activeSection === 'infrastructure' && (
              <InfrastructureEditor />
            )}
            {activeSection === 'driver-packages' && <DriverPackageEditor />}
            {activeSection === 'miscellaneous' && <MiscellaneousEditor />}
            {activeSection === 'validation' && (
              <ValidationPanel />
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default CatalogEditor;
