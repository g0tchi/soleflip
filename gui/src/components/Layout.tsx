import { ReactNode, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  BarChart3, 
  Package, 
  Database, 
  Upload, 
  Settings, 
  Activity,
  Monitor,
  Brain
} from 'lucide-react';
import StatusBar from './StatusBar';
import RetroTitle from './RetroTitle';
import { useTheme } from '../contexts/ThemeContext';

interface LayoutProps {
  children: ReactNode;
}

const Layout = ({ children }: LayoutProps) => {
  const location = useLocation();
  const [currentTime, setCurrentTime] = useState(new Date());
  const { theme } = useTheme();
  
  const isModernTheme = theme === 'happy-hues-modern';

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const navItems = [
    { path: '/', icon: Monitor, label: 'Dashboard' },
    { path: '/inventory', icon: Package, label: 'Inventory' },
    { path: '/analytics', icon: BarChart3, label: 'Analytics' },
    { path: '/pricing-forecast', icon: Brain, label: 'AI Pricing' },
    { path: '/import', icon: Upload, label: 'Import' },
    { path: '/database', icon: Database, label: 'Database' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  if (isModernTheme) {
    return (
      <div className="flex h-screen" style={{ backgroundColor: '#16161a' }}>
        {/* Modern Sidebar */}
        <div className="w-64 relative" style={{ backgroundColor: '#242629', borderRight: '1px solid #3a3d42' }}>
          <div className="p-8" style={{ borderBottom: '1px solid #3a3d42' }}>
            <h1 
              className="text-2xl font-bold" 
              style={{color: '#fffffe', fontWeight: 700, letterSpacing: '-0.025em'}}
            >
              SoleFlipper
            </h1>
            <p 
              className="text-sm" 
              style={{color: '#94a1b2', fontWeight: 400}}
            >
              AI-powered flipping
            </p>
          </div>
          
          <nav className="mt-8 px-4">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center px-4 py-3 mb-2 text-sm font-medium rounded-xl transition-all duration-200
                    ${isActive 
                      ? 'text-white' 
                      : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                    }`}
                  style={isActive ? { 
                    backgroundColor: '#7f5af0',
                    boxShadow: '0 4px 16px rgba(127, 90, 240, 0.3)' 
                  } : {}}
                >
                  <Icon className="w-5 h-5 mr-3" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          
          {/* Modern System Status */}
          <div className="absolute bottom-0 w-full p-6" style={{ borderTop: '1px solid #3a3d42' }}>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-2 h-2 rounded-full bg-green-400 mr-2"></div>
                <span className="text-sm" style={{color: '#94a1b2'}}>System Online</span>
              </div>
              <span className="text-xs" style={{color: '#94a1b2'}}>
                {currentTime.toLocaleTimeString()}
              </span>
            </div>
          </div>
        </div>
        
        {/* Modern Main Content */}
        <div className="flex-1" style={{ backgroundColor: '#16161a' }}>
          <main 
            className="h-full w-full"
            style={{ 
              backgroundColor: '#16161a',
              minHeight: '100vh',
              overflow: 'visible'
            }}
          >
            {children}
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-dark-bg relative matrix-bg">
      {/* Sidebar */}
      <div className="w-64 bg-dark-surface border-r border-retro-cyan relative">
        <div className="p-6 border-b border-retro-cyan">
          <RetroTitle />
        </div>
        
        <nav className="mt-8">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-6 py-3 text-sm font-mono uppercase tracking-wider transition-all duration-300
                  ${isActive 
                    ? 'bg-retro-cyan text-dark-bg' 
                    : 'text-retro-cyan hover:bg-dark-card'
                  }`}
              >
                <Icon className="w-5 h-5 mr-3" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        
        {/* System Status */}
        <div className="absolute bottom-0 w-full p-4 border-t border-retro-cyan">
          <div className="text-xs font-mono">
            <div className="flex justify-between items-center mb-2">
              <span className="text-retro-cyan/70">SYSTEM</span>
              <div className="flex items-center">
                <Activity className="w-3 h-3 mr-1 text-retro-green animate-pulse" />
                <span className="status-healthy">ONLINE</span>
              </div>
            </div>
            <div className="text-retro-cyan/50 text-[10px]">
              {currentTime.toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <StatusBar />
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;