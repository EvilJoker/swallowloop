import { cn } from '@/lib/utils';

interface LogEntry {
  id: string;
  timestamp: Date;
  level: 'info' | 'warn' | 'error' | 'success';
  message: string;
}

interface LogViewerProps {
  logs: LogEntry[];
  className?: string;
}

const LEVEL_STYLES = {
  info: 'text-blue-600',
  warn: 'text-yellow-600',
  error: 'text-red-600',
  success: 'text-green-600',
};

const LEVEL_PREFIX = {
  info: '[INFO]',
  warn: '[WARN]',
  error: '[ERROR]',
  success: '[OK]',
};

export function LogViewer({ logs, className }: LogViewerProps) {
  return (
    <div
      className={cn(
        'bg-gray-900 rounded-lg p-4 font-mono text-sm overflow-auto max-h-64',
        className
      )}
    >
      {logs.length === 0 ? (
        <div className="text-gray-500">暂无日志</div>
      ) : (
        <div className="space-y-1">
          {logs.map((log) => (
            <div key={log.id} className="flex gap-2">
              <span className="text-gray-500">
                {log.timestamp.toLocaleTimeString('zh-CN')}
              </span>
              <span className={LEVEL_STYLES[log.level]}>
                {LEVEL_PREFIX[log.level]}
              </span>
              <span className="text-gray-300">{log.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
