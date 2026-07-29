import { useCatalogStore } from '../catalogStore';
import { useValidateCatalog } from '../hooks/useCatalog';

const ValidationPanel = () => {
  const catalogRoot = useCatalogStore((s) => s.catalogRoot);
  const validationErrors = useCatalogStore((s) => s.validationErrors);
  const validationWarnings = useCatalogStore((s) => s.validationWarnings);
  const setValidationResults = useCatalogStore((s) => s.setValidationResults);
  const validateCatalog = useValidateCatalog();

  const handleRevalidate = async () => {
    if (!catalogRoot) return;
    try {
      const result =
        await validateCatalog.mutateAsync(catalogRoot);
      setValidationResults(result.errors, result.warnings);
    } catch (err) {
      console.error('Validation failed:', err);
    }
  };

  // Separate L1 and L2 errors/warnings
  const l1Errors = validationErrors.filter(e => !e.startsWith('[L2]'));
  const l2Errors = validationErrors.filter(e => e.startsWith('[L2]'));
  const l1Warnings = validationWarnings.filter(w => !w.startsWith('[L2]'));
  const l2Warnings = validationWarnings.filter(w => w.startsWith('[L2]'));

  return (
    <div className="validation-panel p-8">
      <div className="flex justify-between items-center mb-4">
        <h2>Validation Results</h2>
        <button
          onClick={handleRevalidate}
          disabled={validateCatalog.isPending}
          className="button button-primary"
        >
          {validateCatalog.isPending
            ? 'Validating…'
            : 'Re-validate'}
        </button>
      </div>

      {validationErrors.length === 0 &&
        validationWarnings.length === 0 && (
          <div className="card card-success padding-md text-center">
            [OK] Catalog schema valid
          </div>
        )}

      {/* L1 Errors */}
      {l1Errors.length > 0 && (
        <div className="mb-4">
          <h3 className="text-error">
            L1 Errors (Schema) ({l1Errors.length})
          </h3>
          {l1Errors.map((error, i) => (
            <div key={i} className="validation-error-item">
              {error}
            </div>
          ))}
        </div>
      )}

      {/* L2 Errors */}
      {l2Errors.length > 0 && (
        <div className="mb-4">
          <h3 className="text-error">
            L2 Errors (Business Logic) ({l2Errors.length})
          </h3>
          {l2Errors.map((error, i) => (
            <div key={i} className="validation-error-item">
              {error.replace('[L2] ', '')}
            </div>
          ))}
        </div>
      )}

      {/* L1 Warnings */}
      {l1Warnings.length > 0 && (
        <div className="mb-4">
          <h3 className="text-warning">
            L1 Warnings ({l1Warnings.length})
          </h3>
          {l1Warnings.map((warning, i) => (
            <div key={i} className="validation-warning-item">
              {warning}
            </div>
          ))}
        </div>
      )}

      {/* L2 Warnings */}
      {l2Warnings.length > 0 && (
        <div className="mb-4">
          <h3 className="text-warning">
            L2 Warnings ({l2Warnings.length})
          </h3>
          {l2Warnings.map((warning, i) => (
            <div key={i} className="validation-warning-item">
              {warning.replace('[L2] ', '')}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ValidationPanel;
