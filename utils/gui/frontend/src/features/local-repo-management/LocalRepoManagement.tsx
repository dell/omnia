import { useState } from 'react';
import { useParams } from 'react-router-dom';
import Layout from '../../components/Layout';
import Button from '../../components/Button';
import { LocalRepoConfigForm } from './LocalRepoConfigForm';
import { useLocalRepoStore, type LocalRepoOsType, type LocalRepoOsData } from './localRepoStore';
import { useGenerateLocalRepo } from './hooks/useLocalRepo';
import {
  DEFAULT_OMNIA_REPO_X86_64,
  DEFAULT_OMNIA_REPO_AARCH64,
} from './localRepoDefaults';
import { showAlert } from '../toast/toastStore';
import { showConfirm } from '../confirmDialog/confirmDialogStore';

const OS_LABELS: Record<LocalRepoOsType, string> = {
  rhel: 'RHEL',
  ubuntu: 'Ubuntu',
};

const isValidOs = (os: string | undefined): os is LocalRepoOsType => os === 'rhel' || os === 'ubuntu';

const isNonEmptyValue = (value: unknown): boolean => {
  if (value === null || value === undefined) return false;
  if (typeof value === 'string') return value.trim().length > 0;
  if (Array.isArray(value)) return value.some(isNonEmptyValue);
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>).some(
      ([k, v]) => !k.startsWith('_') && isNonEmptyValue(v)
    );
  }
  return true;
};

const isDefaultOmniaRepo = (
  key: string,
  value: unknown,
  osType: LocalRepoOsType
): boolean => {
  if (osType !== 'rhel') return false;
  const defaultRepos =
    key === 'omnia_repo_url_rhel_x86_64'
      ? DEFAULT_OMNIA_REPO_X86_64
      : key === 'omnia_repo_url_rhel_aarch64'
        ? DEFAULT_OMNIA_REPO_AARCH64
        : null;
  if (!defaultRepos || !Array.isArray(value) || value.length !== defaultRepos.length) return false;
  return value.every((item, index) => {
    const def = defaultRepos[index];
    return (
      item &&
      def &&
      item.url === def.url &&
      item.gpgkey === def.gpgkey &&
      item.name === def.name
    );
  });
};

const hasLocalRepoData = (store: { rhel: LocalRepoOsData; ubuntu: LocalRepoOsData }): boolean => {
  for (const osType of ['rhel', 'ubuntu'] as const) {
    const osData = store[osType];
    for (const [key, value] of Object.entries(osData)) {
      if (key.startsWith('_ui_')) continue;
      if (isDefaultOmniaRepo(key, value, osType)) continue;
      if (isNonEmptyValue(value)) return true;
    }
  }
  return false;
};

const LocalRepoManagement = () => {
  const { os } = useParams<{ os: string }>();
  const osType: LocalRepoOsType = isValidOs(os) ? os : 'rhel';
  const store = useLocalRepoStore();
  const generateLocalRepo = useGenerateLocalRepo();
  const [isGenerating, setIsGenerating] = useState(false);
  const [resetKey, setResetKey] = useState(0);

  const handleGenerate = async () => {
    if (!hasLocalRepoData(store)) {
      showAlert('Please enter local repo configuration data before generating.', 'error');
      return;
    }
    setIsGenerating(true);
    try {
      const payload = {
        rhel: store.rhel,
        ubuntu: store.ubuntu,
      };
      await generateLocalRepo.mutateAsync(payload);
      showAlert('Local repo config and user registry credentials generation started.', 'success');
    } catch (error) {
      showAlert(error instanceof Error ? error.message : 'Failed to generate local repo config.', 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Layout>
      <div className="card">
        <div className="flex justify-between items-center">
          <h1>{OS_LABELS[osType]} Local Repo Configuration</h1>
        </div>
        <p className="text-muted">
          Configure the local repository settings used by Omnia for the {OS_LABELS[osType]} operating system.
        </p>

        <div className="mt-4">
          <LocalRepoConfigForm key={`${osType}-${resetKey}`} osType={osType} />
        </div>

        <div className="mt-6 flex justify-end">
          <Button
            variant="secondary"
            onClick={() => {
              showConfirm(
                'Reset Local Repo Configuration',
                `Are you sure you want to clear all entered values for ${OS_LABELS[osType]}?`,
                () => {
                  store.resetOs(osType);
                  setResetKey((k) => k + 1);
                }
              );
            }}
            disabled={isGenerating}
          >
            Reset
          </Button>
          <Button
            variant="primary"
            onClick={handleGenerate}
            disabled={isGenerating}
            style={{ backgroundColor: '#0097a7' }}
          >
            {isGenerating ? 'Generating...' : 'Generate'}
          </Button>
        </div>
      </div>
    </Layout>
  );
};

export default LocalRepoManagement;
