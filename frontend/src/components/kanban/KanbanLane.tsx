import { cn } from '@/lib/utils';
import type { Issue } from '@/types';
import { IssueCard } from './IssueCard';

interface KanbanLaneProps {
  issues: Issue[];
  onIssueClick?: (issue: Issue) => void;
  onIssueDelete?: (issue: Issue) => void;
  className?: string;
}

export function KanbanLane({ issues, onIssueClick, onIssueDelete, className }: KanbanLaneProps) {
  return (
    <div className={cn('flex flex-col min-w-[200px] w-[200px]', className)}>
      {/* 卡片列表 */}
      <div className="flex-1 p-2 space-y-2 overflow-y-auto">
        {issues.map((issue) => (
          <IssueCard
            key={issue.id}
            issue={issue}
            onClick={() => onIssueClick?.(issue)}
            onDelete={onIssueDelete}
          />
        ))}

        {issues.length === 0 && (
          <div className="py-8 text-center text-slate-400 text-sm border-2 border-dashed border-slate-200 rounded-lg bg-slate-50">
            暂无问题
          </div>
        )}
      </div>
    </div>
  );
}
