import { cn } from '../../lib/cn';
import { HTMLAttributes } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
}

export function Card({ hover = false, className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700',
        'shadow-[0_4px_16px_rgba(10,92,138,.07)]',
        hover && 'hover:shadow-[0_8px_24px_rgba(10,92,138,.12)] hover:-translate-y-0.5 transition-all duration-200 cursor-pointer',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
