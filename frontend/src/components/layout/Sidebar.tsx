import { Home, LayoutDashboard, Settings, Archive } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SidebarProps {
  currentPage: string;
  onNavigate: (page: 'home' | 'overview' | 'archive' | 'settings') => void;
  className?: string;
}

const menuItems = [
  { icon: Home, label: '首页', key: 'home' as const },
  { icon: LayoutDashboard, label: '概览', key: 'overview' as const },
  { icon: Archive, label: '归档', key: 'archive' as const },
  { icon: Settings, label: '设置', key: 'settings' as const },
];

export function Sidebar({ currentPage, onNavigate, className }: SidebarProps) {
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
          </button>
        ))}
      </nav>
    </aside>
  );
}
