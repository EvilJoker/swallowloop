import type { Issue, Stage } from '@/types';
import { STAGES } from '@/types';
import { KanbanLane } from './KanbanLane';

interface KanbanBoardProps {
  issues: Issue[];
  onIssueClick?: (issue: Issue) => void;
  className?: string;
}

export function KanbanBoard({ issues, onIssueClick, className }: KanbanBoardProps) {
  // 按阶段分组
  const issuesByStage = STAGES.reduce<Record<Stage, Issue[]>>((acc, stage) => {
    acc[stage.key] = issues.filter(
      (issue) => issue.status === 'active' && issue.currentStage === stage.key
    );
    return acc;
  }, {} as Record<Stage, Issue[]>);

  return (
    <div className={className}>
      {/* 泳道图头部 - 固定7列 */}
      <div className="flex bg-slate-100 border-b border-slate-200">
        {STAGES.map((stage) => (
          <div
            key={stage.key}
            className="w-[200px] min-w-[200px] px-3 py-2.5 border-r border-slate-200 last:border-r-0"
          >
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-slate-700 text-sm">{stage.label}</h3>
              <span className="text-xs text-slate-500 bg-slate-200 px-1.5 py-0.5 rounded-full">
                {issuesByStage[stage.key].length}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* 泳道内容 */}
      <div className="flex bg-slate-50 overflow-x-auto">
        {STAGES.map((stage) => (
          <KanbanLane
            key={stage.key}
            issues={issuesByStage[stage.key]}
            onIssueClick={onIssueClick}
            className="border-r border-slate-100 last:border-r-0"
          />
        ))}
      </div>
    </div>
  );
}
