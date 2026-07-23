import { ReactNode, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useConfigStore } from '../features/configuration-wizard/configStore';
import { WIZARD_STEPS } from '../features/configuration-wizard/constants';
import ToastContainer from '../features/toast/ToastContainer';
import ConfirmDialog from '../features/confirmDialog/ConfirmDialog';
import omniaLogo from '../assets/omnia-logo.png';

interface LayoutProps {
  children: ReactNode;
}

const Layout = ({ children }: LayoutProps) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { activeStep, setActiveStep, wizardExpanded, setWizardExpanded, catalogExpanded, setCatalogExpanded, buildConfigExpanded, setBuildConfigExpanded, localRepoExpanded, setLocalRepoExpanded, isStepEnabled } = useConfigStore();

  // Close wizard expanded state when navigating away from /wizard
  useEffect(() => {
    if (location.pathname !== '/wizard' && wizardExpanded) {
      setWizardExpanded(false);
    }
  }, [location.pathname, wizardExpanded, setWizardExpanded]);

  // Expand/collapse local repo group based on route changes only
  useEffect(() => {
    const localRepoPages = ['/local-repo', '/local-repo/rhel', '/local-repo/ubuntu'];
    if (localRepoPages.some((path) => location.pathname.startsWith(path))) {
      setBuildConfigExpanded(true);
      setLocalRepoExpanded(true);
    } else {
      setLocalRepoExpanded(false);
    }
  }, [location.pathname, setBuildConfigExpanded, setLocalRepoExpanded]);

  const isActive = (path: string) => location.pathname === path;

  const handleStepClick = (stepId: number) => {
    setActiveStep(stepId);
  };

  const handleNavigation = (path: string) => {
    navigate(path);
  };

  return (
    <div className="layout-container flex flex-col">
      {/* Top Bar */}
      <header className="top-bar">
        <Link to="/" className="logo-link">
          <img src={omniaLogo} alt="Omnia" className="logo" />
        </Link>
      </header>

      {/* Main Content Area with Sidebar */}
      <div className="flex flex-1">
        {/* Left Sidebar */}
        <aside className="sidebar">
          <nav>
            <button onClick={() => { setCatalogExpanded(false); setBuildConfigExpanded(false); handleNavigation('/'); }} className={`nav-link ${isActive('/') ? 'active' : ''}`}>Home</button>

            {/* Build Configuration - contains Catalog Management and Local Repo Management */}
            <div className="nav-group">
              <button
                type="button"
                className={`nav-toggle ${buildConfigExpanded ? 'expanded' : ''}`}
                onClick={() => {
                  const buildConfigPages = ['/landing', '/catalog-editor', '/preset-picker', '/catalog', '/local-repo', '/local-repo/rhel', '/local-repo/ubuntu'];
                  if (buildConfigExpanded && buildConfigPages.includes(location.pathname)) {
                    setBuildConfigExpanded(false);
                  } else {
                    setBuildConfigExpanded(true);
                    setWizardExpanded(false);
                    handleNavigation('/landing');
                  }
                }}
              >
                <span>Build Configuration</span>
                <span className="chevron">{buildConfigExpanded ? '▼' : '▶'}</span>
              </button>
              {buildConfigExpanded && (
                <div className="nav-submenu">
                  {/* Nested Catalog Management */}
                  <div className="nav-group nested">
                    <button
                      type="button"
                      className={`nav-toggle ${catalogExpanded ? 'expanded' : ''}`}
                      onClick={() => {
                        const catalogPages = ['/landing', '/catalog-editor', '/preset-picker', '/catalog'];
                        if (catalogExpanded && catalogPages.includes(location.pathname)) {
                          setCatalogExpanded(false);
                        } else {
                          setCatalogExpanded(true);
                          handleNavigation('/landing');
                        }
                      }}
                    >
                      <span>Catalog Management</span>
                      <span className="chevron">{catalogExpanded ? '▼' : '▶'}</span>
                    </button>
                    {catalogExpanded && (
                      <div className="nav-submenu">
                        <button
                          type="button"
                          className={`nav-item ${isActive('/landing') ? 'active' : ''}`}
                          onClick={() => handleNavigation('/landing')}
                        >
                          Overview
                        </button>
                        <button
                          type="button"
                          className={`nav-item ${isActive('/catalog-editor') ? 'active' : ''}`}
                          onClick={() => handleNavigation('/catalog-editor')}
                        >
                          Catalog Editor
                        </button>
                        <button
                          type="button"
                          className={`nav-item ${isActive('/preset-picker') ? 'active' : ''}`}
                          onClick={() => handleNavigation('/preset-picker')}
                        >
                          Presets
                        </button>
                        <button
                          type="button"
                          className={`nav-item ${isActive('/catalog') ? 'active' : ''}`}
                          onClick={() => handleNavigation('/catalog')}
                        >
                          Catalog Viewer
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="nav-group nested">
                    <button
                      type="button"
                      className={`nav-toggle ${localRepoExpanded ? 'expanded' : ''}`}
                      onClick={() => {
                        const localRepoPages = ['/local-repo', '/local-repo/rhel', '/local-repo/ubuntu'];
                        if (localRepoExpanded && localRepoPages.includes(location.pathname)) {
                          setLocalRepoExpanded(false);
                        } else {
                          setLocalRepoExpanded(true);
                          handleNavigation('/local-repo/rhel');
                        }
                      }}
                    >
                      <span>Local Repo Management</span>
                      <span className="chevron">{localRepoExpanded ? '▼' : '▶'}</span>
                    </button>
                    {localRepoExpanded && (
                      <div className="nav-submenu">
                        <button
                          type="button"
                          className={`nav-item ${isActive('/local-repo/rhel') ? 'active' : ''}`}
                          onClick={() => handleNavigation('/local-repo/rhel')}
                        >
                          RHEL Configuration
                        </button>
                        <button
                          type="button"
                          className={`nav-item ${isActive('/local-repo/ubuntu') ? 'active' : ''}`}
                          onClick={() => handleNavigation('/local-repo/ubuntu')}
                        >
                          Ubuntu Configuration
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Nested Deployment Configuration */}
            <div className="nav-group">
              <button
                type="button"
                className={`nav-toggle ${wizardExpanded ? 'expanded' : ''}`}
                onClick={() => {
                  setCatalogExpanded(false);
                  setBuildConfigExpanded(false);
                  if (wizardExpanded && location.pathname === '/wizard') {
                    setWizardExpanded(false);
                  } else {
                    setWizardExpanded(true);
                    setActiveStep(0);
                    handleNavigation('/wizard');
                  }
                }}
              >
                <span>Deployment Configuration</span>
                <span className="chevron">{wizardExpanded ? '▼' : '▶'}</span>
              </button>
              {wizardExpanded && (
                <div className="nav-submenu">
                  <button
                    type="button"
                    className={`nav-item ${isActive('/wizard') && activeStep === 0 ? 'active' : ''} ${!isStepEnabled(0) ? 'disabled' : ''}`}
                    onClick={() => {
                      if (isStepEnabled(0)) {
                        handleStepClick(0);
                        handleNavigation('/wizard');
                      }
                    }}
                  >
                    Overview
                  </button>
                  {WIZARD_STEPS.map(step => (
                    <button
                      key={step.id}
                      type="button"
                      className={`nav-item ${isActive('/wizard') && activeStep === step.id ? 'active' : ''} ${!isStepEnabled(step.id) ? 'disabled' : ''}`}
                      onClick={() => {
                        if (isStepEnabled(step.id)) {
                          handleStepClick(step.id);
                          handleNavigation('/wizard');
                        }
                      }}
                    >
                      {step.title}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button onClick={() => { setCatalogExpanded(false); setBuildConfigExpanded(false); handleNavigation('/adapter-policy'); }} className={`nav-link ${isActive('/adapter-policy') ? 'active' : ''}`}>Adapter Policy</button>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="main-content">
          {children}
        </main>
      </div>
      
      <ToastContainer />
      <ConfirmDialog />
    </div>
  );
};

export default Layout;
