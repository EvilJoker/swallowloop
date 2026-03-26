import { ChevronDown, Layers, Wifi, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useIssueStore } from '@/store/issueStore';

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  const backendConnected = useIssueStore((state) => state.backendConnected);

  return (
    <header className={cn('h-12 border-b border-slate-200 flex items-center px-4 bg-white', className)}>
      <button className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-100 rounded-lg transition-colors group">
        <div className="w-7 h-7 rounded-md bg-blue-500 flex items-center justify-center">
          <Layers className="h-4 w-4 text-white" />
        </div>
        <span className="text-sm font-medium text-slate-700 group-hover:text-slate-900">SwallowLoop</span>
        <ChevronDown className="h-4 w-4 text-slate-400 group-hover:text-slate-600 transition-colors" />
      </button>

      {/* 后端状态指示器 */}
      <div className="ml-auto flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-50">
        {backendConnected ? (
          <>
            <Wifi className="h-4 w-4 text-green-500" />
            <span className="text-xs text-green-600">后端正常</span>
          </>
        ) : (
          <>
            <WifiOff className="h-4 w-4 text-red-500" />
            <span className="text-xs text-red-600">后端断开</span>
          </>
        )}
      </div>
    </header>
  );
}
