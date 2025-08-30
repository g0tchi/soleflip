import { useState } from 'react';
import { 
  Database, 
  Palette, 
  Bell,
  Shield,
  Save,
  RefreshCw
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

const ModernSettings = () => {
  const { theme, setTheme } = useTheme();
  const [notifications, setNotifications] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(30);
  const [apiEndpoint, setApiEndpoint] = useState('http://localhost:8000');
  const [isSaving, setIsSaving] = useState(false);

  const themes = [
    { value: 'happy-hues-modern', label: 'Happy Hues Modern', color: '#7f5af0', preview: '◉◉◉' },
    { value: 'retro-cyan', label: 'Cyan Matrix', color: '#00ffff', preview: '●●●' },
    { value: 'retro-green', label: 'Green Terminal', color: '#00ff00', preview: '●●●' },
    { value: 'retro-magenta', label: 'Magenta Neon', color: '#ff00ff', preview: '●●●' },
    { value: 'retro-yellow', label: 'Amber Classic', color: '#ffff00', preview: '●●●' },
    { value: 'claude-code', label: 'Claude Code', color: '#f97316', preview: '◉◉◉' },
    { value: 'purple-haze', label: 'Purple Haze', color: '#7f5af0', preview: '◆◆◆' }
  ];

  const handleSave = async () => {
    setIsSaving(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsSaving(false);
  };

  return (
    <div className="min-h-screen p-8 space-y-12">
      {/* Header */}
      <div className="space-y-4">
        <h1 className="text-5xl font-bold modern-heading">
          Settings
        </h1>
        <p className="text-xl modern-subheading max-w-2xl">
          Customize your workspace and configure system preferences to match your workflow.
        </p>
      </div>

      {/* Theme Section */}
      <div className="modern-card">
        <div className="flex items-center space-x-4 mb-8">
          <div className="p-3 rounded-xl bg-purple-500/10">
            <Palette className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold modern-heading">Appearance</h2>
            <p className="modern-subheading">Choose your preferred color theme and visual style</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-4">
            <label className="block text-sm font-medium modern-subheading">
              Color Theme
            </label>
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value as any)}
              className="modern-input w-full"
            >
              {themes.map((themeOption) => (
                <option key={themeOption.value} value={themeOption.value}>
                  {themeOption.label}
                </option>
              ))}
            </select>
          </div>
          
          <div className="space-y-4">
            <label className="block text-sm font-medium modern-subheading">
              Preview
            </label>
            <div className="modern-card p-6 bg-gray-800/50">
              <div className="flex space-x-3 mb-4">
                {themes.map((t) => (
                  <button
                    key={t.value}
                    className={`w-8 h-8 rounded-full transition-all duration-200 hover:scale-110 ${
                      theme === t.value ? 'ring-2 ring-white ring-offset-2 ring-offset-gray-800' : ''
                    }`}
                    style={{ backgroundColor: t.color }}
                    onClick={() => setTheme(t.value as any)}
                    title={t.label}
                  />
                ))}
              </div>
              <p className="text-sm modern-subheading">Click any color to preview the theme</p>
            </div>
          </div>
        </div>
      </div>

      {/* System Configuration */}
      <div className="modern-card">
        <div className="flex items-center space-x-4 mb-8">
          <div className="p-3 rounded-xl bg-blue-500/10">
            <Database className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold modern-heading">System</h2>
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
          <div className="p-3 rounded-xl bg-green-500/10">
            <Bell className="w-6 h-6 text-green-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold modern-heading">Notifications</h2>
            <p className="modern-subheading">Manage how you receive updates and alerts</p>
          </div>
        </div>
        
        <div className="space-y-6">
          <div className="flex items-center justify-between p-4 rounded-xl bg-gray-800/30">
            <div>
              <div className="font-medium modern-heading">Desktop Notifications</div>
              <p className="text-sm modern-subheading">
                Receive system notifications for imports and alerts
              </p>
            </div>
            <button
              onClick={() => setNotifications(!notifications)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors
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
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex justify-between items-center p-4 rounded-xl bg-gray-800/30">
              <span className="modern-subheading">Database Access</span>
              <span className="px-3 py-1 rounded-full bg-yellow-500/20 text-yellow-400 text-sm font-medium">
                READ-ONLY
              </span>
            </div>
            <div className="flex justify-between items-center p-4 rounded-xl bg-gray-800/30">
              <span className="modern-subheading">API Authentication</span>
              <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-sm font-medium">
                ENABLED
              </span>
            </div>
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-4 rounded-xl bg-gray-800/30">
              <span className="modern-subheading">Encryption</span>
              <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-sm font-medium">
                AES-256
              </span>
            </div>
            <div className="flex justify-between items-center p-4 rounded-xl bg-gray-800/30">
              <span className="modern-subheading">Session Timeout</span>
              <span className="px-3 py-1 rounded-full bg-blue-500/20 text-blue-400 text-sm font-medium">
                24 hours
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* System Information */}
      <div className="modern-card">
        <div className="mb-8">
          <h2 className="text-2xl font-bold modern-heading mb-2">System Information</h2>
          <p className="modern-subheading">Application details and build information</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="modern-subheading">Version</span>
              <span className="modern-heading">1.0.0</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="modern-subheading">Framework</span>
              <span className="modern-heading">Tauri + React</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="modern-subheading">Platform</span>
              <span className="modern-heading">Desktop</span>
            </div>
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="modern-subheading">Build Date</span>
              <span className="modern-heading">{new Date().toLocaleDateString()}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="modern-subheading">Environment</span>
              <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-sm font-medium">
                Development
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="modern-subheading">License</span>
              <span className="modern-heading">MIT</span>
            </div>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className={`modern-button flex items-center space-x-3 ${isSaving ? 'opacity-70 cursor-not-allowed' : ''}`}
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