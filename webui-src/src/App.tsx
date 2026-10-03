import { useState, useEffect, useCallback } from 'react';
import { api } from '@/api';
import type { TailscaleStatus, ServiceStatus } from '@/api';
import { Sidebar } from '@/components/Sidebar';
import { StatusCard } from '@/components/StatusCard';
import { ExitNodeToggle } from '@/components/ExitNodeToggle';
import { LogViewer } from '@/components/LogViewer';
import { SettingsPanel } from '@/components/SettingsPanel';

function App() {
  const [activeTab, setActiveTab] = useState('status');
  const [tailscaleStatus, setTailscaleStatus] = useState<TailscaleStatus | null>(null);
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus | null>(null);
  const [autostartEnabled, setAutostartEnabled] = useState(false);
  const [version, setVersion] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [statusRes, serviceRes, autostartRes, versionRes] = await Promise.all([
        api.getStatus(),
        api.getServiceStatus(),
        api.getAutostartStatus(),
        api.getVersion(),
      ]);

      if (statusRes.success && statusRes.data) {
        setTailscaleStatus(statusRes.data);
      }
      if (serviceRes.success && serviceRes.data) {
        setServiceStatus(serviceRes.data);
      }
      if (autostartRes.success && autostartRes.data) {
        setAutostartEnabled(autostartRes.data.enabled);
      }
      if (versionRes.success && versionRes.data) {
        setVersion(versionRes.data.version);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const getTitle = () => {
    switch (activeTab) {
      case 'status': return 'Status';
      case 'exitnode': return 'Exit Node';
      case 'logs': return 'Logs';
      case 'settings': return 'Settings';
      default: return '';
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'status':
        return (
          <StatusCard
            tailscaleStatus={tailscaleStatus}
            serviceStatus={serviceStatus}
            loading={loading && !tailscaleStatus}
          />
        );
      case 'exitnode':
        return <ExitNodeToggle status={tailscaleStatus} onRefresh={fetchData} />;
      case 'logs':
        return <LogViewer />;
      case 'settings':
        return (
          <SettingsPanel
            isRunning={serviceStatus?.running ?? false}
            autostartEnabled={autostartEnabled}
            onRefresh={fetchData}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-[#f0f0f0]">
      {/* Sidebar - positioned below TOS header (90px = 40px drag bar + 50px app header) */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} version={version} />

      {/* Main content area */}
      <div className="ml-[220px] mt-[40px] h-[calc(100vh-40px)] flex flex-col bg-[#f0f0f0]">
        {/* Fixed title */}
        <div className="flex-shrink-0 px-6 py-4">
          <h1 className="text-2xl font-bold">{getTitle()}</h1>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-auto px-6 pb-6">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}

export default App;
