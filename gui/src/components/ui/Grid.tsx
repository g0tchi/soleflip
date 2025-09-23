import { HTMLAttributes, forwardRef } from 'react';
import { clsx } from 'clsx';

export interface GridProps extends HTMLAttributes<HTMLDivElement> {
  cols?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
  gap?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
  responsive?: boolean;
  children: React.ReactNode;
}

const Grid = forwardRef<HTMLDivElement, GridProps>(
  (
    {
      className,
      cols = 1,
      gap = 'md',
      responsive = true,
      children,
      ...props
    },
    ref
  ) => {
    const baseClasses = ['grid'];

    // Responsive grid columns
    const responsiveColumns = responsive
      ? {
          1: 'grid-cols-1',
          2: 'grid-cols-1 sm:grid-cols-2',
          3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
          4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
          5: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5',
          6: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6',
          12: 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-12',
        }[cols]
      : `grid-cols-${cols}`;

    const gaps = {
      none: 'gap-0',
      sm: 'gap-3 sm:gap-4',
      md: 'gap-4 sm:gap-6',
      lg: 'gap-6 sm:gap-8',
      xl: 'gap-8 sm:gap-10',
    };

    const classes = clsx(
      baseClasses,
      responsiveColumns,
      gaps[gap],
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

Grid.displayName = 'Grid';

export { Grid };