// Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
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
