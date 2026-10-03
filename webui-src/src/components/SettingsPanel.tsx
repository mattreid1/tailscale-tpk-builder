import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ServiceControls } from '@/components/ServiceControls';
import { AutostartToggle } from '@/components/AutostartToggle';

interface SettingsPanelProps {
  isRunning: boolean;
  autostartEnabled: boolean;
  onRefresh: () => void;
}

export function SettingsPanel({ isRunning, autostartEnabled, onRefresh }: SettingsPanelProps) {
  return (
    <div className="space-y-6">
      <div className="grid gap-6">
        <ServiceControls isRunning={isRunning} onRefresh={onRefresh} />
        <AutostartToggle enabled={autostartEnabled} onRefresh={onRefresh} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>About</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            Tailscale creates a secure network between your devices.
            This app runs the Tailscale daemon on your TerraMaster NAS.
          </p>
          <p>
            <a
              href="https://login.tailscale.com/admin"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              Open Admin Console
            </a>
            {' · '}
            <a
              href="https://tailscale.com/kb"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              Documentation
            </a>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
