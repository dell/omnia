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
interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
}

const LoadingSpinner = ({ size = 'medium' }: LoadingSpinnerProps) => {
  const sizeStyles = {
    small: { width: '16px', height: '16px', borderWidth: '2px' },
    medium: { width: '24px', height: '24px', borderWidth: '3px' },
    large: { width: '40px', height: '40px', borderWidth: '4px' },
  };

  return (
    <div
      style={{
        border: `${sizeStyles[size].borderWidth} solid #f3f3f3`,
        borderTop: `${sizeStyles[size].borderWidth} solid #0097a7`,
        borderRadius: '50%',
        ...sizeStyles[size],
        animation: 'spin 1s linear infinite',
      }}
    />
  );
};

// Add keyframes to CSS
const style = document.createElement('style');
style.textContent = `
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;
document.head.appendChild(style);

export default LoadingSpinner;
