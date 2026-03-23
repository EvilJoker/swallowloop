import { useState } from 'react';
import { Plus } from 'lucide-react';
import type { Issue, Stage } from '@/types';
import { STAGES } from '@/types';
import { KanbanLane } from './KanbanLane';
import { NewIssueDialog } from '@/components/issue/NewIssueDialog';

interface KanbanBoardProps {
  issues: Issue[];
  onIssueClick?: (issue: Issue) => void;
  onIssueCreated?: (issue: Issue) => void;
  className?: string;
}

export function KanbanBoard({ issues, onIssueClick, onIssueCreated, className }: KanbanBoardProps) {
  const [showNewDialog, setShowNewDialog] = useState(false);

  // 按阶段分组
  const issuesByStage = STAGES.reduce<Record<Stage, Issue[]>>((acc, stage) => {
    acc[stage.key] = issues.filter(
      (issue) => issue.status === 'active' && issue.currentStage === stage.key
    );
    return acc;
  }, {} as Record<Stage, Issue[]>);

  const handleIssueCreated = (issue: Issue) => {
    onIssueCreated?.(issue);
    setShowNewDialog(false);
  };

  return (
    <div className={className}>
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-slate-200">
        <h2 className="font-semibold text-slate-800">泳道图</h2>
        <button
          onClick={() => setShowNewDialog(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500 text-white hover:bg-blue-600 rounded-lg transition-colors text-sm font-medium"
        >
          <Plus className="h-4 w-4" />
          新建 Issue
        </button>
      </div>

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

      {/* 新建 Issue 对话框 */}
      {showNewDialog && (
        <NewIssueDialog
          onClose={() => setShowNewDialog(false)}
          onCreated={handleIssueCreated}
        />
      )}
    </div>
  );
}
