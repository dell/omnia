import { useFieldArray, UseFormRegister, Control, FieldErrors, UseFormSetValue } from 'react-hook-form';
import Button from '../../../../components/Button';
import { SlurmClusterRow } from './SlurmClusterRow';
import { OmniaHaDiscoveryFormData } from '../../schemas/omniaHaDiscoveryConfig';
import type { ValidationError } from '../../utils/l2Validation';

interface SlurmTabProps {
  register: UseFormRegister<OmniaHaDiscoveryFormData>;
  control: Control<OmniaHaDiscoveryFormData>;
  errors: FieldErrors<OmniaHaDiscoveryFormData>;
  setValue: UseFormSetValue<OmniaHaDiscoveryFormData>;
  validationErrors?: ValidationError[];
}

type SlurmCluster = OmniaHaDiscoveryFormData['slurm_cluster'][number];

export const EMPTY_SLURM_CLUSTER: Readonly<SlurmCluster> = Object.freeze({
  cluster_name: '',
  nfs_storage_name: '',
  vast_storage_name: '',
  skip_merge: false,
  node_discovery_mode: 'heterogeneous',
  node_hardware_defaults: [],
  config_sources: [],
});

export const SlurmTab = ({ register, control, errors, setValue, validationErrors }: SlurmTabProps) => {
  const { fields, append, remove } = useFieldArray({
    control,
    name: 'slurm_cluster',
  });

  return (
    <div className="space-y-6">
      <div className="form-group">
        <label className="form-label">Slurm Cluster Configuration (Required)</label>
        {fields.map((field, index) => (
          <SlurmClusterRow
            key={field.id}
            index={index}
            register={register}
            control={control}
            errors={errors}
            setValue={setValue}
            validationErrors={validationErrors}
            remove={() => remove(index)}
            canRemove={fields.length > 1}
          />
        ))}
        <Button variant="primary" onClick={() => append({ ...EMPTY_SLURM_CLUSTER })}>Add Slurm Cluster</Button>
      </div>
    </div>
  );
};
