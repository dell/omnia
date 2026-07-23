import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../../components/Layout';
import { useCatalogStore } from '../catalog-editor/catalogStore';
import { get } from '../../utils/api';
import { useImportCatalog } from '../catalog-editor/hooks/useCatalog';
import type { CatalogRoot } from '../catalog-editor/schemas/catalogSchema';

interface CatalogPreset {
  name: string;
  filename: string;
  path: string;
}

const PresetPicker = () => {
  const navigate = useNavigate();
  const setCatalogRoot = useCatalogStore((s) => s.setCatalogRoot);
  const importCatalog = useImportCatalog();
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [catalogPresets, setCatalogPresets] = useState<CatalogPreset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch catalog presets from examples/catalog folder
  useEffect(() => {
    const fetchPresets = async () => {
      try {
        const response = await get<CatalogPreset[]>('/catalog/presets');
        setCatalogPresets(response);
      } catch (err) {
        setError('Failed to load catalog presets');
        console.error('Error loading presets:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchPresets();
  }, []);

  if (isLoading) {
    return (
      <Layout>
        <p>Loading catalog presets...</p>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <p className="text-error">{error}</p>
      </Layout>
    );
  }

  const handleSelectPreset = (presetName: string) => {
    setSelectedPreset(presetName);
  };

  const handleLoadPreset = async () => {
    if (selectedPreset && catalogPresets) {
      const preset = catalogPresets.find((p) => p.name === selectedPreset);
      if (preset) {
        try {
          // Load the catalog preset from the API
          const catalogData = await get<CatalogRoot>(`/catalog/presets/${preset.filename}`);
          
          // Load the catalog into the catalog editor store
          setCatalogRoot(catalogData);
          
          // Also import to backend to sync in-memory catalog
          try {
            await importCatalog.mutateAsync(catalogData);
          } catch (err) {
            console.error('Failed to import catalog to backend:', err);
            // Don't block UI - local state is still updated
          }
          
          // Navigate to catalog editor
          navigate('/catalog-editor');
        } catch (err) {
          console.error('Error loading catalog preset:', err);
          setError('Failed to load catalog preset');
        }
      }
    }
  };

  const handleBack = () => {
    navigate('/landing');
  };

  return (
    <Layout>
      <h1 className="mb-8">Select a Catalog Preset</h1>
      
      <p className="mb-6 text-secondary">
        Choose a catalog preset from the examples folder to load into the Catalog Editor.
      </p>

      <div className="grid-1-col" role="radiogroup" aria-label="Catalog presets">
        {catalogPresets.map((preset) => (
          <div
            key={preset.filename}
            className={`card preset-card ${selectedPreset === preset.name ? 'selected' : ''}`}
            role="radio"
            aria-checked={selectedPreset === preset.name}
            aria-label={`${preset.name} - ${preset.filename}`}
            tabIndex={0}
            onClick={() => handleSelectPreset(preset.name)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleSelectPreset(preset.name);
              }
            }}
          >
            <div className="flex justify-between items-center">
              <div>
                <h3>{preset.name}</h3>
                <p className="text-secondary mb-2">
                  {preset.filename}
                </p>
              </div>
              <div className="text-2xl">
                {selectedPreset === preset.name ? '✓' : '○'}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="config-uploader-actions">
        <button className="button button-secondary" onClick={handleBack}>
          Back
        </button>
        <button
          className={`button button-primary ${!selectedPreset ? 'disabled' : ''}`}
          onClick={handleLoadPreset}
          disabled={!selectedPreset}
        >
          Load Catalog & Continue
        </button>
      </div>
    </Layout>
  );
};

export default PresetPicker;
