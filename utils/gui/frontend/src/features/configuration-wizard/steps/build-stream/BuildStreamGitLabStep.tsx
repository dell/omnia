import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useConfigStore } from '../../configStore';
import { BuildStreamGitLabFormData, buildStreamGitLabSchema } from '../../schemas';
import { clearL2ErrorsForStep } from '../../utils/l2Validation';
import { useFormErrors } from '../../hooks/useFormErrors';

export const BuildStreamGitLabStep = () => {
  const { updateWizardFields, wizardData, setStepValid, enableBuildStream, enableGitlab } = useConfigStore();
  const validationErrors = useConfigStore((s) => s.validationErrors);

  const {
    register,
    formState: { errors },
    watch,
    setValue,
    getValues,
  } = useForm<BuildStreamGitLabFormData>({
    // zodResolver type inference conflicts with .default() and .refine() on optional fields.
    resolver: zodResolver(buildStreamGitLabSchema) as any,
    defaultValues: {
      enable_build_stream: typeof wizardData.enable_build_stream === 'boolean' ? wizardData.enable_build_stream : enableBuildStream,
      build_stream_host_ip: (wizardData.build_stream_host_ip as string) || '',
      build_stream_port: typeof wizardData.build_stream_port === 'number' ? wizardData.build_stream_port : 8010,
      aarch64_inventory_host_ip: wizardData.aarch64_inventory_host_ip as string | undefined,
      enable_gitlab: typeof wizardData.enable_gitlab === 'boolean' ? wizardData.enable_gitlab : enableGitlab,
      // GitLab defaults from input/gitlab_config.yml
      gitlab_host: (wizardData.gitlab_host as string) || '',
      gitlab_project_name: (wizardData.gitlab_project_name as string) || 'omnia-catalog',
      gitlab_project_visibility: (wizardData.gitlab_project_visibility as 'private' | 'internal' | 'public') || 'private',
      gitlab_default_branch: (wizardData.gitlab_default_branch as string) || 'main',
      gitlab_https_port: typeof wizardData.gitlab_https_port === 'number' ? wizardData.gitlab_https_port : 443,
      gitlab_min_storage_gb: typeof wizardData.gitlab_min_storage_gb === 'number' ? wizardData.gitlab_min_storage_gb : 20,
      gitlab_min_memory_gb: typeof wizardData.gitlab_min_memory_gb === 'number' ? wizardData.gitlab_min_memory_gb : 4,
      gitlab_min_cpu_cores: typeof wizardData.gitlab_min_cpu_cores === 'number' ? wizardData.gitlab_min_cpu_cores : 2,
      gitlab_puma_workers: typeof wizardData.gitlab_puma_workers === 'number' ? wizardData.gitlab_puma_workers : 2,
      gitlab_sidekiq_concurrency: typeof wizardData.gitlab_sidekiq_concurrency === 'number' ? wizardData.gitlab_sidekiq_concurrency : 10,
    },
    mode: 'onTouched',
  });

  const getError = useFormErrors(errors, validationErrors);

  // Sync initial Build Stream/GitLab form values to store immediately so Summary
  // validation works even if the user navigates quickly, then keep syncing subsequent changes
  useEffect(() => {
    const currentValues = getValues();
    updateWizardFields(currentValues as Partial<any>);
  }, []);

  // Sync form changes to store and validate step
  useEffect(() => {
    const currentValues = watch();
    const initialResult = buildStreamGitLabSchema.safeParse(currentValues);
    setStepValid(8, initialResult.success);
    clearL2ErrorsForStep(initialResult, 'Build Stream & GitLab', useConfigStore.getState);

    let timer: ReturnType<typeof setTimeout>;
    const subscription = watch((formValues) => {
      const result = buildStreamGitLabSchema.safeParse(formValues);
      setStepValid(8, result.success);
      clearL2ErrorsForStep(result, 'Build Stream & GitLab', useConfigStore.getState);

      clearTimeout(timer);
      timer = setTimeout(() => {
        updateWizardFields(formValues as Partial<any>);
      }, 300);
    });
    return () => { clearTimeout(timer); subscription.unsubscribe(); };
  }, [watch, setStepValid, updateWizardFields]);

  // Sync store enable values to form (one-way sync from store to form)
  useEffect(() => {
    setValue('enable_build_stream', enableBuildStream);
  }, [enableBuildStream, setValue]);

  useEffect(() => {
    setValue('enable_gitlab', enableGitlab);
  }, [enableGitlab, setValue]);

  return (
    <div className="space-y-6">
      {/* Build Stream Configuration */}
      {enableBuildStream && (
        <div className="space-y-2">
          <div className="form-group">
            <label className="form-label">Build Stream Configuration</label>
          </div>

          <div className="space-y-2">
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Build Stream Host IP Address (Required)</label>
                <input
                  type="text"
                  className={`form-input ${getError('build_stream_host_ip') ? 'error' : ''}`}
                  placeholder="Public IP or admin IP of OIM server"
                  {...register('build_stream_host_ip')}
                />
                {getError('build_stream_host_ip') && <span className="error-message">{String(getError('build_stream_host_ip')?.message)}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Build Stream Port (Required)</label>
                <input
                  type="number"
                  className={`form-input ${getError('build_stream_port') ? 'error' : ''}`}
                  placeholder="e.g., 8010"
                  {...register('build_stream_port')}
                />
                <p className="text-sm text-gray-600 mt-1">Default: 8010</p>
                {getError('build_stream_port') && <span className="error-message">{String(getError('build_stream_port')?.message)}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">AArch64 Inventory Host IP Address (Optional)</label>
                <input
                  type="text"
                  className={`form-input ${getError('aarch64_inventory_host_ip') ? 'error' : ''}`}
                  placeholder="Admin IP of aarch64 host"
                  {...register('aarch64_inventory_host_ip')}
                />
                {getError('aarch64_inventory_host_ip') && <span className="error-message">{String(getError('aarch64_inventory_host_ip')?.message)}</span>}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* GitLab Configuration */}
      {enableGitlab && (
        <div className="space-y-2">
          <div className="form-group">
            <label className="form-label">GitLab Configuration</label>
          </div>

          <div className="space-y-2">
            <div className="form-row form-row-4-col">
              <div className="form-group">
                <label className="form-label">GitLab Host IP Address (Required)</label>
                <input
                  type="text"
                  className={`form-input ${getError('gitlab_host') ? 'error' : ''}`}
                  placeholder="e.g., 172.16.107.254"
                  {...register('gitlab_host')}
                />
                {getError('gitlab_host') && <span className="error-message">{String(getError('gitlab_host')?.message)}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">GitLab Project Name (Required)</label>
                <input
                  type="text"
                  className={`form-input ${getError('gitlab_project_name') ? 'error' : ''}`}
                  placeholder="e.g., omnia-catalog"
                  {...register('gitlab_project_name')}
                />
                {getError('gitlab_project_name') && <span className="error-message">{String(getError('gitlab_project_name')?.message)}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Project Visibility (Required)</label>
                <select
                  className={`form-select ${getError('gitlab_project_visibility') ? 'error' : ''}`}
                  {...register('gitlab_project_visibility')}
                >
                  <option value="private">Private</option>
                  <option value="internal">Internal</option>
                  <option value="public">Public</option>
                </select>
                {getError('gitlab_project_visibility') && <span className="error-message">{String(getError('gitlab_project_visibility')?.message)}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Default Branch (Required)</label>
                <input
                  type="text"
                  className={`form-input ${getError('gitlab_default_branch') ? 'error' : ''}`}
                  placeholder="e.g., main"
                  {...register('gitlab_default_branch')}
                />
                {getError('gitlab_default_branch') && <span className="error-message">{String(getError('gitlab_default_branch')?.message)}</span>}
              </div>
            </div>

            <div className="form-row form-row-4-col">
              <div className="form-group">
                <label className="form-label">HTTPS Port (Required)</label>
                <input
                  type="number"
                  className={`form-input ${getError('gitlab_https_port') ? 'error' : ''}`}
                  placeholder="e.g., 443"
                  {...register('gitlab_https_port')}
                />
                <p className="text-sm text-gray-600 mt-1">Default: 443</p>
                {getError('gitlab_https_port') && <span className="error-message">{String(getError('gitlab_https_port')?.message)}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Minimum Storage in GB (Required)</label>
                <input
                  type="number"
                  className={`form-input ${getError('gitlab_min_storage_gb') ? 'error' : ''}`}
                  placeholder="e.g., 20"
                  {...register('gitlab_min_storage_gb')}
                />
                <p className="text-sm text-gray-600 mt-1">Default: 20</p>
                {getError('gitlab_min_storage_gb') && <span className="error-message">{String(getError('gitlab_min_storage_gb')?.message)}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Minimum Memory in GB (Required)</label>
                <input
                  type="number"
                  className={`form-input ${getError('gitlab_min_memory_gb') ? 'error' : ''}`}
                  placeholder="e.g., 4"
                  {...register('gitlab_min_memory_gb')}
                />
                <p className="text-sm text-gray-600 mt-1">Default: 4</p>
                {getError('gitlab_min_memory_gb') && <span className="error-message">{String(getError('gitlab_min_memory_gb')?.message)}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Minimum CPU Cores (Required)</label>
                <input
                  type="number"
                  className={`form-input ${getError('gitlab_min_cpu_cores') ? 'error' : ''}`}
                  placeholder="e.g., 2"
                  {...register('gitlab_min_cpu_cores')}
                />
                <p className="text-sm text-gray-600 mt-1">Default: 2</p>
                {getError('gitlab_min_cpu_cores') && <span className="error-message">{String(getError('gitlab_min_cpu_cores')?.message)}</span>}
              </div>
            </div>

            <div className="form-row form-row-4-col">
              <div className="form-group">
                <label className="form-label">Puma Workers (Required)</label>
                <input
                  type="number"
                  className={`form-input ${getError('gitlab_puma_workers') ? 'error' : ''}`}
                  placeholder="e.g., 2"
                  {...register('gitlab_puma_workers')}
                />
                <p className="text-sm text-gray-600 mt-1">Default: 2</p>
                {getError('gitlab_puma_workers') && <span className="error-message">{String(getError('gitlab_puma_workers')?.message)}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Sidekiq Concurrency (Required)</label>
                <input
                  type="number"
                  className={`form-input ${getError('gitlab_sidekiq_concurrency') ? 'error' : ''}`}
                  placeholder="e.g., 10"
                  {...register('gitlab_sidekiq_concurrency')}
                />
                <p className="text-sm text-gray-600 mt-1">Default: 10</p>
                {getError('gitlab_sidekiq_concurrency') && <span className="error-message">{String(getError('gitlab_sidekiq_concurrency')?.message)}</span>}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
