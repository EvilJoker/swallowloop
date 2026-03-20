import { useState } from 'react';
import type { Issue } from '@/types';
import { KanbanBoard } from '@/components/kanban/KanbanBoard';
import { IssueDetail } from '@/components/issue/IssueDetail';
import { mockIssues } from '@/types/mock';

export function Home() {
  const [issues] = useState<Issue[]>(mockIssues);
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);

  const handleIssueClick = (issue: Issue) => {
    setSelectedIssue(issue);
  };

  const handleCloseDetail = () => {
    setSelectedIssue(null);
  };

  const handleApprove = () => {
    if (!selectedIssue) return;
    // TODO: 实现通过逻辑
    console.log('Issue approved:', selectedIssue.id);
    setSelectedIssue(null);
  };

  const handleReject = (reason: string) => {
    if (!selectedIssue) return;
    // TODO: 实现打回逻辑
    console.log('Issue rejected:', selectedIssue.id, reason);
    setSelectedIssue(null);
  };

  const handleTrigger = () => {
    if (!selectedIssue) return;
    // TODO: 实现触发 AI 更新逻辑
    console.log('Trigger AI update for:', selectedIssue.id);
  };

  return (
    <div className="h-full flex">
      {/* 泳道图区域 */}
      <div className={`flex-1 transition-all ${selectedIssue ? 'mr-0' : ''}`}>
        <KanbanBoard issues={issues} onIssueClick={handleIssueClick} className="h-full" />
      </div>

      {/* Issue 详情侧边栏 */}
      {selectedIssue && (
        <div className="w-[500px] border-l border-gray-200 flex flex-col">
          <IssueDetail
            issue={selectedIssue}
            onClose={handleCloseDetail}
            onApprove={handleApprove}
            onReject={handleReject}
            onTrigger={handleTrigger}
            className="flex-1"
          />
        </div>
      )}
    </div>
  );
}
