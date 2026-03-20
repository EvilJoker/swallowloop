import { useState } from 'react';
import { Github, Database, Bell, Check, Cpu, Plus, Trash2, Radio } from 'lucide-react';
import { cn } from '@/lib/utils';

type TabKey = 'project' | 'ai' | 'pipeline' | 'notify';

function Toggle({ label, description, defaultChecked = false }: { label: string; description?: string; defaultChecked?: boolean }) {
  const [checked, setChecked] = useState(defaultChecked);

  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-100 last:border-0">
      <div>
        <div className="text-sm font-medium text-slate-700">{label}</div>
        {description && <div className="text-xs text-slate-400 mt-0.5">{description}</div>}
      </div>
      <button
        onClick={() => setChecked(!checked)}
        className={`relative w-11 h-6 rounded-full transition-colors ${
          checked ? 'bg-blue-500' : 'bg-slate-200'
        }`}
      >
        <span
          className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${
            checked ? 'left-6' : 'left-1'
          }`}
        />
      </button>
    </div>
  );
}

interface LLMConfig {
  id: string;
  name: string;
  provider: 'openai' | 'anthropic' | 'ollama';
  baseUrl: string;
  apiKey: string;
  model: string;
}

const defaultLLMs: LLMConfig[] = [
  { id: '1', name: 'GPT-4', provider: 'openai', baseUrl: 'https://api.openai.com/v1', apiKey: 'sk-***', model: 'gpt-4' },
  { id: '2', name: 'Claude', provider: 'anthropic', baseUrl: 'https://api.anthropic.com', apiKey: 'sk-***', model: 'claude-3-opus' },
];

function ProjectSettings() {
  return (
    <div className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-slate-600 mb-1.5">项目名称</label>
        <input
          type="text"
          defaultValue="SwallowLoop"
          className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-600 mb-1.5">GitHub 仓库</label>
        <input
          type="text"
          defaultValue="https://github.com/example/repo"
          className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
    </div>
  );
}

function AISettings() {
  const [llms, setLlms] = useState<LLMConfig[]>(defaultLLMs);
  const [activeLlmId, setActiveLlmId] = useState('1');

  const addLlm = () => {
    const newLlm: LLMConfig = {
      id: Date.now().toString(),
      name: '新配置',
      provider: 'openai',
      baseUrl: 'https://api.openai.com/v1',
      apiKey: '',
      model: '',
    };
    setLlms([...llms, newLlm]);
  };

  const removeLlm = (id: string) => {
    if (llms.length <= 1) return;
    const newLlms = llms.filter((llm) => llm.id !== id);
    setLlms(newLlms);
    if (activeLlmId === id) {
      setActiveLlmId(newLlms[0].id);
    }
  };

  const updateLlm = (id: string, field: keyof LLMConfig, value: string) => {
    setLlms(llms.map((llm) => (llm.id === id ? { ...llm, [field]: value } : llm)));
  };

  return (
    <div className="space-y-4">
      {llms.map((llm) => (
        <div
          key={llm.id}
          className={cn(
            'p-4 rounded-xl border-2 transition-colors',
            activeLlmId === llm.id ? 'border-blue-400 bg-blue-50/50' : 'border-slate-200 bg-slate-50'
          )}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveLlmId(llm.id)}
                className={cn(
                  'w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors',
                  activeLlmId === llm.id ? 'border-blue-500 bg-blue-500' : 'border-slate-300'
                )}
              >
                {activeLlmId === llm.id && <Radio className="h-3 w-3 text-white" />}
              </button>
              <input
                type="text"
                value={llm.name}
                onChange={(e) => updateLlm(llm.id, 'name', e.target.value)}
                className="text-sm font-medium text-slate-800 bg-transparent border-none outline-none"
              />
            </div>
            <div className="flex items-center gap-2">
              <select
                value={llm.provider}
                onChange={(e) => updateLlm(llm.id, 'provider', e.target.value)}
                className="text-xs px-2 py-1 bg-white border border-slate-200 rounded-md text-slate-600"
              >
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="ollama">Ollama</option>
              </select>
              <button
                onClick={() => removeLlm(llm.id)}
                className="p-1 text-slate-400 hover:text-red-500 transition-colors"
                disabled={llms.length <= 1}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-500 mb-1">API URL</label>
              <input
                type="text"
                value={llm.baseUrl}
                onChange={(e) => updateLlm(llm.id, 'baseUrl', e.target.value)}
                className="w-full px-2.5 py-2 bg-white border border-slate-200 rounded-lg text-xs text-slate-800"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">API Key</label>
              <input
                type="password"
                value={llm.apiKey}
                onChange={(e) => updateLlm(llm.id, 'apiKey', e.target.value)}
                className="w-full px-2.5 py-2 bg-white border border-slate-200 rounded-lg text-xs text-slate-800"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-slate-500 mb-1">模型</label>
              <input
                type="text"
                value={llm.model}
                onChange={(e) => updateLlm(llm.id, 'model', e.target.value)}
                placeholder="如: gpt-4, claude-3-opus"
                className="w-full px-2.5 py-2 bg-white border border-slate-200 rounded-lg text-xs text-slate-800"
              />
            </div>
          </div>
        </div>
      ))}
      <button
        onClick={addLlm}
        className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-sm text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
      >
        <Plus className="h-4 w-4" />
        添加 LLM 配置
      </button>
    </div>
  );
}

function PipelineSettings() {
  return (
    <div>
      <Toggle
        label="新 Issue 自动开始流水线"
        description="创建 Issue 时自动进入头脑风暴阶段"
        defaultChecked={true}
      />
      <Toggle
        label="废弃 Issue 3 天后自动删除"
        description="清理不再需要的任务"
        defaultChecked={true}
      />
      <Toggle
        label="执行失败自动重试"
        description="任务失败时自动重试最多 3 次"
        defaultChecked={false}
      />
    </div>
  );
}

function NotifySettings() {
  return (
    <div>
      <Toggle
        label="阶段变更通知"
        description="任务进入新阶段时发送通知"
        defaultChecked={true}
      />
      <Toggle
        label="执行完成通知"
        description="任务执行完成或失败时发送通知"
        defaultChecked={true}
      />
      <Toggle
        label="每日汇总"
        description="每天发送任务状态汇总"
        defaultChecked={false}
      />
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
        {activeTab === 'project' && <ProjectSettings />}
        {activeTab === 'ai' && <AISettings />}
        {activeTab === 'pipeline' && <PipelineSettings />}
        {activeTab === 'notify' && <NotifySettings />}
      </div>

      {/* 保存按钮 */}
      <div className="flex gap-3 mt-5">
        <button className="px-5 py-2.5 bg-blue-500 text-white hover:bg-blue-600 rounded-lg transition-colors text-sm font-medium flex items-center gap-2">
          <Check className="h-4 w-4" />
          保存设置
        </button>
        <button className="px-5 py-2.5 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors text-sm font-medium">
          重置
        </button>
      </div>
    </div>
  );
}
