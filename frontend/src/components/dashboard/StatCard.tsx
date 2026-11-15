import { motion } from 'framer-motion';
import { ReactNode } from 'react';
import { Card } from '../ui/Card';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  index?: number;
}

export function StatCard({ title, value, subtitle, icon, trend, index = 0 }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
    >
      <Card className="p-5 flex flex-col justify-between h-full">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
            {title}
          </span>
          <div className="p-2.5 rounded-xl bg-accent/10 text-accent dark:bg-accent/20">
            {icon}
          </div>
        </div>

        <div className="mt-4">
          <div className="flex items-baseline gap-2">
            <h3 className="font-syne font-bold text-2xl text-navy dark:text-white">
              {value}
            </h3>
            {trend && (
              <span
                className={`flex items-center text-xs font-semibold ${
                  trend.isPositive ? 'text-sipn-green' : 'text-red-500'
                }`}
              >
                {trend.isPositive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                {trend.value}%
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
      </Card>
    </motion.div>
  );
}
