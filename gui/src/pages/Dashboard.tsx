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
import { Button, Card, Heading, Text } from '../components/ui';
import { QuickFlipWidget } from '../components/Dashboard/QuickFlipWidget';

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

  // These variables were used in the old design but are now replaced by the new UI components
  // Keeping them for reference but they're no longer used
  // const containerClasses = 'min-h-screen padding-section space-section fade-in';
  // const cardClasses = 'modern-card-elevated';
  // const metricCardClasses = 'modern-card-metric slide-up';
  // const headingClasses = 'heading-lg';
  // const subheadingClasses = 'body-md';

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
      <div
        className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-purple-900/20 to-gray-900"
        role="status"
        aria-live="polite"
        aria-label="Loading dashboard data"
      >
        <div className="text-center space-element">
          <div className="pulse-glow rounded-full w-20 h-20 mx-auto mb-6 flex items-center justify-center bg-gradient-to-r from-purple-500/20 to-green-500/20">
            <RefreshCw className="w-12 h-12 animate-spin text-purple-400" aria-hidden="true" />
          </div>
          <h2 className="heading-md mb-2">Loading Dashboard...</h2>
          <p className="body-lg">Fetching your latest metrics</p>
        </div>
      </div>
    );
  }

  return (
    <div className="responsive-p-lg space-section fade-in">
      {/* Enhanced Responsive Header */}
      <header className="flex flex-col sm:flex-row sm:justify-between sm:items-start mb-8 sm:mb-12 space-y-4 sm:space-y-0">
        <div className="space-tight">
          <Heading level={1} variant="display" gradient>
            Dashboard
          </Heading>
          <Text variant="body" color="secondary" size="lg">
            Real-time insights into your business performance
          </Text>
        </div>
        <button
          onClick={fetchMetrics}
          disabled={isLoading}
          className="youtube-button flex items-center space-x-3 micro-bounce self-start focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900"
          aria-label={isLoading ? 'Refreshing dashboard data' : 'Refresh dashboard data'}
          type="button"
        >
          <RefreshCw
            className={`w-4 h-4 sm:w-5 sm:h-5 ${isLoading ? 'animate-spin' : ''}`}
            aria-hidden="true"
          />
          <span className="responsive-text-sm">Refresh Data</span>
        </button>
      </header>

      {/* Enhanced Responsive Stats Grid */}
      <section aria-labelledby="metrics-heading" className="responsive-grid mb-8 sm:mb-12 lg:mb-16">
        <h2 id="metrics-heading" className="sr-only">Key Performance Metrics</h2>
        {statCards.map((card, index) => {
          const Icon = card.icon;
          return (
            <article
              key={card.title}
              className="frosted-glass reactive-card group micro-pulse"
              style={{
                animationDelay: `${index * 0.1}s`,
                padding: '1.5rem',
                borderRadius: '16px'
              }}
              role="article"
              aria-labelledby={`metric-${index}-title`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="metric-icon group-hover:scale-110 reactive-icon">
                  <Icon className="w-5 h-5 sm:w-6 sm:h-6 text-purple-400" aria-hidden="true" />
                </div>
                <div className="w-1 h-6 sm:h-8 bg-gradient-to-b from-purple-500 to-transparent rounded-full opacity-60" aria-hidden="true" />
              </div>
              <div className="space-tight">
                <div className="responsive-text-2xl font-bold tracking-tight mb-2" style={{
                  background: 'linear-gradient(135deg, #fffffe 0%, #7f5af0 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text'
                }}>
                  {card.value}
                </div>
                <h3
                  id={`metric-${index}-title`}
                  className="responsive-text-sm font-medium uppercase tracking-wider"
                  style={{
                    color: '#94a1b2',
                    letterSpacing: '0.1em'
                  }}
                >
                  {card.title}
                </h3>
              </div>
            </article>
          );
        })}
      </section>

      {/* Enhanced Responsive Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8 lg:gap-12">
        {/* QuickFlip Opportunities Widget */}
        <div className="lg:col-span-1">
          <QuickFlipWidget />
        </div>

        {/* Enhanced Recent Activity */}
        <section
          className="frosted-glass lg:col-span-2 space-element responsive-p-lg"
          aria-labelledby="recent-activity-heading"
        >
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 sm:mb-8 space-y-2 sm:space-y-0">
            <div className="space-tight">
              <h2 id="recent-activity-heading" className="responsive-text-2xl font-semibold" style={{ color: '#fffffe' }}>Recent Activity</h2>
              <p className="responsive-text-sm uppercase tracking-wider font-medium" style={{ color: '#72757e' }}>Latest transactions and updates</p>
            </div>
            <button
              className="youtube-button text-sm self-start sm:self-auto focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900"
              aria-label="View all recent activity"
              type="button"
            >
              View all →
            </button>
          </div>
          
          <div className="space-element" role="list" aria-label="Recent transactions">
            {recentActivity.length > 0 ? recentActivity.map((activity, index) => (
              <article
                key={activity.id}
                className="group flex items-center justify-between p-6 md:p-8 rounded-2xl bg-gradient-to-r from-gray-800/50 to-gray-800/30 hover:from-gray-700/50 hover:to-gray-700/30 border border-gray-700/50 hover:border-purple-500/30 transition-all duration-300 backdrop-blur-sm"
                style={{ animationDelay: `${index * 0.1}s` }}
                role="listitem"
                aria-labelledby={`activity-${activity.id}-title`}
              >
                <div className="flex items-center gap-6">
                  <div className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-all duration-300 ${
                    activity.type === 'sale' ? 'bg-gradient-to-br from-green-400/20 to-green-600/10 border border-green-400/20' :
                    activity.type === 'listing' ? 'bg-gradient-to-br from-purple-500/20 to-purple-700/10 border border-purple-500/20' : 'bg-gradient-to-br from-red-400/20 to-red-600/10 border border-red-400/20'
                  }`}>
                    {activity.type === 'sale' ? (
                      <Banknote className="w-6 h-6 text-green-400 group-hover:scale-110 transition-transform" aria-hidden="true" />
                    ) : activity.type === 'listing' ? (
                      <PlusCircle className="w-6 h-6 text-purple-500 group-hover:scale-110 transition-transform" aria-hidden="true" />
                    ) : (
                      <TrendingUp className="w-6 h-6 text-red-400 group-hover:scale-110 transition-transform" aria-hidden="true" />
                    )}
                  </div>
                  <div className="space-micro">
                    <h4 id={`activity-${activity.id}-title`} className="label mb-1">{activity.item}</h4>
                    <p className="caption">
                      {activity.brand} • <time dateTime={new Date().toISOString()}>{activity.time}</time>
                    </p>
                  </div>
                </div>
                <div className="text-right space-micro">
                  <div className="label mb-1">€{activity.amount}</div>
                  <div className="caption">
                    Profit: €{activity.profit.toFixed(2)}
                  </div>
                </div>
              </article>
            )) : (
              <div className="text-center p-12 md:p-16 space-element" role="status">
                <div className="w-20 h-20 mx-auto mb-6 rounded-3xl bg-gradient-to-br from-gray-700/30 to-gray-800/30 border border-gray-600/30 flex items-center justify-center">
                  <Activity className="w-10 h-10 text-gray-500" aria-hidden="true" />
                </div>
                <h3 className="heading-sm mb-3">No Recent Activity</h3>
                <p className="body-md">
                  Transaction data will appear here once sales are recorded in the system.
                </p>
              </div>
            )}
          </div>
        </section>

        {/* Enhanced Quick Actions & Performance Summary */}
        <div className="space-component">
          <div className="frosted-glass space-element responsive-p-lg">
            <div className="space-tight mb-6 sm:mb-8">
              <h2 className="responsive-text-xl font-semibold" style={{ color: '#fffffe' }}>Quick Actions</h2>
              <p className="responsive-text-sm uppercase tracking-wider font-medium" style={{ color: '#72757e' }}>Common tasks and shortcuts</p>
            </div>

            <div className="space-element">
              <button className="youtube-button w-full flex items-center justify-center space-x-3 group micro-bounce">
                <PlusCircle className="w-4 h-4 sm:w-5 sm:h-5 group-hover:rotate-90 reactive-icon" />
                <span className="responsive-text-sm">Add Product</span>
              </button>

              <button className="modern-button-secondary w-full flex items-center justify-center space-x-3 group micro-bounce">
                <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5 group-hover:scale-110 reactive-icon" />
                <span className="responsive-text-sm">Update Prices</span>
              </button>

              <button className="modern-button-outline w-full flex items-center justify-center space-x-3 group micro-bounce">
                <Activity className="w-4 h-4 sm:w-5 sm:h-5 group-hover:rotate-12 reactive-icon" />
                <span className="responsive-text-sm">View Analytics</span>
              </button>
            </div>
          </div>

          {/* Enhanced Performance Summary */}
          <div className="frosted-glass space-element responsive-p-lg">
            <div className="space-tight mb-6 sm:mb-8">
              <h2 className="responsive-text-xl font-semibold" style={{ color: '#fffffe' }}>This Week</h2>
              <p className="responsive-text-sm uppercase tracking-wider font-medium" style={{ color: '#72757e' }}>Performance metrics overview</p>
            </div>

            <div className="space-element">
              <div className="space-tight">
                <div className="flex justify-between items-center mb-3">
                  <span className="label-secondary">Sales</span>
                  <span className="heading-sm">{metrics.weekly_stats.sales_count}</span>
                </div>
                <div className="w-full h-3 rounded-full overflow-hidden bg-gradient-to-r from-gray-800 to-gray-700 border border-gray-600/30">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-purple-400 rounded-full transition-all duration-700 ease-out shadow-lg"
                    style={{ width: `${Math.min(100, (metrics.weekly_stats.sales_count / 50) * 100)}%` }}
                  />
                </div>
              </div>

              <div className="space-tight">
                <div className="flex justify-between items-center mb-3">
                  <span className="label-secondary">Revenue</span>
                  <span className="heading-sm">€{metrics.weekly_stats.revenue.toLocaleString()}</span>
                </div>
                <div className="w-full h-3 rounded-full overflow-hidden bg-gradient-to-r from-gray-800 to-gray-700 border border-gray-600/30">
                  <div
                    className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded-full transition-all duration-700 ease-out shadow-lg"
                    style={{ width: `${Math.min(100, (metrics.weekly_stats.revenue / 5000) * 100)}%` }}
                  />
                </div>
              </div>

              <div className="space-tight">
                <div className="flex justify-between items-center mb-3">
                  <span className="label-secondary">New Listings</span>
                  <span className="heading-sm">{metrics.weekly_stats.new_listings}</span>
                </div>
                <div className="w-full h-3 rounded-full overflow-hidden bg-gradient-to-r from-gray-800 to-gray-700 border border-gray-600/30">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full transition-all duration-700 ease-out shadow-lg"
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