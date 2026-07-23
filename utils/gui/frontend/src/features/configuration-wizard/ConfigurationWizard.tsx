import { useEffect } from 'react';
import Layout from '../../components/Layout';
import { useConfigStore } from './configStore';
import { WIZARD_STEPS } from './constants';
import DeploymentOverview from './components/DeploymentOverview';
import { showConfirm } from '../confirmDialog/confirmDialogStore';

const ConfigurationWizard = () => {
  const activeStep = useConfigStore((state) => state.activeStep);
  const setActiveStep = useConfigStore((state) => state.setActiveStep);
  const nextStep = useConfigStore((state) => state.nextStep);
  const prevStep = useConfigStore((state) => state.prevStep);
  const isCurrentStepValid = useConfigStore((state) => state.stepValidity[activeStep] ?? true);
  const resetWizard = useConfigStore((state) => state.resetWizard);
  const configSource = useConfigStore((state) => state.configSource);
  const wizardData = useConfigStore((state) => state.wizardData);
  const isStepEnabled = useConfigStore((state) => state.isStepEnabled);
  const totalSteps = WIZARD_STEPS.length;

  // Manage step transitions and guard against disabled / out-of-bounds steps
  useEffect(() => {
    if (activeStep > totalSteps || activeStep < 0) {
      setActiveStep(0);
      return;
    }

    if (configSource === 'preset' && Object.keys(wizardData).length > 0 && activeStep === 0) {
      setActiveStep(1);
      return;
    }

    if (!isStepEnabled(activeStep) && activeStep > 0) {
      let nearestEnabled = activeStep;
      while (nearestEnabled > 0 && !isStepEnabled(nearestEnabled)) {
        nearestEnabled--;
      }
      if (isStepEnabled(nearestEnabled)) {
        setActiveStep(nearestEnabled);
      }
    }
  }, [activeStep, configSource, wizardData, isStepEnabled, setActiveStep, totalSteps]);

  const stepIndex = activeStep > 0 ? activeStep - 1 : undefined;
  const stepConfig = activeStep === 0
    ? { title: 'Deployment Overview' }
    : stepIndex !== undefined ? WIZARD_STEPS[stepIndex] : { title: 'Configuration' };
  const StepComponent = activeStep === 0
    ? DeploymentOverview
    : stepIndex !== undefined ? WIZARD_STEPS[stepIndex].component : undefined;

  return (
    <Layout>
      <div className="wizard-page">
        <div
          className="wizard-header"
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <h1>{stepConfig?.title || 'Configuration'}</h1>
          {stepConfig?.title === 'Telemetry Configuration' && (
            <button
              type="button"
              onClick={() => document.getElementById('telemetry-upload-input')?.click()}
              className="button button-secondary"
            >
              Upload Configuration
            </button>
          )}
        </div>
        
        <div className="wizard-content">
          {StepComponent && <StepComponent />}
        </div>
        
        <div className="wizard-footer">
          <button
            onClick={() => {
              showConfirm(
                'Reset Configuration',
                'Are you sure you want to reset all deployment configuration fields? This will clear all values and return to Step 1.',
                () => resetWizard()
              );
            }}
            className="button button-secondary margin-right-auto"
          >
            Reset All
          </button>

          {activeStep > 0 && (
            <button
              onClick={prevStep}
              className="button button-secondary"
            >
              Back
            </button>
          )}
          
          {activeStep < totalSteps && (
            <button
              onClick={nextStep}
              className="button button-tertiary"
              disabled={!isCurrentStepValid}
            >
              Next
            </button>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default ConfigurationWizard;
