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
