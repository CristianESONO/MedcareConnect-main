import { cn } from '../../lib/cn';
import { HTMLAttributes } from 'react';

type BadgeVariant = 'green' | 'accent' | 'navy' | 'gray' | 'warning' | 'danger';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const cls: Record<BadgeVariant, string> = {
  green:   'bg-sipn-green/10 text-sipn-green border-sipn-green/20',
  accent:  'bg-accent/10 text-accent border-accent/20',
  navy:    'bg-navy/10 text-navy border-navy/20',
  gray:    'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-700 dark:text-gray-300',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  danger:  'bg-red-50 text-red-600 border-red-200',
};

export function Badge({ variant = 'gray', className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border',
        cls[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
