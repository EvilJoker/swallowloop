import { useState, useEffect } from 'react';
import { deerflowApi, type DeerFlowStatus } from '@/lib/api';
import { Activity, Bot, Globe, HardDrive, Copy, Check } from 'lucide-react';

function formatDateTime(isoString: string | null): string {
  if (!isoString) return '-';
  try {
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

function formatNumber(num: number): string {
  return num.toLocaleString('zh-CN');
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1 hover:bg-slate-100 rounded transition-colors"
      title="复制"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-green-500" />
      ) : (
        <Copy className="h-3.5 w-3.5 text-slate-400 hover:text-slate-600" />
      )}
    </button>
  );
}

export function DeerFlow() {
  const [status, setStatus] = useState<DeerFlowStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await deerflowApi.getStatus();
        setStatus(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取状态失败');
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    // 每 30 秒刷新一次
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-slate-800 mb-5">🦌 DeerFlow 状态</h1>
        <div className="animate-pulse space-y-4">
          <div className="h-24 bg-slate-200 rounded-xl"></div>
          <div className="h-24 bg-slate-200 rounded-xl"></div>
          <div className="h-32 bg-slate-200 rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (error || !status) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-slate-800 mb-5">🦌 DeerFlow 状态</h1>
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
          {error || '无法获取 DeerFlow 状态'}
        </div>
      </div>
    );
  }

  const usagePercent = Math.min((status.llm_used / status.llm_quota) * 100, 100);

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-semibold text-slate-800 mb-5">🦌 DeerFlow 状态</h1>

      <div className="space-y-4">
        {/* 状态卡片行 */}
        <div className="grid grid-cols-2 gap-4">
          {/* 服务状态 */}
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="h-4 w-4 text-slate-500" />
              <span className="text-sm font-medium text-slate-600">服务状态</span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  status.status === 'online' ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className={`text-lg font-semibold ${status.status === 'online' ? 'text-green-600' : 'text-red-600'}`}>
                {status.status === 'online' ? '在线' : '离线'}
              </span>
            </div>
            {status.version && (
              <div className="mt-1 text-xs text-slate-400">v{status.version}</div>
            )}
          </div>

          {/* AI 模型 */}
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Bot className="h-4 w-4 text-slate-500" />
              <span className="text-sm font-medium text-slate-600">AI 模型</span>
            </div>
            <div className="text-lg font-semibold text-slate-800">
              {status.model_display_name || status.model_name || '-'}
            </div>
            {status.model_name && status.model_display_name && (
              <div className="mt-1 text-xs text-slate-400">{status.model_name}</div>
            )}
          </div>
        </div>

        {/* MiniMax 套餐使用 */}
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <HardDrive className="h-4 w-4 text-slate-500" />
            <span className="text-sm font-medium text-slate-600">MiniMax 套餐使用</span>
            <span className="text-xs text-slate-400">（每5小时刷新）</span>
          </div>

          <div className="flex items-baseline gap-2 mb-3">
            <span className="text-2xl font-bold text-slate-800">{formatNumber(status.llm_used)}</span>
            <span className="text-slate-400">/</span>
            <span className="text-lg text-slate-500">{formatNumber(status.llm_quota)}</span>
          </div>

          {/* 进度条 */}
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden mb-2">
            <div
              className={`h-full rounded-full transition-all ${
                usagePercent > 90 ? 'bg-red-500' : usagePercent > 70 ? 'bg-amber-500' : 'bg-blue-500'
              }`}
              style={{ width: `${usagePercent}%` }}
            />
          </div>

          <div className="flex justify-between text-xs text-slate-400">
            <span>{usagePercent.toFixed(1)}%</span>
            <span>下次刷新: {formatDateTime(status.llm_next_refresh)}</span>
          </div>
        </div>

        {/* 连接信息 */}
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Globe className="h-4 w-4 text-slate-500" />
            <span className="text-sm font-medium text-slate-600">连接信息</span>
          </div>

          <div className="space-y-2 text-sm">
            <div className="flex justify-between items-center">
              <span className="text-slate-500">URL</span>
              <a
                href={status.base_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 hover:text-blue-600 font-mono text-xs underline"
              >
                {status.base_url}
              </a>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-500">数据目录</span>
              <div className="flex items-center gap-2">
                <span className="text-slate-800 font-mono text-xs">{status.data_dir}</span>
                <CopyButton text={status.data_dir} />
              </div>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">活跃 Thread</span>
              <span className="text-slate-800">{status.active_threads}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
