import { motion } from 'framer-motion';

interface CompletionBarProps {
  label: string;
  percentage: number;
  color?: string;
}

export function CompletionBar({ label, percentage, color = 'bg-accent' }: CompletionBarProps) {
  const clamped = Math.min(Math.max(percentage, 0), 100);

  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-1 text-xs">
        <span className="font-medium text-gray-700 dark:text-gray-300">{label}</span>
        <span className="font-bold text-navy dark:text-accent">{clamped}%</span>
      </div>
      <div className="w-full h-2.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
        <motion.div
          className={`h-full ${color} rounded-full`}
          initial={{ width: 0 }}
          animate={{ width: `${clamped}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}
