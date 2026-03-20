import { cn } from '@/lib/utils';
import type { Comment } from '@/types';
import { Check, X } from 'lucide-react';

interface CommentHistoryProps {
  comments: Comment[];
  className?: string;
}

const ACTION_CONFIG = {
  approve: { icon: Check, label: '通过', className: 'text-green-600 bg-green-50' },
  reject: { icon: X, label: '打回', className: 'text-red-600 bg-red-50' },
};

export function CommentHistory({ comments, className }: CommentHistoryProps) {
  if (comments.length === 0) {
    return (
      <div className={cn('py-8 text-center text-gray-400 text-sm', className)}>
        暂无评论记录
      </div>
    );
  }

  return (
    <div className={cn('space-y-3', className)}>
      {comments.map((comment) => {
        const config = ACTION_CONFIG[comment.action];
        return (
          <div
            key={comment.id}
            className="p-3 bg-gray-50 rounded-lg border border-gray-100"
          >
            <div className="flex items-center gap-2 mb-2">
              <span
                className={cn(
                  'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium',
                  config.className
                )}
              >
                <config.icon className="h-3 w-3" />
                {config.label}
              </span>
              <span className="text-xs text-gray-500">
                {comment.createdAt.toLocaleString('zh-CN')}
              </span>
            </div>
            {comment.content && (
              <p className="text-sm text-gray-700">{comment.content}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
