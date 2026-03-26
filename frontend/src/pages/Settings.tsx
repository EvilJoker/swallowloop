import { useState, useEffect, useCallback } from 'react';
import { Github, Database, Bell, Check, Cpu, Plus, Trash2, Radio, AlertCircle, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { settingsApi, type Settings, type SettingsUpdate } from '@/lib/api';

type TabKey = 'project' | 'ai' | 'pipeline' | 'notify';

function EnvOverrideBadge() {
  return (
    <span className="ml-2 px-1.5 py-0.5 text-xs bg-amber-100 text-amber-700 rounded">
      环境变量
    </span>
  );
}

interface InputFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: 'text' | 'password';
  disabled?: boolean;
  hint?: string;
}

function InputField({ label, value, onChange, placeholder, type = 'text', disabled, hint }: InputFieldProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-600 mb-1.5">
        {label}
        {disabled && <EnvOverrideBadge />}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className={cn(
          'w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800',
          'placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
          disabled && 'bg-slate-100 text-slate-500'
        )}
      />
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

function ProjectSettings({ settings, onChange }: { settings: Settings; onChange: (update: Partial<SettingsUpdate>) => void }) {
  return (
    <div className="space-y-5">
      <InputField
        label="GitHub 仓库"
        value={settings.github_repo}
        onChange={(v) => onChange({ github_repo: v })}
        placeholder="owner/repo"
        disabled={settings.env_overrides.github_repo}
      />
      <InputField
        label="GitHub Token"
        value={settings.github_token}
        onChange={(v) => onChange({ github_token: v })}
        placeholder="ghp_xxx"
        type="password"
        disabled={settings.env_overrides.github_token}
        hint="用于访问 GitHub API 的 Personal Access Token"
      />
      <InputField
        label="Issue 标签"
        value={settings.issue_label}
        onChange={(v) => onChange({ issue_label: v })}
        placeholder="swallow"
        disabled={settings.env_overrides.issue_label}
      />
      <InputField
        label="基础分支"
        value={settings.base_branch}
        onChange={(v) => onChange({ base_branch: v })}
        placeholder="main"
        disabled={settings.env_overrides.base_branch}
      />
    </div>
  );
}

function AISettings({ settings, onChange }: { settings: Settings; onChange: (update: Partial<SettingsUpdate>) => void }) {
  return (
    <div className="space-y-5">
      <InputField
        label="API Base URL"
        value={settings.llm_base_url}
        onChange={(v) => onChange({ llm_base_url: v })}
        placeholder="https://api.openai.com/v1"
        disabled={settings.env_overrides.llm_base_url}
        hint="LLM API 的基础地址"
      />
      <InputField
        label="API Key"
        value={settings.llm_api_key}
        onChange={(v) => onChange({ llm_api_key: v })}
        placeholder="sk-xxx"
        type="password"
        disabled={settings.env_overrides.llm_api_key}
      />
      <InputField
        label="模型名称"
        value={settings.llm_model}
        onChange={(v) => onChange({ llm_model: v })}
        placeholder="gpt-4, claude-3-opus, MiniMax-M2.5-highspeed"
        disabled={settings.env_overrides.llm_model}
      />
      <div>
        <label className="block text-sm font-medium text-slate-600 mb-1.5">
          Agent 类型
          {settings.env_overrides.agent_type && <EnvOverrideBadge />}
        </label>
        <select
          value={settings.agent_type}
          onChange={(e) => onChange({ agent_type: e.target.value })}
          disabled={settings.env_overrides.agent_type}
          className={cn(
            'w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            settings.env_overrides.agent_type && 'bg-slate-100 text-slate-500'
          )}
        >
          <option value="mock">Mock（模拟模式，延迟 5 秒）</option>
          <option value="iflow">iFlow（使用 iFlow CLI）</option>
        </select>
      </div>
    </div>
  );
}

function PipelineSettings({ settings, onChange }: { settings: Settings; onChange: (update: Partial<SettingsUpdate>) => void }) {
  return (
    <div className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-slate-600 mb-1.5">
          最大并发 Worker 数
          {settings.env_overrides.max_workers && <EnvOverrideBadge />}
        </label>
        <input
          type="number"
          value={settings.max_workers}
          onChange={(e) => onChange({ max_workers: parseInt(e.target.value) || 3 })}
          disabled={settings.env_overrides.max_workers}
          min={1}
          max={20}
          className={cn(
            'w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            settings.env_overrides.max_workers && 'bg-slate-100 text-slate-500'
          )}
        />
        <p className="mt-1 text-xs text-slate-400">同时执行的最大任务数，建议 3-5</p>
      </div>
    </div>
  );
}

function NotifySettings() {
  return (
    <div className="py-2">
      <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg mb-4">
        <AlertCircle className="h-5 w-5 text-amber-500" />
        <p className="text-sm text-amber-700">通知功能暂未实现，当前版本不发送通知</p>
      </div>
      <div className="space-y-3 opacity-50">
        <div className="flex items-center justify-between py-3 border-b border-slate-100">
          <div>
            <div className="text-sm font-medium text-slate-700">阶段变更通知</div>
            <div className="text-xs text-slate-400 mt-0.5">任务进入新阶段时发送通知</div>
          </div>
          <div className="w-11 h-6 bg-slate-200 rounded-full"></div>
        </div>
        <div className="flex items-center justify-between py-3 border-b border-slate-100">
          <div>
            <div className="text-sm font-medium text-slate-700">执行完成通知</div>
            <div className="text-xs text-slate-400 mt-0.5">任务执行完成或失败时发送通知</div>
          </div>
          <div className="w-11 h-6 bg-slate-200 rounded-full"></div>
        </div>
        <div className="flex items-center justify-between py-3">
          <div>
            <div className="text-sm font-medium text-slate-700">每日汇总</div>
            <div className="text-xs text-slate-400 mt-0.5">每天发送任务状态汇总</div>
          </div>
          <div className="w-11 h-6 bg-slate-200 rounded-full"></div>
        </div>
      </div>
    </div>
  );
}

const tabs: { key: TabKey; label: string; icon: React.ElementType }[] = [
  { key: 'project', label: '项目', icon: Github },
  { key: 'ai', label: 'AI', icon: Cpu },
  { key: 'pipeline', label: '流水线', icon: Database },
  { key: 'notify', label: '通知', icon: Bell },
];

export function Settings() {
  const [activeTab, setActiveTab] = useState<TabKey>('project');
  const [settings, setSettings] = useState<Settings | null>(null);
  const [pendingUpdate, setPendingUpdate] = useState<Partial<SettingsUpdate>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 加载配置
  useEffect(() => {
    settingsApi.get().then((data) => {
      setSettings(data);
      setLoading(false);
    }).catch(() => {
      setMessage({ type: 'error', text: '加载配置失败' });
      setLoading(false);
    });
  }, []);

  // 合并 pendingUpdate 到 settings
  const mergedSettings = settings ? { ...settings, ...pendingUpdate } : null;

  // 处理配置变更
  const handleChange = useCallback((update: Partial<SettingsUpdate>) => {
    setPendingUpdate((prev) => ({ ...prev, ...update }));
  }, []);

  // 保存设置
  const handleSave = async () => {
    if (!pendingUpdate || Object.keys(pendingUpdate).length === 0) {
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      await settingsApi.update(pendingUpdate);
      setMessage({ type: 'success', text: '设置已保存，重启后端服务后生效' });
      setPendingUpdate({});
      // 重新加载配置
      const data = await settingsApi.get();
      setSettings(data);
    } catch (err) {
      setMessage({ type: 'error', text: '保存失败' });
    } finally {
      setSaving(false);
    }
  };

  // 重置
  const handleReset = () => {
    setPendingUpdate({});
    setMessage(null);
  };

  if (loading) {
    return (
      <div className="p-6 max-w-2xl">
        <h1 className="text-2xl font-semibold text-slate-800 mb-5">设置</h1>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="animate-pulse space-y-4">
            <div className="h-10 bg-slate-200 rounded"></div>
            <div className="h-10 bg-slate-200 rounded"></div>
            <div className="h-10 bg-slate-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!mergedSettings) {
    return (
      <div className="p-6 max-w-2xl">
        <h1 className="text-2xl font-semibold text-slate-800 mb-5">设置</h1>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700">加载配置失败</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-semibold text-slate-800 mb-5">设置</h1>

      {/* Tab 切换 */}
      <div className="flex gap-1 p-1 bg-slate-100 rounded-xl mb-5">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
              activeTab === tab.key
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-slate-600 hover:text-slate-800'
            )}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        {activeTab === 'project' && <ProjectSettings settings={mergedSettings} onChange={handleChange} />}
        {activeTab === 'ai' && <AISettings settings={mergedSettings} onChange={handleChange} />}
        {activeTab === 'pipeline' && <PipelineSettings settings={mergedSettings} onChange={handleChange} />}
        {activeTab === 'notify' && <NotifySettings />}
      </div>

      {/* 消息提示 */}
      {message && (
        <div className={cn(
          'mt-4 p-3 rounded-lg text-sm flex items-center gap-2',
          message.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'
        )}>
          {message.type === 'success' ? <Check className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          {message.text}
        </div>
      )}

      {/* 保存和重启按钮 */}
      <div className="flex gap-3 mt-5">
        <button
          onClick={handleSave}
          disabled={saving || Object.keys(pendingUpdate).length === 0}
          className={cn(
            'px-5 py-2.5 rounded-lg transition-colors text-sm font-medium flex items-center gap-2',
            Object.keys(pendingUpdate).length > 0
              ? 'bg-blue-500 text-white hover:bg-blue-600'
              : 'bg-slate-200 text-slate-400 cursor-not-allowed'
          )}
        >
          <Check className="h-4 w-4" />
          {saving ? '保存中...' : '保存设置'}
        </button>
        <button
          onClick={handleReset}
          disabled={Object.keys(pendingUpdate).length === 0}
          className={cn(
            'px-5 py-2.5 rounded-lg transition-colors text-sm font-medium',
            Object.keys(pendingUpdate).length > 0
              ? 'text-slate-600 hover:bg-slate-100'
              : 'text-slate-300 cursor-not-allowed'
          )}
        >
          重置
        </button>
        <button
          onClick={async () => {
            if (Object.keys(pendingUpdate).length === 0) return;
            setSaving(true);
            try {
              await settingsApi.update(pendingUpdate);
              setPendingUpdate({});
              setMessage({ type: 'success', text: '正在保存并重启...' });
              await settingsApi.restart();
              setMessage({ type: 'success', text: '后端正在重启，请稍候...' });
              // 轮询健康检查
              const checkHealth = async () => {
                const res = await fetch('/health');
                if (res.ok) {
                  setMessage({ type: 'success', text: '后端已恢复' });
                } else {
                  setTimeout(checkHealth, 2000);
                }
              };
              setTimeout(checkHealth, 2000);
            } catch {
              setMessage({ type: 'error', text: '操作失败' });
            } finally {
              setSaving(false);
            }
          }}
          disabled={saving || Object.keys(pendingUpdate).length === 0}
          className={cn(
            'px-5 py-2.5 rounded-lg transition-colors text-sm font-medium flex items-center gap-2',
            Object.keys(pendingUpdate).length > 0
              ? 'bg-orange-500 text-white hover:bg-orange-600'
              : 'bg-slate-200 text-slate-400 cursor-not-allowed'
          )}
        >
          <Radio className="h-4 w-4" />
          保存并重启
        </button>
      </div>

      {/* 环境变量提示 */}
      <div className="mt-6 p-3 bg-slate-50 border border-slate-200 rounded-lg">
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <Info className="h-4 w-4 text-slate-400" />
          <span>带"环境变量"标记的字段表示已被系统环境变量覆盖，修改不会生效</span>
        </div>
      </div>
    </div>
  );
}
