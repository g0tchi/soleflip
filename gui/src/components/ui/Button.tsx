import { ButtonHTMLAttributes, forwardRef } from 'react';
import { clsx } from 'clsx';
import { LucideIcon } from 'lucide-react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  icon?: LucideIcon;
  iconPosition?: 'left' | 'right';
  isLoading?: boolean;
  fullWidth?: boolean;
  children: React.ReactNode;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      icon: Icon,
      iconPosition = 'left',
      isLoading = false,
      fullWidth = false,
      children,
      disabled,
      type = 'button',
      ...props
    },
    ref
  ) => {
    const baseClasses = [
      // Base styles
      'inline-flex items-center justify-center font-semibold transition-all duration-300 ease-out',
      'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none',
      'relative overflow-hidden',
      // Transform & hover effects
      'hover:scale-[1.02] active:scale-[0.98]',
      'transform-gpu will-change-transform',
    ];

    const variants = {
      primary: [
        'bg-gradient-to-r from-purple-600 to-purple-700',
        'hover:from-purple-700 hover:to-purple-800',
        'text-white border-purple-600',
        'shadow-lg shadow-purple-500/25',
        'hover:shadow-xl hover:shadow-purple-500/40',
        'focus:ring-purple-500',
      ],
      secondary: [
        'bg-gradient-to-r from-green-500 to-green-600',
        'hover:from-green-600 hover:to-green-700',
        'text-white border-green-500',
        'shadow-lg shadow-green-500/25',
        'hover:shadow-xl hover:shadow-green-500/40',
        'focus:ring-green-500',
      ],
      outline: [
        'bg-transparent border border-gray-600',
        'text-gray-300 hover:text-white',
        'hover:bg-purple-600/10 hover:border-purple-500',
        'focus:ring-purple-500',
      ],
      ghost: [
        'bg-transparent text-gray-300',
        'hover:text-white hover:bg-gray-800/50',
        'focus:ring-gray-500',
      ],
      danger: [
        'bg-gradient-to-r from-red-500 to-red-600',
        'hover:from-red-600 hover:to-red-700',
        'text-white border-red-500',
        'shadow-lg shadow-red-500/25',
        'hover:shadow-xl hover:shadow-red-500/40',
        'focus:ring-red-500',
      ],
    };

    const sizes = {
      sm: ['px-3 py-2 text-sm rounded-lg', Icon && 'gap-2'],
      md: ['px-6 py-3 text-base rounded-xl', Icon && 'gap-3'],
      lg: ['px-8 py-4 text-lg rounded-2xl', Icon && 'gap-3'],
      xl: ['px-10 py-5 text-xl rounded-2xl', Icon && 'gap-4'],
    };

    const iconSizes = {
      sm: 'w-4 h-4',
      md: 'w-5 h-5',
      lg: 'w-6 h-6',
      xl: 'w-7 h-7',
    };

    const classes = clsx(
      baseClasses,
      variants[variant],
      sizes[size],
      fullWidth && 'w-full',
      className
    );

    const iconClasses = clsx(
      iconSizes[size],
      isLoading && 'animate-spin'
    );

    const content = (
      <>
        {/* Shimmer effect overlay */}
        <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent" />

        {Icon && iconPosition === 'left' && (
          <Icon className={iconClasses} aria-hidden="true" />
        )}

        <span className="relative z-10">{children}</span>

        {Icon && iconPosition === 'right' && (
          <Icon className={iconClasses} aria-hidden="true" />
        )}
      </>
    );

    return (
      <button
        ref={ref}
        type={type}
        className={classes}
        disabled={disabled || isLoading}
        aria-busy={isLoading}
        {...props}
      >
        {content}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };