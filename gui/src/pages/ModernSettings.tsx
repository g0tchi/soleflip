import { useState, useEffect } from 'react';
import { 
  Bell,
  Shield,
  Save,
  RefreshCw,
  Server,
  Activity,
  Monitor
} from 'lucide-react';
import { invoke } from '@tauri-apps/api/tauri';

interface SystemStatus {
  database_access: 'READ-ONLY' | 'READ-WRITE';
  api_auth_enabled: boolean;
  encryption_level: string;
  session_timeout: string;
}

const ModernSettings = () => {
  const [notifications, setNotifications] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(30);
  const [apiEndpoint, setApiEndpoint] = useState('http://localhost:8000');
  const [maxConnections, setMaxConnections] = useState(20);
  const [enableLogging, setEnableLogging] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    database_access: 'READ-WRITE',
    api_auth_enabled: true,
    encryption_level: 'AES-256',
    session_timeout: '24 hours'
  });

  const fetchSystemStatus = async () => {
    try {
      const response = await invoke<SystemStatus>('get_system_status');
      setSystemStatus(response);
    } catch (error) {
      console.error('Failed to fetch system status:', error);
      // Keep defaults if API fails
    }
  };

  useEffect(() => {
    fetchSystemStatus();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsSaving(false);
  };

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8 space-y-8 lg:space-y-12">
      {/* Header */}
      <div className="space-y-4">
        <h1 className="text-5xl font-bold modern-heading">
          Settings
        </h1>
        <p className="text-xl modern-subheading max-w-2xl">
          Customize your workspace and configure system preferences to match your workflow.
        </p>
      </div>

      {/* Performance */}
      <div className="modern-card">
        <div className="flex items-center space-x-4 mb-8">
          <div className="p-3 rounded-xl bg-blue-500/10">
            <Monitor className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold modern-heading">Performance</h2>
            <p className="modern-subheading">Configure performance and connection settings</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-4">
            <label className="block text-sm font-medium modern-subheading">
              Max Connections
            </label>
            <input
              type="number"
              value={maxConnections}
              onChange={(e) => setMaxConnections(Number(e.target.value))}
              className="modern-input w-full"
              min="1"
              max="100"
            />
          </div>
          
          <div className="space-y-4">
            <label className="block text-sm font-medium modern-subheading">
              Enable Debug Logging
            </label>
            <div className="flex items-center justify-between p-4 rounded-xl bg-gray-800/30">
              <span className="modern-subheading">System debug logs</span>
              <button
                onClick={() => setEnableLogging(!enableLogging)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                  ${enableLogging ? 'bg-purple-500' : 'bg-gray-600'}
                `}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                    ${enableLogging ? 'translate-x-6' : 'translate-x-1'}
                  `}
                />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* API Configuration */}
      <div className="modern-card">
        <div className="flex items-center space-x-4 mb-8">
          <div className="p-3 rounded-xl bg-green-500/10">
            <Server className="w-6 h-6 text-green-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold modern-heading">API Configuration</h2>
            <p className="modern-subheading">Configure API endpoints and refresh intervals</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-4">
            <label className="block text-sm font-medium modern-subheading">
              API Endpoint
            </label>
            <input
              type="url"
              value={apiEndpoint}
              onChange={(e) => setApiEndpoint(e.target.value)}
              className="modern-input w-full"
              placeholder="http://localhost:8000"
            />
          </div>
          
          <div className="space-y-4">
            <label className="block text-sm font-medium modern-subheading">
              Auto Refresh Interval
            </label>
            <select
              value={autoRefresh}
              onChange={(e) => setAutoRefresh(Number(e.target.value))}
              className="modern-input w-full"
            >
              <option value={10}>10 seconds</option>
              <option value={30}>30 seconds</option>
              <option value={60}>1 minute</option>
              <option value={300}>5 minutes</option>
              <option value={0}>Disabled</option>
            </select>
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="modern-card">
        <div className="flex items-center space-x-4 mb-8">
          <div className="p-3 rounded-xl bg-yellow-500/10">
            <Bell className="w-6 h-6 text-yellow-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold modern-heading">Notifications</h2>
            <p className="modern-subheading">Manage how you receive updates and alerts</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 gap-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 rounded-xl bg-gray-800/30 gap-3 sm:gap-0">
            <div>
              <div className="font-medium modern-heading">Desktop Notifications</div>
              <p className="text-sm modern-subheading">
                Receive system notifications for imports and alerts
              </p>
            </div>
            <button
              onClick={() => setNotifications(!notifications)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors self-start sm:self-auto
                ${notifications ? 'bg-purple-500' : 'bg-gray-600'}
              `}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                  ${notifications ? 'translate-x-6' : 'translate-x-1'}
                `}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Security */}
      <div className="modern-card">
        <div className="flex items-center space-x-4 mb-8">
          <div className="p-3 rounded-xl bg-red-500/10">
            <Shield className="w-6 h-6 text-red-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold modern-heading">Security</h2>
            <p className="modern-subheading">System security and access information</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 lg:gap-6">
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center p-4 rounded-xl bg-gray-800/30 gap-2 sm:gap-0">
              <span className="modern-subheading">Database Access</span>
              <span className={`px-3 py-1 rounded-full text-sm font-medium self-start ${
                systemStatus.database_access === 'READ-WRITE' 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'bg-yellow-500/20 text-yellow-400'
              }`}>
                {systemStatus.database_access}
              </span>
            </div>
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center p-4 rounded-xl bg-gray-800/30 gap-2 sm:gap-0">
              <span className="modern-subheading">API Authentication</span>
              <span className={`px-3 py-1 rounded-full text-sm font-medium self-start ${
                systemStatus.api_auth_enabled
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-red-500/20 text-red-400'
              }`}>
                {systemStatus.api_auth_enabled ? 'ENABLED' : 'DISABLED'}
              </span>
            </div>
          </div>
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center p-4 rounded-xl bg-gray-800/30 gap-2 sm:gap-0">
              <span className="modern-subheading">Encryption</span>
              <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-sm font-medium self-start">
                {systemStatus.encryption_level}
              </span>
            </div>
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center p-4 rounded-xl bg-gray-800/30 gap-2 sm:gap-0">
              <span className="modern-subheading">Session Timeout</span>
              <span className="px-3 py-1 rounded-full bg-blue-500/20 text-blue-400 text-sm font-medium self-start">
                {systemStatus.session_timeout}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* System Information */}
      <div className="modern-card">
        <div className="flex items-center space-x-4 mb-8">
          <div className="p-3 rounded-xl bg-purple-500/10">
            <Activity className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold modern-heading">System Information</h2>
            <p className="modern-subheading">Application details and build information</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 lg:gap-6">
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 sm:gap-0">
              <span className="modern-subheading">Version</span>
              <span className="modern-heading text-left sm:text-right">1.0.0</span>
            </div>
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 sm:gap-0">
              <span className="modern-subheading">Framework</span>
              <span className="modern-heading text-left sm:text-right">Tauri + React</span>
            </div>
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 sm:gap-0">
              <span className="modern-subheading">Platform</span>
              <span className="modern-heading text-left sm:text-right">Desktop</span>
            </div>
          </div>
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 sm:gap-0">
              <span className="modern-subheading">Build Date</span>
              <span className="modern-heading text-left sm:text-right">{new Date().toLocaleDateString()}</span>
            </div>
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 sm:gap-0">
              <span className="modern-subheading">Environment</span>
              <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-sm font-medium self-start sm:self-auto">
                Development
              </span>
            </div>
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 sm:gap-0">
              <span className="modern-subheading">License</span>
              <span className="modern-heading text-left sm:text-right">MIT</span>
            </div>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-center sm:justify-end">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className={`modern-button flex items-center space-x-2 w-full sm:w-auto ${isSaving ? 'opacity-70 cursor-not-allowed' : ''}`}
        >
          {isSaving ? (
            <RefreshCw className="w-5 h-5 animate-spin" />
          ) : (
            <Save className="w-5 h-5" />
          )}
          <span>{isSaving ? 'Saving...' : 'Save Settings'}</span>
        </button>
      </div>
    </div>
  );
};

export default ModernSettings;