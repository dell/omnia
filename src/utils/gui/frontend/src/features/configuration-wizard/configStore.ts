import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ValidationError } from './utils/l2Validation';
import { WIZARD_STEPS } from './constants';

export type ConfigSource = 'fresh' | 'preset' | 'upload';

interface ConfigState {
  // UI State
  activeStep: number
  setActiveStep: (step: number) => void
  nextStep: () => void
  prevStep: () => void

  // Config Source
  configSource: ConfigSource
  setConfigSource: (source: ConfigSource) => void

  // Wizard Data
  wizardData: Record<string, unknown>
  setWizardData: (data: Record<string, unknown>) => void
  updateWizardField: (field: string, value: unknown) => void
  updateWizardFields: (fields: Record<string, unknown>) => void
  resetWizard: () => void

  // Step Validation
  stepValidity: Record<number, boolean>
  setStepValid: (step: number, valid: boolean) => void
  validationErrors: ValidationError[]
  setValidationErrors: (errors: ValidationError[]) => void
  clearValidationErrors: () => void
  removeValidationErrorsByField: (fields: string[]) => void

  // UI Toggles
  sidebarOpen: boolean
  toggleSidebar: () => void
  wizardExpanded: boolean
  setWizardExpanded: (expanded: boolean) => void
  catalogExpanded: boolean
  setCatalogExpanded: (expanded: boolean) => void
  buildConfigExpanded: boolean
  setBuildConfigExpanded: (expanded: boolean) => void
  localRepoExpanded: boolean
  setLocalRepoExpanded: (expanded: boolean) => void
  telemetryActiveTab: string
  setTelemetryActiveTab: (tab: string) => void

  // Guiding Screen State
  clusterType: 'slurm' | 'k8s' | 'both' | null
  setClusterType: (type: 'slurm' | 'k8s' | 'both' | null) => void
  enableHa: boolean
  setEnableHa: (enabled: boolean) => void
  enableCloudInit: boolean
  setEnableCloudInit: (enabled: boolean) => void
  enableBmcDiscovery: boolean
  setEnableBmcDiscovery: (enabled: boolean) => void
  selectedTelemetrySources: string[]
  setSelectedTelemetrySources: (sources: string[]) => void
  enableBuildStream: boolean
  setEnableBuildStream: (enabled: boolean) => void
  enableGitlab: boolean
  setEnableGitlab: (enabled: boolean) => void
  enableTelemetry: boolean
  setEnableTelemetry: (enabled: boolean) => void
  configMode: 'pxe_upload' | 'manual' | null
  setConfigMode: (mode: 'pxe_upload' | 'manual' | null) => void
  isStepEnabled: (stepId: number) => boolean
}

export const useConfigStore = create<ConfigState>()(
  persist(
    (set, get) => ({
      // UI State
      activeStep: 0,
      setActiveStep: (step) => set({ activeStep: step }),
      nextStep: () => set((state) => {
        const current = state.activeStep;
        let next = current + 1;
        const totalSteps = WIZARD_STEPS.length;
        while (next <= totalSteps && !get().isStepEnabled(next)) {
          next++;
        }
        return { activeStep: next };
      }),
      prevStep: () => set((state) => {
        const current = state.activeStep;
        let prev = current - 1;
        while (prev >= 1 && !get().isStepEnabled(prev)) {
          prev--;
        }
        return { activeStep: Math.max(0, prev) };
      }),

      // Config Source
      configSource: 'fresh',
      setConfigSource: (source) => set({ configSource: source }),

      // Wizard Data
      wizardData: {},
      setWizardData: (data) => set({ wizardData: data }),
      updateWizardField: (field, value) => set((state) => ({
        wizardData: { ...state.wizardData, [field]: value },
      })),
      updateWizardFields: (fields) => set((state) => ({
        wizardData: { ...state.wizardData, ...fields },
      })),
      resetWizard: () => set({
        wizardData: {},
        activeStep: 0,
        stepValidity: {},
        validationErrors: [],
        clusterType: null,
        enableHa: false,
        enableCloudInit: false,
        enableBmcDiscovery: false,
        selectedTelemetrySources: [],
        enableBuildStream: false,
        enableGitlab: false,
        enableTelemetry: false,
        configMode: null,
      }),

      // Step Validation
      stepValidity: {},
      setStepValid: (step, valid) => set((state) => ({
        stepValidity: { ...state.stepValidity, [step]: valid },
      })),
      validationErrors: [],
      setValidationErrors: (errors) => set({ validationErrors: errors }),
      clearValidationErrors: () => set({ validationErrors: [] }),
      removeValidationErrorsByField: (fields) =>
        set((state) => ({
          validationErrors: state.validationErrors.filter(
            (err) => !fields.includes(err.field)
          ),
        })),

      // UI Toggles
      sidebarOpen: true,
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      wizardExpanded: false,
      setWizardExpanded: (expanded) => set({ wizardExpanded: expanded }),
      catalogExpanded: false,
      setCatalogExpanded: (expanded) => set({ catalogExpanded: expanded }),
      buildConfigExpanded: false,
      setBuildConfigExpanded: (expanded) => set({ buildConfigExpanded: expanded }),
      localRepoExpanded: false,
      setLocalRepoExpanded: (expanded) => set({ localRepoExpanded: expanded }),
      telemetryActiveTab: 'idrac',
      setTelemetryActiveTab: (tab) => set({ telemetryActiveTab: tab }),

      // Guiding Screen State
      clusterType: null,
      setClusterType: (type) => set((state) => {
        const includesSlurm = (t: typeof type) => t === 'slurm' || t === 'both';
        const includesK8s = (t: typeof type) => t === 'k8s' || t === 'both';

        const updates: Partial<ConfigState> & { wizardData: Record<string, unknown> } = {
          clusterType: type,
          wizardData: { ...state.wizardData },
        };

        // Clear slurm data when the new selection no longer includes Slurm
        if (!includesSlurm(type) && includesSlurm(state.clusterType)) {
          updates.wizardData.slurm_cluster = undefined;
        }

        // Clear k8s and HA data when the new selection no longer includes Kubernetes
        if (!includesK8s(type) && includesK8s(state.clusterType)) {
          updates.wizardData.service_k8s_cluster = undefined;
          updates.wizardData.service_k8s_cluster_ha = undefined;
          updates.wizardData.enable_ha = undefined;
          updates.enableHa = false;
        }

        return updates;
      }),
      enableHa: false,
      setEnableHa: (enabled) => set({ enableHa: enabled }),
      enableCloudInit: false,
      setEnableCloudInit: (enabled) => set({ enableCloudInit: enabled }),
      enableBmcDiscovery: false,
      setEnableBmcDiscovery: (enabled) => set({ enableBmcDiscovery: enabled }),
      selectedTelemetrySources: [],
      setSelectedTelemetrySources: (sources) => set({ selectedTelemetrySources: sources }),
      enableBuildStream: false,
      setEnableBuildStream: (enabled) => set({ enableBuildStream: enabled }),
      enableGitlab: false,
      setEnableGitlab: (enabled) => set({ enableGitlab: enabled }),
      enableTelemetry: false,
      setEnableTelemetry: (enabled) => set({ enableTelemetry: enabled }),
      configMode: null,
      setConfigMode: (mode) => set({ configMode: mode }),
      isStepEnabled: (stepId: number) => {
        const state = get();
        // Step 0: Deployment Overview - always enabled
        if (stepId === 0) return true;
        // Step 1: Deployment Setup - always enabled
        if (stepId === 1) return true;
        // Lock all other steps until configMode and clusterType are selected
        if (!state.configMode || !state.clusterType) return false;
        // Step 2: PXE Functional Groups - always enabled after configMode is set (for both modes)
        if (stepId === 2) return true;
        // Step 3: Network Configuration - always enabled after configMode is set
        if (stepId === 3) return true;
        // Step 4: Storage Configuration - always enabled
        if (stepId === 4) return true;
        // Step 5: Cloud-Init Configuration - only when enabled
        if (stepId === 5) return state.enableCloudInit;
        // Step 6: Omnia Cluster Config - always enabled
        if (stepId === 6) return true;
        // Step 7: Telemetry Configuration - only for K8s or Both AND when telemetry is enabled
        if (stepId === 7) return (state.clusterType === 'k8s' || state.clusterType === 'both') && state.enableTelemetry;
        // Step 8: Build Stream Config - only when Build Stream or GitLab enabled
        if (stepId === 8) return state.enableBuildStream || state.enableGitlab;
        // Step 9: Summary & Generate - always enabled
        if (stepId === 9) return true;
        return false;
      },

    }),
    {
      name: 'omnia-config-storage',
      version: 3,
      migrate: (persistedState, version) => {
        if (version === 0) {
          // Handle migration from v0 → v1 if needed in the future
        }
        return persistedState as ConfigState;
      },
      merge: (persistedState, currentState) => ({
        ...currentState,
        ...(persistedState as Partial<ConfigState>),
      }),
      partialize: (state) => ({
        // Persist all state except sensitive credential fields
        activeStep: state.activeStep,
        configSource: state.configSource,
        wizardExpanded: state.wizardExpanded,
        buildConfigExpanded: state.buildConfigExpanded,
        localRepoExpanded: state.localRepoExpanded,
        telemetryActiveTab: state.telemetryActiveTab,
        clusterType: state.clusterType,
        enableHa: state.enableHa,
        enableCloudInit: state.enableCloudInit,
        enableBmcDiscovery: state.enableBmcDiscovery,
        selectedTelemetrySources: state.selectedTelemetrySources,
        enableBuildStream: state.enableBuildStream,
        enableGitlab: state.enableGitlab,
        enableTelemetry: state.enableTelemetry,
        configMode: state.configMode,
        wizardData: (() => {
          const filteredData: Record<string, unknown> = {};
          for (const [key, value] of Object.entries(state.wizardData)) {
            // Always preserve PXE mapping data
            if (key === 'pxe_mapping_data' || key === 'pxe_mapping_file_path') {
              filteredData[key] = value;
            }
            // Exclude password fields within user_registry_credential
            else if (key === 'user_registry_credential' && Array.isArray(value)) {
              const filteredCredentials = value.map((cred: any) => ({
                ...cred,
                password: undefined
              }));
              filteredData[key] = filteredCredentials;
            }
            // Exclude other sensitive fields
            else if (['password', 'admin_password', 'bmc_password', 'secret_key', 'api_secret', 'auth_token', 'access_token'].includes(key)) {
              // Skip these keys entirely
            }
            else {
              // Keep all other data
              filteredData[key] = value;
            }
          }
          return filteredData;
        })(),
        sidebarOpen: state.sidebarOpen,
      }),
    }
  )
)
