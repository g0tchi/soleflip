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
    <div className="flex flex-col lg:flex-row min-h-screen modern-typography" style={{ backgroundColor: '#16161a' }}>
      {/* Responsive Sidebar with Enhanced YouTube-style Effects */}
      <div className="w-full lg:w-80 xl:w-96 min-h-auto lg:min-h-screen lg:sticky lg:top-0 frosted-glass-intense" style={{
        backgroundColor: '#242629',
        borderRight: '1px solid #3a3d42'
      }}>
        <div className="p-4 md:p-6" style={{ borderBottom: '1px solid #3a3d42' }}>
          <h1 className="text-lg md:text-xl lg:text-2xl text-center font-bold" style={{ color: '#fffffe' }}>
            SoleFlipper
          </h1>
          <div className="w-12 h-1 rounded-full mx-auto mt-3" style={{
            background: 'linear-gradient(90deg, #7f5af0 0%, #2cb67d 100%)'
          }}></div>
        </div>

        <nav className="p-3 md:p-4">
          <div className="space-y-2">
            {navItems.map((item, index) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center p-3 md:p-4 rounded-2xl transition-all duration-300 group relative overflow-hidden ${
                    isActive
                      ? 'scale-105'
                      : ''
                  }`}
                  style={{
                    backgroundColor: isActive
                      ? 'rgba(127, 90, 240, 0.15)'
                      : 'transparent',
                    borderColor: isActive
                      ? 'rgba(127, 90, 240, 0.3)'
                      : 'transparent',
                    border: '1px solid',
                    animationDelay: `${index * 0.1}s`
                  }}
                >
                  <div className="flex items-center space-x-3 relative z-10">
                    <div
                      className="p-2 rounded-xl transition-all duration-300"
                      style={{
                        backgroundColor: isActive
                          ? 'rgba(127, 90, 240, 0.2)'
                          : 'rgba(114, 117, 126, 0.1)',
                        transform: isActive ? 'scale(1.1)' : 'scale(1)'
                      }}
                    >
                      <Icon
                        className="w-4 h-4 md:w-5 md:h-5 transition-all duration-300"
                        style={{
                          color: isActive ? '#7f5af0' : '#94a1b2'
                        }}
                      />
                    </div>
                    <span
                      className="text-sm md:text-base font-semibold transition-all duration-300 hidden md:block"
                      style={{
                        color: isActive ? '#fffffe' : '#94a1b2'
                      }}
                    >
                      {item.label}
                    </span>
                  </div>
                  {isActive && (
                    <div
                      className="absolute right-0 top-0 bottom-0 w-1 rounded-l-full"
                      style={{
                        background: 'linear-gradient(180deg, #7f5af0 0%, #2cb67d 100%)'
                      }}
                    ></div>
                  )}
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Enhanced Responsive Status Section */}
        <div className="absolute bottom-0 left-0 right-0 p-3 md:p-4">
          <div
            className="frosted-glass p-3 md:p-4"
            style={{
              backgroundColor: '#2e2f33',
              border: '1px solid #3a3d42',
              borderRadius: '16px'
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs uppercase tracking-wider font-medium" style={{ color: '#94a1b2' }}>
                Status
              </span>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: '#2cb67d' }}></div>
                <span className="text-xs" style={{ color: '#2cb67d' }}>Online</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs" style={{ color: '#94a1b2' }}>
                {currentTime.toLocaleTimeString()}
              </span>
              <div
                className="w-1 h-4 rounded-full"
                style={{
                  background: 'linear-gradient(180deg, #7f5af0 0%, #2cb67d 100%)'
                }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* Responsive Main Content with Page Transitions */}
      <div className="flex-1 w-full overflow-y-auto p-4 md:p-6 lg:p-8" style={{ backgroundColor: '#16161a' }}>
        {children}
      </div>
    </div>
  );
};

export default Layout;