import { STAGES } from '@/types';
import { mockIssues } from '@/types/mock';
import { Clock, CheckCircle, PlayCircle } from 'lucide-react';

interface StageStat {
  issueCount: number;
  executionCount: number;
  totalDuration: number;
  completedCount: number;
}

// 指标卡片数据
function MetricCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: string | number; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl ${color} flex items-center justify-center`}>
        <Icon className="h-6 w-6 text-white" />
      </div>
      <div>
        <div className="text-2xl font-semibold text-slate-800">{value}</div>
        <div className="text-sm text-slate-500">{label}</div>
      </div>
    </div>
  );
}

// 最近执行的任务
function RecentExecution() {
  const activeIssues = mockIssues.filter((i) => i.status === 'active');
  const runningIssues = activeIssues.filter((i) =>
    Object.values(i.stages).some((s) => s.executionState === 'running' || s.status === 'running')
  );

  // 按开始时间排序，取最近5个
  const recentIssues = [...runningIssues, ...activeIssues.filter(i => !runningIssues.includes(i))]
    .slice(0, 5);

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100">
        <h2 className="text-base font-medium text-slate-800">最近执行</h2>
      </div>
      <div className="divide-y divide-slate-100">
        {recentIssues.map((issue) => {
          const currentStage = issue.stages[issue.currentStage];
          const isRunning = currentStage.executionState === 'running' || currentStage.status === 'running';
          return (
            <div key={issue.id} className="px-5 py-3 flex items-center gap-3 hover:bg-slate-50">
              <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-blue-500 animate-pulse' : 'bg-slate-300'}`} />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-800 truncate">{issue.title}</div>
                <div className="text-xs text-slate-400">{issue.currentStage}</div>
              </div>
              {currentStage.startedAt && (
                <div className="text-xs text-slate-400">
                  {new Date(currentStage.startedAt).toLocaleDateString('zh-CN')}
                </div>
              )}
            </div>
          );
        })}
        {recentIssues.length === 0 && (
          <div className="px-5 py-8 text-center text-sm text-slate-400">暂无执行中的任务</div>
        )}
      </div>
    </div>
  );
}

// 阶段详细统计表格
function StageStatsTable() {
  const activeIssues = mockIssues.filter((i) => i.status === 'active');

  // 计算各阶段统计
  const stats = STAGES.reduce<Record<string, StageStat>>((acc, stage) => {
    acc[stage.key] = { issueCount: 0, executionCount: 0, totalDuration: 0, completedCount: 0 };
    return acc;
  }, {});

  // 遍历 active Issue 统计
  activeIssues.forEach((issue) => {
    Object.entries(issue.stages).forEach(([stageKey, stageState]: [string, any]) => {
      if (stats[stageKey]) {
        // 统计 Issue 数量（只在 currentStage 时计一次）
        if (issue.currentStage === stageKey) {
          stats[stageKey].issueCount++;
        }

        // 统计执行次数（每个阶段被处理过就算一次）
        stats[stageKey].executionCount++;

        // 统计耗时（只计算已完成的）
        if (stageState.completedAt && stageState.startedAt) {
          const duration = (new Date(stageState.completedAt).getTime() - new Date(stageState.startedAt).getTime()) / (1000 * 60);
          stats[stageKey].totalDuration += duration;
          stats[stageKey].completedCount++;
        }
      }
    });
  });

  // 计算平均值
  const getAverageDuration = (stat: StageStat) => {
    if (stat.completedCount === 0) return '-';
    return Math.round(stat.totalDuration / stat.completedCount) + ' 分钟';
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100">
        <h2 className="text-base font-medium text-slate-800">各阶段统计</h2>
      </div>
      <table className="w-full">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            <th className="text-left px-5 py-3 text-sm font-medium text-slate-600">阶段</th>
            <th className="text-center px-4 py-3 text-sm font-medium text-slate-600">Issue 数量</th>
            <th className="text-center px-4 py-3 text-sm font-medium text-slate-600">执行次数</th>
            <th className="text-center px-4 py-3 text-sm font-medium text-slate-600">平均耗时</th>
          </tr>
        </thead>
        <tbody>
          {STAGES.map((stage) => {
            const stat = stats[stage.key];
            return (
              <tr key={stage.key} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-5 py-3 text-sm text-slate-800">{stage.label}</td>
                <td className="px-4 py-3 text-sm text-slate-600 text-center">{stat.issueCount}</td>
                <td className="px-4 py-3 text-sm text-slate-600 text-center">{stat.executionCount}</td>
                <td className="px-4 py-3 text-sm text-slate-600 text-center">{getAverageDuration(stat)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function Overview() {
  const activeIssues = mockIssues.filter((i) => i.status === 'active');
  const totalIssues = mockIssues.length;
  const runningCount = activeIssues.filter((i) =>
    Object.values(i.stages).some((s) => s.executionState === 'running' || s.status === 'running')
  ).length;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold text-slate-800">概览</h1>

      {/* 指标卡片 */}
      <div className="grid grid-cols-3 gap-4">
        <MetricCard icon={CheckCircle} label="活跃 Issue" value={activeIssues.length} color="bg-blue-500" />
        <MetricCard icon={PlayCircle} label="执行中" value={runningCount} color="bg-amber-500" />
        <MetricCard icon={Clock} label="总 Issue" value={totalIssues} color="bg-slate-500" />
      </div>

      {/* 阶段统计 */}
      <StageStatsTable />

      {/* 最近执行 */}
      <RecentExecution />
    </div>
  );
}
