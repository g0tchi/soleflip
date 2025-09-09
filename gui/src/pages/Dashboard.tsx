import { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Package, 
  Banknote, 
  Activity,
  ShoppingCart,
  PlusCircle,
  RefreshCw
} from 'lucide-react';
import { invoke } from '@tauri-apps/api/tauri';

interface DashboardMetrics {
  total_inventory_value: number;
  monthly_sales: number;
  profit_margin: number;
  active_listings: number;
  pending_imports: number;
  recent_transactions: any[];
  weekly_stats: {
    sales_count: number;
    revenue: number;
    new_listings: number;
  };
}

const Dashboard = () => {
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
    recent_transactions: [],
    weekly_stats: {
      sales_count: 0,
      revenue: 0,
      new_listings: 0
    }
  });
  const [isLoading, setIsLoading] = useState(true);

  // Modern theme styles
  const containerClasses = 'min-h-screen p-8 space-y-8';
  const cardClasses = 'modern-card';
  const headingClasses = 'modern-heading';
  const subheadingClasses = 'modern-subheading';

  const fetchMetrics = async () => {
    try {
      setIsLoading(true);
      const response = await invoke<any>('get_dashboard_metrics');
      
      // Ensure weekly_stats exists, provide defaults if missing
      const metricsWithDefaults = {
        ...response,
        weekly_stats: response.weekly_stats || {
          sales_count: 0,
          revenue: 0,
          new_listings: 0
        }
      };
      
      setMetrics(metricsWithDefaults);
    } catch (error) {
      console.error('Failed to fetch dashboard metrics:', error);
      // Keep metrics at zero if API fails - no fake data
      setMetrics({
        total_inventory_value: 0,
        monthly_sales: 0,
        profit_margin: 0,
        active_listings: 0,
        pending_imports: 0,
        recent_transactions: [],
        weekly_stats: {
          sales_count: 0,
          revenue: 0,
          new_listings: 0
        }
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 300000); // 5 minutes
    return () => clearInterval(interval);
  }, []);


  const statCards = [
    {
      title: 'Total Revenue',
      value: `€${metrics.total_inventory_value.toLocaleString()}`,
      icon: Banknote,
      color: 'green'
    },
    {
      title: 'Monthly Sales',
      value: `€${metrics.monthly_sales.toLocaleString()}`,
      icon: Package,
      color: 'blue'
    },
    {
      title: "Profit Margin",
      value: `${metrics.profit_margin.toFixed(1)}%`,
      icon: ShoppingCart,
      color: 'purple'
    },
    {
      title: 'Active Listings',
      value: metrics.active_listings.toLocaleString(),
      icon: Activity,
      color: 'orange'
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
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-16 h-16 animate-spin mx-auto mb-4 text-purple-500" />
          <p className={`${headingClasses} text-xl`}>Loading Dashboard...</p>
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
          className="modern-button-outline flex items-center space-x-2"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.title} className="modern-card px-6 py-3">
              <div className="flex items-center space-x-4">
                <div className={`p-2 rounded-xl bg-${card.color}-500/10`}>
                  <Icon className={`w-5 h-5 text-${card.color}-400`} />
                </div>
                <div>
                  <div className="text-xl font-bold modern-heading">
                    {card.value}
                  </div>
                  <div className="text-xs modern-subheading">
                    {card.title}
                  </div>
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
            <button className="text-sm cursor-pointer bg-none border-none text-gray-400 hover:text-white">
              View all
            </button>
          </div>
          
          <div className="flex flex-col gap-4">
            {recentActivity.length > 0 ? recentActivity.map((activity) => (
              <div key={activity.id} className="flex items-center justify-between p-4 rounded-xl bg-gray-800">
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
            )) : (
              <div className="text-center py-8">
                <Activity className="w-12 h-12 mx-auto mb-4 text-gray-500" />
                <p className={`${headingClasses} text-lg mb-2`}>No Recent Activity</p>
                <p className={`${subheadingClasses} text-sm`}>
                  Transaction data will appear here once sales are recorded in the system.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions & Performance Summary */}
        <div className="flex flex-col gap-6">
          <div className={cardClasses}>
            <h2 className={`${headingClasses} text-xl mb-6`}>Quick Actions</h2>
            
            <div className="flex flex-col gap-4">
              <button className="modern-button w-full flex items-center justify-center space-x-2">
                <PlusCircle className="w-4 h-4" />
                <span>Add Product</span>
              </button>
              
              <button className="modern-button-secondary w-full flex items-center justify-center space-x-2">
                <TrendingUp className="w-4 h-4" />
                <span>Update Prices</span>
              </button>
              
              <button className="modern-button-outline w-full flex items-center justify-center space-x-2">
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
                  <span className={headingClasses}>{metrics.weekly_stats.sales_count}</span>
                </div>
                <div className="w-full h-2 rounded overflow-hidden bg-gray-800">
                  <div 
                    className="h-full bg-purple-500 rounded transition-all duration-300" 
                    style={{ width: `${Math.min(100, (metrics.weekly_stats.sales_count / 50) * 100)}%` }}
                  />
                </div>
              </div>
              
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className={subheadingClasses}>Revenue</span>
                  <span className={headingClasses}>€{metrics.weekly_stats.revenue.toLocaleString()}</span>
                </div>
                <div className="w-full h-2 rounded overflow-hidden bg-gray-800">
                  <div 
                    className="h-full bg-green-400 rounded transition-all duration-300" 
                    style={{ width: `${Math.min(100, (metrics.weekly_stats.revenue / 5000) * 100)}%` }}
                  />
                </div>
              </div>
              
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className={subheadingClasses}>New Listings</span>
                  <span className={headingClasses}>{metrics.weekly_stats.new_listings}</span>
                </div>
                <div className="w-full h-2 rounded overflow-hidden bg-gray-800">
                  <div 
                    className="h-full bg-red-400 rounded transition-all duration-300" 
                    style={{ width: `${Math.min(100, (metrics.weekly_stats.new_listings / 20) * 100)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;