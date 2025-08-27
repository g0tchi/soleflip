import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { Wifi, WifiOff, Database, AlertTriangle, CheckCircle } from 'lucide-react';

interface SystemStatus {
  api_connected: boolean;
  database_healthy: boolean;
  last_check: string;
  version: string;
  environment: string;
}

const StatusBar = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchSystemStatus = async () => {
    try {
      const status = await invoke<SystemStatus>('get_system_status');
      setSystemStatus(status);
    } catch (error) {
      console.error('Failed to fetch system status:', error);
      setSystemStatus({
        api_connected: false,
        database_healthy: false,
        last_check: new Date().toISOString(),
        version: 'unknown',
        environment: 'unknown'
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return (
      <div className="bg-dark-surface border-b border-retro-cyan px-6 py-2">
        <div className="flex justify-between items-center">
          <div className="text-retro-cyan animate-pulse">Loading system status...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-dark-surface border-b border-retro-cyan px-6 py-2">
      <div className="flex justify-between items-center text-sm font-mono">
        <div className="flex items-center space-x-6">
          {/* API Status */}
          <div className="flex items-center space-x-2">
            {systemStatus?.api_connected ? (
              <Wifi className="w-4 h-4 text-retro-green" />
            ) : (
              <WifiOff className="w-4 h-4 text-retro-magenta" />
            )}
            <span className={systemStatus?.api_connected ? 'status-healthy' : 'status-error'}>
              API {systemStatus?.api_connected ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>

          {/* Database Status */}
          <div className="flex items-center space-x-2">
            <Database className={`w-4 h-4 ${systemStatus?.database_healthy ? 'text-retro-green' : 'text-retro-magenta'}`} />
            <span className={systemStatus?.database_healthy ? 'status-healthy' : 'status-error'}>
              DB {systemStatus?.database_healthy ? 'HEALTHY' : 'ERROR'}
            </span>
          </div>

          {/* Environment */}
          <div className="flex items-center space-x-2">
            {systemStatus?.environment === 'production' ? (
              <AlertTriangle className="w-4 h-4 text-retro-yellow" />
            ) : (
              <CheckCircle className="w-4 h-4 text-retro-green" />
            )}
            <span className={systemStatus?.environment === 'production' ? 'status-warning' : 'status-healthy'}>
              ENV: {systemStatus?.environment?.toUpperCase()}
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-4 text-retro-cyan/70">
          <span>v{systemStatus?.version}</span>
          <span>
            Last Check: {systemStatus?.last_check 
              ? new Date(systemStatus.last_check).toLocaleTimeString()
              : 'Never'
            }
          </span>
        </div>
      </div>
    </div>
  );
};

export default StatusBar;