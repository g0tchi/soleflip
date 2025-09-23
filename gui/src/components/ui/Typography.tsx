import { HTMLAttributes, forwardRef } from 'react';
import { clsx } from 'clsx';

// Heading component
interface HeadingProps extends HTMLAttributes<HTMLHeadingElement> {
  level?: 1 | 2 | 3 | 4 | 5 | 6;
  variant?: 'hero' | 'display' | 'title' | 'subtitle' | 'body';
  gradient?: boolean;
  children: React.ReactNode;
}

const Heading = forwardRef<HTMLHeadingElement, HeadingProps>(
  (
    {
      level = 2,
      variant = 'title',
      gradient = false,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const HeadingTag = `h${level}` as keyof JSX.IntrinsicElements;

    const baseClasses = [
      'font-bold tracking-tight',
      'transition-colors duration-200',
    ];

    const variants = {
      hero: [
        'text-5xl md:text-6xl lg:text-7xl',
        'leading-none font-black',
        'tracking-tighter',
      ],
      display: [
        'text-3xl md:text-4xl lg:text-5xl',
        'leading-tight',
        'tracking-tight',
      ],
      title: [
        'text-2xl md:text-3xl',
        'leading-snug',
      ],
      subtitle: [
        'text-xl md:text-2xl',
        'leading-relaxed font-semibold',
      ],
      body: [
        'text-lg md:text-xl',
        'leading-relaxed font-medium',
      ],
    };

    const colorClasses = gradient
      ? [
          'bg-gradient-to-r from-white via-purple-100 to-green-100',
          'bg-clip-text text-transparent',
        ]
      : ['text-white'];

    const classes = clsx(
      baseClasses,
      variants[variant],
      colorClasses,
      className
    );

    return (
      <HeadingTag
        ref={ref}
        className={classes}
        {...(props as any)}
      >
        {children}
      </HeadingTag>
    );
  }
);

// Text component
interface TextProps extends HTMLAttributes<HTMLParagraphElement> {
  variant?: 'body' | 'caption' | 'label' | 'small';
  color?: 'primary' | 'secondary' | 'muted' | 'inverse';
  weight?: 'normal' | 'medium' | 'semibold' | 'bold';
  size?: 'xs' | 'sm' | 'base' | 'lg' | 'xl';
  children: React.ReactNode;
}

const Text = forwardRef<HTMLParagraphElement, TextProps>(
  (
    {
      variant = 'body',
      color = 'primary',
      weight = 'normal',
      size,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const baseClasses = [
      'transition-colors duration-200',
    ];

    const variants = {
      body: ['leading-relaxed'],
      caption: ['text-xs uppercase tracking-wider font-medium leading-tight'],
      label: ['font-medium leading-tight'],
      small: ['text-sm leading-snug'],
    };

    const colors = {
      primary: 'text-white',
      secondary: 'text-gray-300',
      muted: 'text-gray-400',
      inverse: 'text-gray-900',
    };

    const weights = {
      normal: 'font-normal',
      medium: 'font-medium',
      semibold: 'font-semibold',
      bold: 'font-bold',
    };

    const sizes = size ? {
      xs: 'text-xs',
      sm: 'text-sm',
      base: 'text-base',
      lg: 'text-lg',
      xl: 'text-xl',
    }[size] : '';

    const classes = clsx(
      baseClasses,
      variants[variant],
      colors[color],
      weights[weight],
      sizes,
      className
    );

    return (
      <p
        ref={ref}
        className={classes}
        {...props}
      >
        {children}
      </p>
    );
  }
);

Heading.displayName = 'Heading';
Text.displayName = 'Text';

export { Heading, Text };