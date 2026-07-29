import { useState, useEffect } from 'react';

type DnsInputProps = {
  value: string[];
  onChange: (val: string[]) => void;
  onBlur: () => void;
  error?: { message?: string } | Array<{ message?: string } | undefined>;
  placeholder?: string;
};

export const DnsInput = ({ value, onChange, onBlur, error, placeholder }: DnsInputProps) => {
  const [displayValue, setDisplayValue] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  // Sync external value → display, but only when not actively editing
  useEffect(() => {
    if (!isFocused) {
      setDisplayValue(Array.isArray(value) ? value.join(', ') : '');
    }
  }, [value, isFocused]);

  const errMsg = typeof error === 'object' && !Array.isArray(error)
    ? error?.message
    : Array.isArray(error)
      ? error.find((e) => e)?.message
      : undefined;

  return (
    <>
      <input
        type="text"
        className={`form-input ${error ? 'error' : ''}`}
        placeholder={placeholder || "comma-separated IPs, e.g., 8.8.8.8, 8.8.4.4"}
        value={displayValue}
        onFocus={() => setIsFocused(true)}
        onChange={(e) => setDisplayValue(e.target.value)}
        onBlur={() => {
          const parsed = displayValue
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean);
          onChange(parsed);
          setDisplayValue(parsed.join(', ')); // reflect cleanup
          setIsFocused(false);
          onBlur();
        }}
      />
      {errMsg && <span className="error-message">{errMsg}</span>}
    </>
  );
};
