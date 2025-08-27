import { ReactNode, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  BarChart3, 
  Package, 
  Database, 
  Upload, 
  Settings, 
  Activity,
  Monitor 
} from 'lucide-react';
import StatusBar from './StatusBar';
import RetroTitle from './RetroTitle';

interface LayoutProps {
  children: ReactNode;
}

const Layout = ({ children }: LayoutProps) => {
  const location = useLocation();
  const [currentTime, setCurrentTime] = useState(new Date());

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
    { path: '/import', icon: Upload, label: 'Import' },
    { path: '/database', icon: Database, label: 'Database' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="flex h-screen bg-dark-bg relative matrix-bg">
      {/* Scanning line effect */}
      <div className="scan-line"></div>
      
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
                    ? 'bg-retro-cyan text-dark-bg shadow-[0_0_20px_rgba(0,255,255,0.6)]' 
                    : 'text-retro-cyan hover:bg-dark-card hover:shadow-[0_0_10px_rgba(0,255,255,0.3)]'
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