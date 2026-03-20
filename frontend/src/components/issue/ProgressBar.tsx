import { cn } from '@/lib/utils';

interface ProgressBarProps {
  value: number;
  className?: string;
}

export function ProgressBar({ value, className }: ProgressBarProps) {
  const clampedValue = Math.max(0, Math.min(100, value));

  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-600">执行进度</span>
        <span className="font-medium text-gray-900">{clampedValue}%</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-300',
            clampedValue === 100 ? 'bg-green-500' : 'bg-blue-600'
          )}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
    </div>
  );
}
