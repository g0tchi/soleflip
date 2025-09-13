import { ReactNode, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  BarChart3, 
  Package, 
  Database, 
  Monitor,
  Brain
} from 'lucide-react';

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
    { path: '/pricing-forecast', icon: Brain, label: 'AI Pricing' },
    { path: '/commerce-intelligence', icon: Database, label: 'Commerce Intel' },
  ];

  return (
    <div className="flex h-screen" style={{ backgroundColor: '#16161a' }}>
      {/* Modern Sidebar */}
      <div className="w-64 relative" style={{ backgroundColor: '#242629', borderRight: '1px solid #3a3d42' }}>
        <div className="p-8" style={{ borderBottom: '1px solid #3a3d42' }}>
          <h1 
            className="text-2xl font-bold" 
            style={{ color: '#94a1b2', textAlign: 'center' }}
          >
            SoleFlipper
          </h1>
        </div>
        
        <nav className="mt-4 px-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-4 py-3 mb-2 rounded-lg transition-all duration-200 group ${
                  isActive 
                    ? 'modern-nav-active' 
                    : 'modern-nav-item'
                }`}
              >
                <Icon className="w-5 h-5 mr-3" />
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>
        
        {/* Status Section */}
        <div className="absolute bottom-0 left-0 right-0 p-4">
          <div 
            className="p-3 rounded-lg text-sm"
            style={{ backgroundColor: '#2d3036', color: '#94a1b2' }}
          >
            <div className="flex items-center justify-between mb-2">
              <span>Status</span>
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            </div>
            <div className="text-xs opacity-75">
              {currentTime.toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {children}
      </div>
    </div>
  );
};

export default Layout;