import { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Package, 
  Banknote, 
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  ShoppingCart,
  PlusCircle,
  RefreshCw
} from 'lucide-react';
import { invoke } from '@tauri-apps/api/tauri';
import { useTheme } from '../contexts/ThemeContext';

interface DashboardMetrics {
  total_inventory_value: number;
  monthly_sales: number;
  profit_margin: number;
  active_listings: number;
  pending_imports: number;
  recent_transactions: any[];
}

const ModernDashboard = () => {
  const { theme } = useTheme();

  // Helper function to format time ago
  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMs = now.getTime() - date.getTime();
    const diffInMinutes = Math.floor(diffInMs / (1000 * 60));
    const diffInHours = Math.floor(diffInMinutes / 60);
    const diffInDays = Math.floor(diffInHours / 24);

    if (diffInMinutes < 60) {
      return `${diffInMinutes} minutes ago`;
    } else if (diffInHours < 24) {
      return `${diffInHours} hours ago`;
    } else if (diffInDays < 7) {
      return `${diffInDays} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    total_inventory_value: 0,
    monthly_sales: 0,
    profit_margin: 0,
    active_listings: 0,
    pending_imports: 0,
    recent_transactions: []
  });
  const [isLoading, setIsLoading] = useState(true);

  // Theme-aware styles
  const isModernTheme = theme === 'happy-hues-modern';
  const containerClasses = isModernTheme 
    ? 'h-full w-full p-8 bg-gray-900 text-gray-200' 
    : 'h-full w-full p-8 bg-dark-bg text-retro-cyan font-mono';
    
  const cardClasses = isModernTheme
    ? 'modern-card'
    : 'retro-card';
    
  const headingClasses = isModernTheme
    ? 'modern-heading'
    : 'text-retro-cyan font-mono';
    
  const subheadingClasses = isModernTheme
    ? 'modern-subheading' 
    : 'text-retro-cyan/70 font-mono';

  const fetchMetrics = async () => {
    try {
      setIsLoading(true);
      const response = await invoke<any>('get_dashboard_metrics');
      setMetrics(response);
    } catch (error) {
      console.error('Failed to fetch dashboard metrics:', error);
      // Keep metrics at zero if API fails - no fake data
      setMetrics({
        total_inventory_value: 0,
        monthly_sales: 0,
        profit_margin: 0,
        active_listings: 0,
        pending_imports: 0,
        recent_transactions: []
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);


  const statCards = [
    {
      title: 'Total Revenue',
      value: `€${metrics.total_inventory_value.toLocaleString()}`,
      change: '+12.3%',
      trend: 'up',
      icon: Banknote,
      color: '#2cb67d'
    },
    {
      title: 'Monthly Sales',
      value: `€${metrics.monthly_sales.toLocaleString()}`,
      change: '+8.2%',
      trend: 'up',
      icon: Package,
      color: '#7f5af0'
    },
    {
      title: "Profit Margin",
      value: `${metrics.profit_margin.toFixed(1)}%`,
      change: '+24.1%',
      trend: 'up',
      icon: ShoppingCart,
      color: '#f2757e'
    },
    {
      title: 'Active Listings',
      value: metrics.active_listings.toLocaleString(),
      change: '-2.4%',
      trend: 'down',
      icon: Activity,
      color: '#ffa500'
    }
  ];

  // Use real recent transactions from backend
  const recentActivity = metrics.recent_transactions.map((transaction: any, index: number) => ({
    id: index + 1,
    type: 'sale',
    item: transaction.product_name || 'Unknown Product',
    brand: transaction.brand_name || 'Unknown Brand',
    amount: transaction.sale_price || 0,
    profit: transaction.net_profit || 0,
    time: transaction.date ? formatTimeAgo(transaction.date) : 'Unknown time'
  }));

  if (isLoading) {
    return (
      <div className={containerClasses}>
        <div className="flex justify-center items-center h-1/2">
          <div className="text-center">
            <RefreshCw className={`w-16 h-16 animate-spin mx-auto mb-4 ${
              isModernTheme ? 'text-purple-500' : 'text-retro-cyan'
            }`} />
            <p className={`${headingClasses} text-xl`}>Loading Dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={containerClasses}>
      {/* Header */}
      <div className="flex justify-end items-start mb-8">
        <button
          onClick={fetchMetrics}
          disabled={isLoading}
          className={`${isModernTheme ? 'modern-button-outline' : 'retro-button'} flex items-center gap-2`}
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((card) => {
          const Icon = card.icon;
          const TrendIcon = card.trend === 'up' ? ArrowUpRight : ArrowDownRight;
          
          return (
            <div key={card.title} className={cardClasses}>
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 rounded-xl" style={{ backgroundColor: `${card.color}20` }}>
                  <Icon className="w-6 h-6" style={{ color: card.color }} />
                </div>
                <div className={`flex items-center gap-1 text-sm font-medium ${
                  card.trend === 'up' ? 'text-green-400' : 'text-red-400'
                }`}>
                  <TrendIcon className="w-4 h-4" />
                  <span>{card.change}</span>
                </div>
              </div>
              <div>
                <div className={`${headingClasses} text-2xl mb-1`}>
                  {card.value}
                </div>
                <div className={`${subheadingClasses} text-sm`}>
                  {card.title}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        {/* Recent Activity */}
        <div className={`${cardClasses} lg:col-span-2`}>
          <div className="flex items-center justify-between mb-6">
            <h2 className={`${headingClasses} text-xl`}>Recent Activity</h2>
            <button className={`text-sm cursor-pointer bg-none border-none ${
              isModernTheme ? 'text-gray-400 hover:text-white' : 'text-retro-cyan/70 hover:text-retro-cyan'
            }`}>
              View all
            </button>
          </div>
          
          <div className="flex flex-col gap-4">
            {recentActivity.map((activity) => (
              <div key={activity.id} className={`flex items-center justify-between p-4 rounded-xl ${
                isModernTheme ? 'bg-gray-800' : 'bg-dark-card border border-retro-cyan/20'
              }`}>
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    activity.type === 'sale' ? 'bg-green-400/20' :
                    activity.type === 'listing' ? 'bg-purple-500/20' : 'bg-red-400/20'
                  }`}>
                    {activity.type === 'sale' ? (
                      <Banknote className="w-5 h-5 text-green-400" />
                    ) : activity.type === 'listing' ? (
                      <PlusCircle className="w-5 h-5 text-purple-500" />
                    ) : (
                      <TrendingUp className="w-5 h-5 text-red-400" />
                    )}
                  </div>
                  <div>
                    <div className={`${headingClasses} text-sm mb-1`}>{activity.item}</div>
                    <div className={`${subheadingClasses} text-xs`}>
                      {activity.brand} • {activity.time}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className={`${headingClasses} text-sm mb-1`}>€{activity.amount}</div>
                  <div className={`${subheadingClasses} text-xs`}>
                    Profit: €{activity.profit.toFixed(2)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions & Performance Summary */}
        <div className="flex flex-col gap-6">
          <div className={cardClasses}>
            <h2 className={`${headingClasses} text-xl mb-6`}>Quick Actions</h2>
            
            <div className="flex flex-col gap-4">
              <button className={`${isModernTheme ? 'modern-button' : 'retro-button'} w-full justify-center flex items-center gap-2`}>
                <PlusCircle className="w-4 h-4" />
                <span>Add Product</span>
              </button>
              
              <button className={`${isModernTheme ? 'modern-button-secondary' : 'retro-button-success'} w-full justify-center flex items-center gap-2`}>
                <TrendingUp className="w-4 h-4" />
                <span>Update Prices</span>
              </button>
              
              <button className={`${isModernTheme ? 'modern-button-outline' : 'retro-button'} w-full justify-center flex items-center gap-2`}>
                <Activity className="w-4 h-4" />
                <span>View Analytics</span>
              </button>
            </div>
          </div>

          {/* Performance Summary */}
          <div className={cardClasses}>
            <h2 className={`${headingClasses} text-xl mb-6`}>This Week</h2>
            
            <div className="flex flex-col gap-4">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className={subheadingClasses}>Sales</span>
                  <span className={headingClasses}>24</span>
                </div>
                <div className={`w-full h-2 rounded overflow-hidden ${isModernTheme ? 'bg-gray-800' : 'bg-dark-card'}`}>
                  <div className="w-3/4 h-full bg-purple-500 rounded" />
                </div>
              </div>
              
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className={subheadingClasses}>Revenue</span>
                  <span className={headingClasses}>$3,420</span>
                </div>
                <div className={`w-full h-2 rounded overflow-hidden ${isModernTheme ? 'bg-gray-800' : 'bg-dark-card'}`}>
                  <div className="w-5/6 h-full bg-green-400 rounded" />
                </div>
              </div>
              
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className={subheadingClasses}>Listings</span>
                  <span className={headingClasses}>12</span>
                </div>
                <div className={`w-full h-2 rounded overflow-hidden ${isModernTheme ? 'bg-gray-800' : 'bg-dark-card'}`}>
                  <div className="w-3/5 h-full bg-red-400 rounded" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModernDashboard;