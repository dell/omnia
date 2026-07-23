import { VictoriaMetricsSection } from './sinks/VictoriaMetricsSection';
import { VictoriaLogsSection } from './sinks/VictoriaLogsSection';
import { KafkaConfigurationSection } from './sinks/KafkaConfigurationSection';
import { KafkaStorageResourcesSection } from './sinks/KafkaStorageResourcesSection';
import { VictoriaClusterStorageSection } from './sinks/VictoriaClusterStorageSection';
import { VictoriaLogsClusterStorageSection } from './sinks/VictoriaLogsClusterStorageSection';
import type { UseFormRegister, FieldErrors, Control } from 'react-hook-form';
import { TelemetryConfigStorageFormData } from '../../schemas/telemetryConfigStorage';
import { useFormErrors } from '../../hooks/useFormErrors';
import type { ValidationError } from '../../utils/l2Validation';

interface SinksTabProps {
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  errors: FieldErrors<TelemetryConfigStorageFormData>;
  control: Control<TelemetryConfigStorageFormData>;
  needsVictoriaMetrics?: boolean;
  needsVictoriaLogs?: boolean;
  needsKafka?: boolean;
  validationErrors?: ValidationError[];
}

export const SinksTab = ({ register, errors, control, needsVictoriaMetrics, needsVictoriaLogs, needsKafka, validationErrors }: SinksTabProps) => {
  const getError = useFormErrors(errors, validationErrors);

  return (
    <div className="space-y-6">
      {!needsVictoriaMetrics && !needsVictoriaLogs && !needsKafka && (
        <p className="text-small-muted">All sink sections below are disabled. Enable telemetry sources with collection targets to configure sinks.</p>
      )}
      <VictoriaMetricsSection enabled={!!needsVictoriaMetrics} register={register} getError={getError} control={control} />
      <VictoriaLogsSection enabled={!!needsVictoriaLogs} register={register} getError={getError} control={control} />
      <KafkaConfigurationSection enabled={!!needsKafka} register={register} getError={getError} />
      <KafkaStorageResourcesSection enabled={!!needsKafka} register={register} getError={getError} />
      <VictoriaClusterStorageSection enabled={!!needsVictoriaMetrics} register={register} getError={getError} />
      <VictoriaLogsClusterStorageSection enabled={!!needsVictoriaLogs} register={register} getError={getError} />
    </div>
  );
};
