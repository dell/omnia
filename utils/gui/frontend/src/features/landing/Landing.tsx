import { useNavigate } from 'react-router-dom';
import Layout from '../../components/Layout';
import { useConfigStore, type ConfigSource } from '../configuration-wizard/configStore';
import { useCatalogStore } from '../catalog-editor/catalogStore';
import { EMPTY_CATALOG } from '../catalog-editor/constants/emptyCatalog';

// Icon Components
const PlusIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

const FileTextIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
);

const CatalogIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
  </svg>
);

type CardSource = ConfigSource | 'catalog';

// Card Data
const CARDS = [
  {
    source: 'fresh',
    path: '/catalog-editor',
    icon: PlusIcon,
    title: 'Start Fresh',
    description: 'Create a new catalog from scratch with default values',
  },
  {
    source: 'preset',
    path: '/preset-picker',
    icon: FileTextIcon,
    title: 'Use Existing',
    description: 'Load an existing preset configuration from the repository',
  },
  {
    source: 'catalog',
    path: '/catalog',
    icon: CatalogIcon,
    title: 'Catalog Viewer',
    description: 'View the generated BuildStream catalog JSON file',
  },
] as const;

const Landing = () => {
  const navigate = useNavigate();
  const setConfigSource = useConfigStore((state) => state.setConfigSource);
  const resetWizard = useConfigStore((state) => state.resetWizard);
  const setCatalogRoot = useCatalogStore((state) => state.setCatalogRoot);

  const handleSelect = (source: CardSource, path: string) => {
    if (source !== 'catalog') {
      setConfigSource(source);
      resetWizard();
      // Initialize with empty catalog structure when starting fresh
      if (source === 'fresh') {
        setCatalogRoot(EMPTY_CATALOG);
      }
    }
    navigate(path);
  };

  return (
    <Layout>
      <div className="landing-container">
        <h1 className="landing-title">
          OMNIA Deployment Configuration
        </h1>
        
        <p className="landing-subtitle">
          Choose how you want to configure your OMNIA deployment
        </p>

        <div className="landing-grid">
          {CARDS.map(({ source, path, icon: Icon, title, description }) => (
            <button
              key={source}
              className="landing-card"
              onClick={() => handleSelect(source, path)}
              type="button"
            >
              <Icon />
              <h3>{title}</h3>
              <p>{description}</p>
            </button>
          ))}
        </div>

        <div className="card mt-4 landing-workflow">
          <h3>Configuration Workflow</h3>
          <ol>
            <li>Configure PXE functional groups, DHCP settings, DNS, and kernel overrides</li>
            <li>Configure admin and InfiniBand networks including subnets, IP addresses, and NTP servers</li>
            <li>Configure Slurm clusters, Kubernetes service clusters, high availability settings, and BMC discovery</li>
            <li>Configure telemetry sources (iDRAC, LDMS, DCGM, PowerScale, UFM, VAST, OME), bridges, and storage sinks</li>
            <li>Configure BuildStream host and GitLab integration for catalog management</li>
            <li>Review all configuration settings and generate the deployment configuration files</li>
          </ol>
        </div>
      </div>
    </Layout>
  );
};

export default Landing;
