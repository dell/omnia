import { Controller, ControllerProps, FieldValues } from 'react-hook-form';

interface FormFieldProps extends Omit<ControllerProps<FieldValues, any>, 'render'> {
  label: string;
  required?: boolean;
  placeholder?: string;
  type?: 'text' | 'number' | 'password' | 'select';
  options?: { value: string; label: string }[];
  className?: string;
}

export const FormField = ({
  label,
  required = false,
  placeholder,
  type = 'text',
  options,
  className = '',
  ...controllerProps
}: FormFieldProps) => {
  const requiredText = required ? '(Required)' : '(Optional)';
  const displayLabel = `${label} ${requiredText}`;

  return (
    <Controller
      {...controllerProps}
      render={({ field, fieldState: { error } }) => (
        <div className={`form-group ${className}`}>
          <label className="form-label">{displayLabel}</label>
          {type === 'select' && options ? (
            <select
              className={`form-select ${error ? 'error' : ''}`}
              {...field}
            >
              <option value="">{placeholder || 'Select an option'}</option>
              {options.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          ) : (
            <input
              type={type}
              className={`form-input ${error ? 'error' : ''}`}
              placeholder={placeholder}
              {...field}
            />
          )}
          {error && <span className="error-message">{error.message}</span>}
        </div>
      )}
    />
  );
};
