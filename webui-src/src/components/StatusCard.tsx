import { CheckCircle, XCircle, AlertCircle, Wifi, Globe, Server } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import type { TailscaleStatus, ServiceStatus } from '../api';

interface StatusCardProps {
  tailscaleStatus: TailscaleStatus | null;
  serviceStatus: ServiceStatus | null;
  loading: boolean;
}

export function StatusCard({ tailscaleStatus, serviceStatus, loading }: StatusCardProps) {
  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-muted rounded w-1/4"></div>
            <div className="h-8 bg-muted rounded w-1/2"></div>
            <div className="h-4 bg-muted rounded w-3/4"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const isRunning = serviceStatus?.running ?? false;
  const isConnected = tailscaleStatus?.BackendState === 'Running';
  const needsAuth = tailscaleStatus?.BackendState === 'NeedsLogin' || !!tailscaleStatus?.AuthURL;

  const getConnectionStatus = () => {
    if (!isRunning) return { color: 'text-muted-foreground', bg: 'bg-muted', text: 'Stopped', icon: XCircle };
    if (needsAuth) return { color: 'text-yellow-600', bg: 'bg-yellow-50', text: 'Needs Authentication', icon: AlertCircle };
    if (isConnected) return { color: 'text-green-600', bg: 'bg-green-50', text: 'Connected', icon: CheckCircle };
    return { color: 'text-destructive', bg: 'bg-red-50', text: 'Disconnected', icon: XCircle };
  };

  const status = getConnectionStatus();
  const StatusIcon = status.icon;

  return (
    <Card>
      {/* Status Banner */}
      <div className={`${status.bg} px-6 py-4 border-b`}>
        <div className="flex items-center gap-3">
          <StatusIcon className={`w-6 h-6 ${status.color}`} />
          <span className={`text-lg font-medium ${status.color}`}>{status.text}</span>
        </div>
      </div>

      {/* Details */}
      <CardContent className="p-6 space-y-4">
        {/* Auth URL if needed */}
        {needsAuth && tailscaleStatus?.AuthURL && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-800 mb-2">
              Visit this URL to authenticate your device:
            </p>
            <a
              href={tailscaleStatus.AuthURL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline break-all text-sm font-mono"
            >
              {tailscaleStatus.AuthURL}
            </a>
          </div>
        )}

        {/* Device Info */}
        {tailscaleStatus?.Self && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex items-start gap-3">
              <Server className="w-5 h-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-sm text-muted-foreground">Hostname</p>
                <p className="font-medium">{tailscaleStatus.Self.HostName}</p>
              </div>
            </div>

            {tailscaleStatus.Self.TailscaleIPs?.[0] && (
              <div className="flex items-start gap-3">
                <Wifi className="w-5 h-5 text-muted-foreground mt-0.5" />
                <div>
                  <p className="text-sm text-muted-foreground">Tailscale IP</p>
                  <p className="font-medium font-mono">{tailscaleStatus.Self.TailscaleIPs[0]}</p>
                </div>
              </div>
            )}

            {tailscaleStatus.Self.DNSName && (
              <div className="flex items-start gap-3 sm:col-span-2">
                <Globe className="w-5 h-5 text-muted-foreground mt-0.5" />
                <div>
                  <p className="text-sm text-muted-foreground">DNS Name</p>
                  <p className="font-medium font-mono text-sm">{tailscaleStatus.Self.DNSName}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Service Status */}
        {serviceStatus && (
          <div className="pt-4 border-t">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Service</span>
              <span className={isRunning ? 'text-green-600' : 'text-muted-foreground'}>
                {isRunning ? `Running (PID ${serviceStatus.pid})` : 'Stopped'}
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
