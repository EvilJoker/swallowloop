import { useState } from 'react';
import { Search, X, FileText, CheckCircle, Clock, ArrowRight } from 'lucide-react';
import { mockIssues } from '@/types/mock';
import { cn } from '@/lib/utils';

interface ArchiveModalProps {
  issue: typeof mockIssues[0];
  onClose: () => void;
}

function ArchiveModal({ issue, onClose }: ArchiveModalProps) {
  const currentStage = issue.stages[issue.currentStage];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white rounded-2xl w-full max-w-lg max-h-[80vh] overflow-hidden shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center">
              <CheckCircle className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <h2 className="font-semibold text-slate-800">{issue.title}</h2>
              <p className="text-xs text-slate-400">已完成归档</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 内容 */}
        <div className="p-5 overflow-auto max-h-[60vh]">
          <p className="text-sm text-slate-600 mb-5">{issue.description}</p>

          {/* 流程时间线 */}
          <div className="mb-5">
            <h3 className="text-sm font-medium text-slate-700 mb-3 flex items-center gap-2">
              <Clock className="h-4 w-4 text-slate-400" />
              执行流程
            </h3>
            <div className="space-y-3">
              {Object.entries(issue.stages)
                .filter(([, stage]) => stage.status === 'approved')
                .map(([key, stage]) => (
                  <div key={key} className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                      <CheckCircle className="h-3.5 w-3.5 text-green-600" />
                    </div>
                    <div className="flex-1">
                      <div className="text-sm text-slate-700">{key}</div>
                      {stage.startedAt && stage.completedAt && (
                        <div className="text-xs text-slate-400">
                          {new Date(stage.startedAt).toLocaleDateString('zh-CN')} - {new Date(stage.completedAt).toLocaleDateString('zh-CN')}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
            </div>
          </div>

          {/* 总结报告 */}
          <div>
            <h3 className="text-sm font-medium text-slate-700 mb-3 flex items-center gap-2">
              <FileText className="h-4 w-4 text-slate-400" />
              总结报告
            </h3>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
              <div className="text-sm text-slate-600 whitespace-pre-wrap">
                {currentStage.document || '任务已完成，文档已更新。'}
              </div>
            </div>
          </div>
        </div>

        {/* 底部 */}
        <div className="px-5 py-4 border-t border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>创建于 {issue.createdAt.toLocaleDateString('zh-CN')}</span>
            <span>归档于 {issue.archivedAt?.toLocaleDateString('zh-CN') || '-'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function Archive() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIssue, setSelectedIssue] = useState<typeof mockIssues[0] | null>(null);
  const archivedIssues = mockIssues
    .filter((issue) => issue.status === 'archived')
    .sort((a, b) => (b.archivedAt?.getTime() || 0) - (a.archivedAt?.getTime() || 0));

  const filteredIssues = archivedIssues.filter((issue) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      issue.title.toLowerCase().includes(query) ||
      issue.description.toLowerCase().includes(query)
    );
  });

  return (
    <div className="p-6 space-y-5">
      <h1 className="text-2xl font-semibold text-slate-800">归档</h1>

      {/* 搜索框 */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <input
          type="text"
          placeholder="搜索归档任务..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* 结果统计 */}
      <div className="text-sm text-slate-500">{filteredIssues.length} 个归档任务</div>

      {/* 列表 */}
      {filteredIssues.length === 0 ? (
        <div className="text-center py-12 text-slate-400">
          {searchQuery ? '未找到匹配的任务' : '暂无归档的任务'}
        </div>
      ) : (
        <div className="space-y-2">
          {filteredIssues.map((issue) => (
            <div
              key={issue.id}
              onClick={() => setSelectedIssue(issue)}
              className={cn(
                'p-3 bg-white rounded-xl border border-slate-200 cursor-pointer flex items-center gap-3',
                'hover:border-blue-300 hover:shadow-sm transition-all group'
              )}
            >
              <span className="inline-flex items-center px-2 py-0.5 bg-slate-100 text-slate-600 text-xs font-medium rounded-full shrink-0">
                #{issue.id.replace('issue-', '')}
              </span>
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-slate-800 text-sm truncate">{issue.title}</h3>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-400 shrink-0">
                <Clock className="h-3 w-3" />
                {issue.archivedAt?.toLocaleDateString('zh-CN') || issue.createdAt.toLocaleDateString('zh-CN')}
              </div>
              <ArrowRight className="h-4 w-4 text-slate-300 group-hover:text-blue-400 transition-colors shrink-0" />
            </div>
          ))}
        </div>
      )}

      {/* 弹窗 */}
      {selectedIssue && (
        <ArchiveModal issue={selectedIssue} onClose={() => setSelectedIssue(null)} />
      )}
    </div>
  );
}
