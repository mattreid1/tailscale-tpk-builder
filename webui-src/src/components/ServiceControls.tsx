import { useState } from 'react';
import { Play, Square, RotateCcw, Trash2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { api } from '@/api';

interface ServiceControlsProps {
  isRunning: boolean;
  onRefresh: () => void;
}

export function ServiceControls({ isRunning, onRefresh }: ServiceControlsProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  const handleAction = async (action: 'start' | 'stop' | 'restart' | 'reset') => {
    setLoading(action);
    try {
      switch (action) {
        case 'start':
          await api.start();
          break;
        case 'stop':
          await api.stop();
          break;
        case 'restart':
          await api.restart();
          break;
        case 'reset':
          await api.reset();
          setShowResetConfirm(false);
          break;
      }
      // Wait a bit for service to change state
      setTimeout(onRefresh, 1500);
    } finally {
      setLoading(null);
    }
  };

  const ButtonIcon = ({ action, icon: Icon }: { action: string; icon: typeof Play }) => {
    if (loading === action) {
      return <Loader2 className="w-4 h-4 animate-spin" />;
    }
    return <Icon className="w-4 h-4" />;
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Service Control</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {!isRunning ? (
              <Button
                onClick={() => handleAction('start')}
                disabled={loading !== null}
                variant="success"
              >
                <ButtonIcon action="start" icon={Play} />
                <span>Start</span>
              </Button>
            ) : (
              <Button
                onClick={() => handleAction('stop')}
                disabled={loading !== null}
                variant="destructive"
              >
                <ButtonIcon action="stop" icon={Square} />
                <span>Stop</span>
              </Button>
            )}

            <Button
              onClick={() => handleAction('restart')}
              disabled={loading !== null || !isRunning}
              variant="default"
            >
              <ButtonIcon action="restart" icon={RotateCcw} />
              <span>Restart</span>
            </Button>

            <Button
              onClick={() => setShowResetConfirm(true)}
              disabled={loading !== null}
              variant="secondary"
            >
              <Trash2 className="w-4 h-4" />
              <span>Reset Config</span>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Reset Confirmation Modal */}
      <Dialog open={showResetConfirm} onOpenChange={setShowResetConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset Configuration?</DialogTitle>
            <DialogDescription>
              This will remove all Tailscale configuration and you'll need to re-authenticate.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowResetConfirm(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => handleAction('reset')}
              disabled={loading !== null}
            >
              {loading === 'reset' && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>Reset</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
