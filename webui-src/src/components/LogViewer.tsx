import { useState, useEffect, useRef } from 'react';
import { RefreshCw, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api } from '@/api';

type LogType = 'daemon' | 'startup';

export function LogViewer() {
  const [activeTab, setActiveTab] = useState<LogType>('startup');
  const [logs, setLogs] = useState<Record<LogType, string>>({ daemon: '', startup: '' });
  const [loading, setLoading] = useState(false);
  const logRef = useRef<HTMLPreElement>(null);

  const fetchLogs = async (type: LogType) => {
    setLoading(true);
    try {
      const result = await api.getLogs(type);
      if (result.success && result.data) {
        setLogs(prev => ({ ...prev, [type]: result.data!.content }));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(activeTab);
  }, [activeTab]);

  // Auto-scroll to bottom when logs update
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs[activeTab]]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as LogType)} className="flex-1">
          <TabsList>
            <TabsTrigger value="startup">Startup Log</TabsTrigger>
            <TabsTrigger value="daemon">Daemon Log</TabsTrigger>
          </TabsList>
        </Tabs>
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchLogs(activeTab)}
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          <span className="ml-2">Refresh</span>
        </Button>
      </div>

      <pre
        ref={logRef}
        className="p-4 h-96 overflow-auto bg-slate-900 text-slate-100 text-xs font-mono whitespace-pre-wrap rounded-lg"
      >
        {loading && !logs[activeTab] ? (
          <span className="text-slate-500">Loading...</span>
        ) : logs[activeTab] ? (
          logs[activeTab]
        ) : (
          <span className="text-slate-500">No logs available</span>
        )}
      </pre>
    </div>
  );
}
