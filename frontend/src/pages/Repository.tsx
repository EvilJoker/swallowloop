import { useState, useEffect } from 'react';
import { repositoryApi, type Repository } from '@/lib/api';
import { GitBranch, Database, Globe, Copy, Check } from 'lucide-react';

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

export function Repository() {
  const [repository, setRepository] = useState<Repository | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRepository = async () => {
      try {
        const data = await repositoryApi.getRepository();
        setRepository(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取仓库信息失败');
      } finally {
        setLoading(false);
      }
    };

    fetchRepository();
  }, []);

  if (loading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-slate-800 mb-5">📦 代码仓库</h1>
        <div className="animate-pulse h-32 bg-slate-200 rounded-xl"></div>
      </div>
    );
  }

  if (error || !repository) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-slate-800 mb-5">📦 代码仓库</h1>
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
          {error || '无法获取仓库信息'}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-semibold text-slate-800 mb-5">📦 代码仓库</h1>

      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center">
            <Database className="h-6 w-6 text-emerald-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-slate-400" />
              <span className="text-lg font-semibold text-slate-800">{repository.name || '-'}</span>
            </div>
            {repository.description && (
              <div className="text-sm text-slate-400 mt-0.5">{repository.description}</div>
            )}
          </div>
        </div>

        <div className="space-y-3 pl-15">
          <div className="flex items-center gap-3">
            <GitBranch className="h-4 w-4 text-slate-400" />
            <span className="text-sm text-slate-500">分支：</span>
            <span className="text-sm font-medium text-slate-700">{repository.branch || 'main'}</span>
          </div>
          <div className="flex items-center gap-3">
            <Globe className="h-4 w-4 text-slate-400" />
            <span className="text-sm text-slate-500">地址：</span>
            <a
              href={repository.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-500 hover:text-blue-600 font-mono text-sm underline"
            >
              {repository.url}
            </a>
            <CopyButton text={repository.url} />
          </div>
        </div>
      </div>
    </div>
  );
}
