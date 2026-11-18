import { motion } from 'framer-motion';
import { Card } from '../ui/Card';

interface DataPoint {
  label: string;
  value: number | null;
}

interface ActivityChartProps {
  data: DataPoint[];
  title?: string;
}

export function ActivityChart({ data, title = 'Activité des 7 derniers jours' }: ActivityChartProps) {
  const maxVal = Math.max(...data.map((d) => d.value ?? 0), 1);

  return (
    <Card className="p-5">
      <h3 className="font-syne font-bold text-navy dark:text-white text-base mb-6">
        {title}
      </h3>

      <div className="flex items-end justify-between gap-2 h-44 pt-4 px-2">
        {data.map((item, idx) => {
          const heightPct = ((item.value ?? 0) / maxVal) * 100;
          return (
            <div key={item.label} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
              <span className="text-[11px] font-semibold text-gray-400 group-hover:text-accent transition-colors">
                {item.value ?? '—'}
              </span>

              <div className="w-full max-w-[36px] bg-gray-100 dark:bg-gray-700/60 rounded-t-lg h-full flex items-end overflow-hidden">
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: `${heightPct}%` }}
                  transition={{ delay: idx * 0.05, duration: 0.5, ease: 'easeOut' }}
                  className={`w-full rounded-t-lg transition-all group-hover:brightness-110 ${
                    item.value === null ? 'bg-gray-300 dark:bg-gray-600' : 'bg-gradient-to-t from-accent to-accent-dark'
                  }`}
                />
              </div>

              <span className="text-[11px] font-medium text-gray-500 dark:text-gray-400 truncate max-w-full">
                {item.label}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
