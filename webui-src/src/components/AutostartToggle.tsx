import { useState } from 'react';
import { Power, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { api } from '@/api';

interface AutostartToggleProps {
  enabled: boolean;
  onRefresh: () => void;
}

export function AutostartToggle({ enabled, onRefresh }: AutostartToggleProps) {
  const [loading, setLoading] = useState(false);

  const handleToggle = async () => {
    setLoading(true);
    try {
      if (enabled) {
        await api.disableAutostart();
      } else {
        await api.enableAutostart();
      }
      setTimeout(onRefresh, 500);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${enabled ? 'bg-blue-100' : 'bg-muted'}`}>
              <Power className={`w-5 h-5 ${enabled ? 'text-blue-600' : 'text-muted-foreground'}`} />
            </div>
            <div>
              <h3 className="font-medium">Autostart on Boot</h3>
              <p className="text-sm text-muted-foreground">
                {enabled ? 'Tailscale starts automatically' : 'Manual start required after reboot'}
              </p>
            </div>
          </div>

          <div className="relative">
            {loading ? (
              <div className="w-11 h-6 flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <Switch
                checked={enabled}
                onCheckedChange={handleToggle}
              />
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
