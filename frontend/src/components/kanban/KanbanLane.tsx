import { cn } from '@/lib/utils';
import type { Issue, IssueRunningStatus } from '@/types';
import { IssueCard } from './IssueCard';

interface KanbanLaneProps {
  laneKey: IssueRunningStatus;
  issues: Issue[];
  onIssueClick?: (issue: Issue) => void;
  onIssueDelete?: (issue: Issue) => void;
  onIssueMove?: (issueId: string, toLane: IssueRunningStatus) => void;
  className?: string;
}

export function KanbanLane({
  laneKey,
  issues,
  onIssueClick,
  onIssueDelete,
  onIssueMove,
  className,
}: KanbanLaneProps) {
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.add('bg-blue-50');
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove('bg-blue-50');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.remove('bg-blue-50');
    const issueId = e.dataTransfer.getData('issueId');
    if (issueId && onIssueMove) {
      onIssueMove(issueId, laneKey);
    }
  };

  return (
    <div
      className={cn('flex flex-col min-w-[200px] w-[200px]', className)}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* 卡片列表 */}
      <div className="flex-1 p-2 space-y-2 overflow-y-auto">
        {issues.map((issue) => (
          <IssueCard
            key={issue.id}
            issue={issue}
            onClick={() => onIssueClick?.(issue)}
            onDelete={onIssueDelete}
            draggable={issue.runningStatus === 'new'}
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
