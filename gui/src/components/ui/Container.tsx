import { HTMLAttributes, forwardRef } from 'react';
import { clsx } from 'clsx';

export interface ContainerProps extends HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
  center?: boolean;
  children: React.ReactNode;
}

const Container = forwardRef<HTMLDivElement, ContainerProps>(
  (
    {
      className,
      size = 'lg',
      padding = 'md',
      center = true,
      children,
      ...props
    },
    ref
  ) => {
    const baseClasses = ['w-full'];

    const sizes = {
      sm: 'max-w-2xl',
      md: 'max-w-4xl',
      lg: 'max-w-6xl',
      xl: 'max-w-7xl',
      full: 'max-w-none',
    };

    const paddings = {
      none: '',
      sm: 'px-4 sm:px-6',
      md: 'px-4 sm:px-6 lg:px-8',
      lg: 'px-6 sm:px-8 lg:px-12',
      xl: 'px-8 sm:px-12 lg:px-16',
    };

    const classes = clsx(
      baseClasses,
      sizes[size],
      paddings[padding],
      center && 'mx-auto',
      className
    );

    return (
      <div
        ref={ref}
        className={classes}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Container.displayName = 'Container';

export { Container };