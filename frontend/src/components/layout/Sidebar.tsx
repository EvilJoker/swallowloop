import { useState, useEffect } from 'react';
import { Home, LayoutDashboard, Archive, Bot } from 'lucide-react';
import { cn } from '@/lib/utils';
import { deerflowApi, type DeerFlowStatus } from '@/lib/api';

interface SidebarProps {
  currentPage: string;
  onNavigate: (page: 'home' | 'overview' | 'archive' | 'deerflow') => void;
  className?: string;
}

const menuItems = [
  { icon: Home, label: '首页', key: 'home' as const },
  { icon: LayoutDashboard, label: '概览', key: 'overview' as const },
  { icon: Archive, label: '归档', key: 'archive' as const },
  { icon: Bot, label: 'DeerFlow', key: 'deerflow' as const, showStatus: true },
];

export function Sidebar({ currentPage, onNavigate, className }: SidebarProps) {
  const [deerflowStatus, setDeerflowStatus] = useState<DeerFlowStatus | null>(null);

  useEffect(() => {
    let lastFetch = 0;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    const fetchStatus = async () => {
      const now = Date.now();
      if (now - lastFetch >= 30000) {
        lastFetch = now;
        try {
          const data = await deerflowApi.getStatus();
          setDeerflowStatus(data);
        } catch {
          setDeerflowStatus(null);
        }
      }
    };

    // 立即获取，然后每 30 秒轮询
    fetchStatus();
    intervalId = setInterval(fetchStatus, 30000);

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, []);

  return (
    <aside className={cn('w-44 bg-slate-50 border-r border-slate-200 p-3', className)}>
      <nav className="space-y-0.5">
        {menuItems.map((item) => (
          <button
            key={item.key}
            onClick={() => onNavigate(item.key)}
            className={cn(
              'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all',
              currentPage === item.key
                ? 'bg-blue-50 text-blue-600 shadow-sm'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            )}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
            {item.showStatus && (
              <span
                className={cn(
                  'ml-auto w-2 h-2 rounded-full',
                  deerflowStatus?.status === 'online' ? 'bg-green-500' : 'bg-red-500'
                )}
              />
            )}
          </button>
        ))}
      </nav>
    </aside>
  );
}
