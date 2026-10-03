import { useState } from 'react';
import { Globe, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { api } from '@/api';
import type { TailscaleStatus } from '@/api';

interface ExitNodeToggleProps {
  status: TailscaleStatus | null;
  onRefresh: () => void;
}

export function ExitNodeToggle({ status, onRefresh }: ExitNodeToggleProps) {
  const [loading, setLoading] = useState(false);

  // Check if this device is advertising as an exit node
  const isExitNode = status?.Self?.ExitNodeOption ?? false;

  const handleToggle = async () => {
    setLoading(true);
    try {
      if (isExitNode) {
        await api.disableExitNode();
      } else {
        await api.enableExitNode();
      }
      setTimeout(onRefresh, 1000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isExitNode ? 'bg-green-100' : 'bg-muted'}`}>
              <Globe className={`w-5 h-5 ${isExitNode ? 'text-green-600' : 'text-muted-foreground'}`} />
            </div>
            <div>
              <h3 className="font-medium">Exit Node</h3>
              <p className="text-sm text-muted-foreground">
                {isExitNode
                  ? 'This device can route traffic for other devices'
                  : 'Allow other devices to use this as an exit node'}
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
                checked={isExitNode}
                onCheckedChange={handleToggle}
                disabled={!status}
              />
            )}
          </div>
        </div>

        {isExitNode && (
          <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-800">
              Exit node is enabled. Other devices on your tailnet can now route their traffic through this device.
              Make sure to approve it in the admin console.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
