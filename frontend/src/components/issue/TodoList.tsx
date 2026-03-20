import { cn } from '@/lib/utils';
import type { TodoItem } from '@/types';
import { Check, Circle, Loader2, X } from 'lucide-react';

interface TodoListProps {
  items: TodoItem[];
  className?: string;
}

const STATUS_ICONS = {
  pending: Circle,
  in_progress: Loader2,
  completed: Check,
  failed: X,
};

const STATUS_STYLES = {
  pending: 'text-gray-400',
  in_progress: 'text-blue-500 animate-spin',
  completed: 'text-green-500',
  failed: 'text-red-500',
};

export function TodoList({ items, className }: TodoListProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {items.map((item) => {
        const Icon = STATUS_ICONS[item.status];
        return (
          <div
            key={item.id}
            className={cn(
              'flex items-start gap-3 p-3 rounded-lg border',
              item.status === 'completed' && 'bg-green-50 border-green-200',
              item.status === 'failed' && 'bg-red-50 border-red-200',
              item.status === 'in_progress' && 'bg-blue-50 border-blue-200',
              item.status === 'pending' && 'bg-gray-50 border-gray-200'
            )}
          >
            <Icon className={cn('h-4 w-4 mt-0.5 flex-shrink-0', STATUS_STYLES[item.status])} />
            <span
              className={cn(
                'text-sm flex-1',
                item.status === 'completed' && 'text-green-700 line-through',
                item.status === 'failed' && 'text-red-700',
                item.status === 'in_progress' && 'text-blue-700',
                item.status === 'pending' && 'text-gray-700'
              )}
            >
              {item.content}
            </span>
          </div>
        );
      })}
    </div>
  );
}
