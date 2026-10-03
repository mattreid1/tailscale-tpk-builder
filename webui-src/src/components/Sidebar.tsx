import { Home, Globe, FileText, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  version: string;
}

const navItems = [
  { id: 'status', label: 'Status', icon: Home },
  { id: 'exitnode', label: 'Exit Node', icon: Globe },
  { id: 'logs', label: 'Logs', icon: FileText },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ activeTab, onTabChange, version }: SidebarProps) {
  return (
    <aside className="fixed left-0 top-[90px] w-[220px] h-[calc(100vh-90px)] bg-[#f0f0f0] flex flex-col">
      {/* Navigation */}
      <nav className="flex-1 py-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={cn(
                'w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors',
                isActive
                  ? 'bg-[#d7d7d7] text-gray-900 font-medium'
                  : 'text-gray-600 hover:bg-[#e5e5e5]'
              )}
            >
              <Icon className={cn('w-5 h-5', isActive ? 'text-blue-600' : 'text-gray-500')} />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Version */}
      <div className="p-4 text-xs text-gray-500">
        Version: {version || '...'}
      </div>
    </aside>
  );
}
