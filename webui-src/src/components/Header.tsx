import { ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface HeaderProps {
  version: string;
}

export function Header({ version }: HeaderProps) {
  return (
    <header className="bg-slate-900 text-white shadow-lg">
      <div className="max-w-4xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Tailscale Logo */}
            <svg className="w-10 h-10" viewBox="0 0 24 24" fill="none">
              <rect width="24" height="24" rx="6" fill="#242424"/>
              <circle cx="6" cy="6" r="2.5" fill="#fff"/>
              <circle cx="12" cy="6" r="2.5" fill="#fff"/>
              <circle cx="18" cy="6" r="2.5" fill="#fff"/>
              <circle cx="6" cy="12" r="2.5" fill="#6B7280"/>
              <circle cx="12" cy="12" r="2.5" fill="#fff"/>
              <circle cx="18" cy="12" r="2.5" fill="#6B7280"/>
              <circle cx="6" cy="18" r="2.5" fill="#6B7280"/>
              <circle cx="12" cy="18" r="2.5" fill="#6B7280"/>
              <circle cx="18" cy="18" r="2.5" fill="#fff"/>
            </svg>
            <div>
              <h1 className="text-xl font-semibold">Tailscale</h1>
              <p className="text-sm text-gray-400">v{version}</p>
            </div>
          </div>
          <Button asChild>
            <a
              href="https://login.tailscale.com/admin"
              target="_blank"
              rel="noopener noreferrer"
            >
              Admin Console
              <ExternalLink className="w-4 h-4" />
            </a>
          </Button>
        </div>
      </div>
    </header>
  );
}
