import { ReactNode } from 'react';

interface ButtonProps {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'tertiary' | 'outline' | 'link';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  disabled?: boolean;
}

const Button = ({
  children,
  variant = 'secondary',
  size = 'md',
  className = '',
  style = {},
  onClick,
  type = 'button',
  disabled = false,
}: ButtonProps) => {
  const baseClasses = 'button';
  const variantClasses = `button-${variant}`;
  const sizeClasses = size === 'sm' ? 'text-sm' : size === 'lg' ? 'text-lg' : '';
  const combinedClassName = `${baseClasses} ${variantClasses} ${sizeClasses} ${className} ${disabled ? 'disabled' : ''}`.trim();

  return (
    <button
      type={type}
      className={combinedClassName}
      style={style}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
};

export default Button;
