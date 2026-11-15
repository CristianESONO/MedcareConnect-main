import { cn } from '../../lib/cn';
import { InputHTMLAttributes, forwardRef, ReactNode } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  icon?: ReactNode;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ icon, error, className, ...props }, ref) => (
    <div className="relative w-full">
      {icon && (
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
          {icon}
        </span>
      )}
      <input
        ref={ref}
        className={cn(
          'w-full rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800',
          'text-gray-800 dark:text-white placeholder-gray-400',
          'focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent',
          'transition-all duration-200 py-2.5 pr-4',
          icon ? 'pl-10' : 'pl-4',
          error && 'border-red-400 focus:ring-red-400/40',
          className
        )}
        {...props}
      />
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </div>
  )
);
Input.displayName = 'Input';
