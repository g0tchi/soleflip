import { HTMLAttributes, forwardRef } from 'react';
import { clsx } from 'clsx';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'metric' | 'interactive';
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
  children: React.ReactNode;
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      variant = 'default',
      padding = 'md',
      children,
      ...props
    },
    ref
  ) => {
    const baseClasses = [
      // Base card styling
      'relative overflow-hidden rounded-2xl transition-all duration-300 ease-out',
      'backdrop-filter backdrop-blur-xl backdrop-saturate-150',
      'border border-gray-700/30',
      // Focus and hover states
      'group hover:scale-[1.01] hover:-translate-y-1',
      'focus-within:ring-2 focus-within:ring-purple-500/50 focus-within:ring-offset-2 focus-within:ring-offset-gray-900',
    ];

    const variants = {
      default: [
        'bg-gray-800/40',
        'hover:bg-gray-800/60',
        'shadow-lg shadow-black/10',
        'hover:shadow-2xl hover:shadow-black/20',
        'border-gray-700/30 hover:border-gray-600/50',
      ],
      elevated: [
        'bg-gradient-to-br from-gray-800/50 to-gray-900/30',
        'hover:from-gray-700/60 hover:to-gray-800/40',
        'shadow-xl shadow-black/20',
        'hover:shadow-2xl hover:shadow-purple-500/10',
        'border-gray-600/40 hover:border-purple-500/30',
        // Subtle gradient border effect
        'before:absolute before:inset-0 before:p-[1px] before:bg-gradient-to-r before:from-purple-500/20 before:to-green-500/20 before:rounded-2xl before:-z-10',
      ],
      metric: [
        'bg-gradient-to-br from-purple-600/10 via-gray-800/40 to-green-600/10',
        'hover:from-purple-600/20 hover:via-gray-800/60 hover:to-green-600/20',
        'shadow-lg shadow-purple-500/5',
        'hover:shadow-xl hover:shadow-purple-500/20',
        'border-purple-500/20 hover:border-purple-400/40',
        // Accent line on the right
        'after:absolute after:top-0 after:right-0 after:w-1 after:h-full after:bg-gradient-to-b after:from-purple-500 after:to-green-500 after:rounded-r-2xl',
      ],
      interactive: [
        'bg-gray-800/30 hover:bg-gray-700/50',
        'cursor-pointer',
        'shadow-md shadow-black/10',
        'hover:shadow-lg hover:shadow-purple-500/20',
        'border-gray-700/30 hover:border-purple-500/50',
        'active:scale-[0.99] active:shadow-sm',
      ],
    };

    const paddings = {
      none: '',
      sm: 'p-4',
      md: 'p-6',
      lg: 'p-8',
      xl: 'p-10',
    };

    const classes = clsx(
      baseClasses,
      variants[variant],
      paddings[padding],
      className
    );

    return (
      <div
        ref={ref}
        className={classes}
        {...props}
      >
        {/* Shimmer effect for elevated cards */}
        {variant === 'elevated' && (
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000 ease-out" />
        )}

        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

export { Card };