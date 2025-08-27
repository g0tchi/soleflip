import { useState } from 'react';
import { 
  Settings as SettingsIcon, 
  Database, 
  Palette, 
  Bell,
  Shield,
  Save,
  RefreshCw 
} from 'lucide-react';

const Settings = () => {
  const [theme, setTheme] = useState('retro-cyan');
  const [notifications, setNotifications] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(30);
  const [apiEndpoint, setApiEndpoint] = useState('http://localhost:8000');
  const [isSaving, setIsSaving] = useState(false);

  const themes = [
    { value: 'retro-cyan', label: 'Cyan Matrix', color: 'text-retro-cyan' },
    { value: 'retro-green', label: 'Green Terminal', color: 'text-retro-green' },
    { value: 'retro-magenta', label: 'Magenta Neon', color: 'text-retro-magenta' },
    { value: 'retro-yellow', label: 'Amber Classic', color: 'text-retro-yellow' }
  ];

  const handleSave = async () => {
    setIsSaving(true);
    
    // Simulate save operation
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    setIsSaving(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-retro font-bold text-retro-cyan animate-glow">
          SETTINGS
        </h1>
        <p className="text-retro-cyan/70 font-mono mt-1">
          Configure application preferences and system options
        </p>
      </div>

      {/* Appearance */}
      <div className="retro-card">
        <div className="flex items-center space-x-3 mb-6">
          <Palette className="w-6 h-6 text-retro-cyan" />
          <h2 className="text-xl font-retro text-retro-cyan">APPEARANCE</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-mono text-retro-cyan/70 mb-2">
              COLOR THEME
            </label>
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="retro-input w-full"
            >
              {themes.map((themeOption) => (
                <option key={themeOption.value} value={themeOption.value}>
                  {themeOption.label}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-mono text-retro-cyan/70 mb-2">
              PREVIEW
            </label>
            <div className="retro-border p-4 bg-dark-surface">
              <div className="ascii-art text-xs">
                {`╔══════════════════╗
║   THEME PREVIEW  ║  
╚══════════════════╝`}
              </div>
              <div className="mt-2 flex space-x-4 text-sm">
                {themes.map((t) => (
                  <span key={t.value} className={t.color}>●</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* System Configuration */}
      <div className="retro-card">
        <div className="flex items-center space-x-3 mb-6">
          <Database className="w-6 h-6 text-retro-cyan" />
          <h2 className="text-xl font-retro text-retro-cyan">SYSTEM</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-mono text-retro-cyan/70 mb-2">
              API ENDPOINT
            </label>
            <input
              type="url"
              value={apiEndpoint}
              onChange={(e) => setApiEndpoint(e.target.value)}
              className="retro-input w-full"
              placeholder="http://localhost:8000"
            />
          </div>
          
          <div>
            <label className="block text-sm font-mono text-retro-cyan/70 mb-2">
              AUTO REFRESH (SECONDS)
            </label>
            <select
              value={autoRefresh}
              onChange={(e) => setAutoRefresh(Number(e.target.value))}
              className="retro-input w-full"
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
      <div className="retro-card">
        <div className="flex items-center space-x-3 mb-6">
          <Bell className="w-6 h-6 text-retro-cyan" />
          <h2 className="text-xl font-retro text-retro-cyan">NOTIFICATIONS</h2>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="font-mono text-retro-cyan">Desktop Notifications</span>
              <p className="text-sm text-retro-cyan/70 font-mono">
                Show system notifications for imports and alerts
              </p>
            </div>
            <button
              onClick={() => setNotifications(!notifications)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                ${notifications ? 'bg-retro-cyan' : 'bg-dark-border'}
              `}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-dark-bg transition-transform
                  ${notifications ? 'translate-x-6' : 'translate-x-1'}
                `}
              />
            </button>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <span className="font-mono text-retro-cyan">Import Status Updates</span>
              <p className="text-sm text-retro-cyan/70 font-mono">
                Notify when imports complete or fail
              </p>
            </div>
            <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-retro-cyan">
              <span className="inline-block h-4 w-4 transform rounded-full bg-dark-bg translate-x-6" />
            </button>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <span className="font-mono text-retro-cyan">System Alerts</span>
              <p className="text-sm text-retro-cyan/70 font-mono">
                Alert for database or API connection issues
              </p>
            </div>
            <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-retro-cyan">
              <span className="inline-block h-4 w-4 transform rounded-full bg-dark-bg translate-x-6" />
            </button>
          </div>
        </div>
      </div>

      {/* Security */}
      <div className="retro-card">
        <div className="flex items-center space-x-3 mb-6">
          <Shield className="w-6 h-6 text-retro-cyan" />
          <h2 className="text-xl font-retro text-retro-cyan">SECURITY</h2>
        </div>
        
        <div className="space-y-4 font-mono text-sm">
          <div className="flex justify-between">
            <span>Database Access:</span>
            <span className="text-retro-yellow">READ-ONLY</span>
          </div>
          <div className="flex justify-between">
            <span>API Authentication:</span>
            <span className="text-retro-green">ENABLED</span>
          </div>
          <div className="flex justify-between">
            <span>Encryption:</span>
            <span className="text-retro-green">AES-256</span>
          </div>
          <div className="flex justify-between">
            <span>Session Timeout:</span>
            <span className="text-retro-cyan">24 hours</span>
          </div>
        </div>
      </div>

      {/* About */}
      <div className="retro-card">
        <h2 className="text-xl font-retro text-retro-cyan mb-4">SYSTEM INFORMATION</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-mono text-sm">
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Application Version:</span>
              <span className="text-retro-cyan">1.0.0</span>
            </div>
            <div className="flex justify-between">
              <span>Build Date:</span>
              <span className="text-retro-cyan">{new Date().toLocaleDateString()}</span>
            </div>
            <div className="flex justify-between">
              <span>Framework:</span>
              <span className="text-retro-cyan">Tauri + React</span>
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Platform:</span>
              <span className="text-retro-cyan">Desktop</span>
            </div>
            <div className="flex justify-between">
              <span>Environment:</span>
              <span className="text-retro-green">Development</span>
            </div>
            <div className="flex justify-between">
              <span>License:</span>
              <span className="text-retro-cyan">MIT</span>
            </div>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="retro-button-success flex items-center space-x-2"
        >
          {isSaving ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          <span>{isSaving ? 'SAVING...' : 'SAVE SETTINGS'}</span>
        </button>
      </div>
    </div>
  );
};

export default Settings;