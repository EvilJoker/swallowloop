import { ChevronDown, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  return (
    <header className={cn('h-12 border-b border-slate-200 flex items-center px-4 bg-white', className)}>
      <button className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-100 rounded-lg transition-colors group">
        <div className="w-7 h-7 rounded-md bg-blue-500 flex items-center justify-center">
          <Layers className="h-4 w-4 text-white" />
        </div>
        <span className="text-sm font-medium text-slate-700 group-hover:text-slate-900">SwallowLoop</span>
        <ChevronDown className="h-4 w-4 text-slate-400 group-hover:text-slate-600 transition-colors" />
      </button>
    </header>
  );
}
