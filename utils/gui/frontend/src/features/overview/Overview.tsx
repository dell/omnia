import { Link } from 'react-router-dom';
import Layout from '../../components/Layout';
import { useConfigStore } from '../configuration-wizard/configStore';

const Overview = () => {
  const setCatalogExpanded = useConfigStore((s) => s.setCatalogExpanded);
  const setBuildConfigExpanded = useConfigStore((s) => s.setBuildConfigExpanded);
  const setWizardExpanded = useConfigStore((s) => s.setWizardExpanded);
  const setActiveStep = useConfigStore((s) => s.setActiveStep);

  return (
    <Layout>
      <h1>Omnia: Overview</h1>

      <p>
        Welcome to the OMNIA configuration tool. This application provides
        workflows for OMNIA deployment and build configuration.
      </p>

      <h2>Workflows</h2>

      <div className="card mt-4">
        <h3>Build Configuration</h3>
        <p>
          Manage the catalog, packages, and local repositories used to build
          OMNIA images.
        </p>
        <p className="margin-top-sm">
          <strong>Catalog Management:</strong>{' '}
          <Link
            to="/landing"
            onClick={() => {
              setBuildConfigExpanded(true);
              setCatalogExpanded(true);
              setWizardExpanded(false);
            }}
          >
            Catalog Editor
          </Link>
        </p>
        <ul className="margin-top-sm">
          <li>Edit software packages and bundles</li>
          <li>Configure functional layers</li>
          <li>Manage infrastructure and miscellaneous settings</li>
          <li>Validate and export catalog files</li>
        </ul>
        <p className="margin-top-sm">
          <strong>Local Repo Management:</strong>{' '}
          <Link
            to="/local-repo"
            onClick={() => {
              setBuildConfigExpanded(true);
              setWizardExpanded(false);
            }}
          >
            Configure Local Repositories
          </Link>
        </p>
        <ul className="margin-top-sm">
          <li>Configure local package repositories for RHEL and Ubuntu</li>
          <li>Configure user registries, credentials, and additional package sources</li>
          <li>Generate local_repo_config.yml independently</li>
        </ul>
      </div>

      <div className="card mt-4">
        <h3>Deployment Configuration</h3>
        <p>
          Configure infrastructure and deployment settings for your OMNIA cluster
          through a step-by-step wizard.
        </p>
        <p className="margin-top-sm">
          <strong>Use the:</strong>{' '}
          <Link
            to="/wizard"
            onClick={() => {
              setWizardExpanded(true);
              setBuildConfigExpanded(false);
              setCatalogExpanded(false);
              setActiveStep(0);
            }}
          >
            Deployment Configuration
          </Link>
        </p>
        <ul className="margin-top-sm">
          <li>Configure PXE functional groups</li>
          <li>Set up deployment configurations</li>
          <li>Configure Omnia, Telemetry, GitLab, and High Availability settings</li>
          <li>Configure Local Repository and Telemetry Storage</li>
          <li>Generate deployment configuration files</li>
        </ul>
      </div>

      <h2>Configuration Flow</h2>
      <ol>
        <li><strong>Build Configuration:</strong> Use the{' '}
          <Link
            to="/landing"
            onClick={() => {
              setBuildConfigExpanded(true);
              setCatalogExpanded(true);
              setWizardExpanded(false);
            }}
          >
            Catalog Editor
          </Link>{' '}
          and{' '}
          <Link
            to="/local-repo"
            onClick={() => {
              setBuildConfigExpanded(true);
              setWizardExpanded(false);
            }}
          >
            Local Repo Management
          </Link>{' '}
          to define your software catalog and local package repositories
        </li>
        <li><strong>Deployment Configuration:</strong> Use the{' '}
          <Link
            to="/wizard"
            onClick={() => {
              setWizardExpanded(true);
              setBuildConfigExpanded(false);
              setCatalogExpanded(false);
              setActiveStep(0);
            }}
          >
            Configuration Wizard
          </Link>{' '}
          to configure infrastructure and deployment settings
        </li>
        <li><strong>Generate Files:</strong> Each workflow generates the necessary YAML, JSON, and CSV configuration files</li>
      </ol>

    </Layout>
  );
};

export default Overview;