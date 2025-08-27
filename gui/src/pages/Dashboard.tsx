import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { 
  TrendingUp, 
  Package, 
  DollarSign, 
  Activity,
  RefreshCw,
  AlertTriangle 
} from 'lucide-react';

interface DashboardMetrics {
  total_inventory_value: number;
  monthly_sales: number;
  profit_margin: number;
  active_listings: number;
  pending_imports: number;
  recent_transactions: any[];
}

interface MetricCardProps {
  title: string;
  value: string;
  icon: React.ComponentType<any>;
  color: 'cyan' | 'green' | 'yellow' | 'magenta';
  subtitle?: string;
}

const MetricCard = ({ title, value, icon: Icon, color, subtitle }: MetricCardProps) => {
  const colorClasses = {
    cyan: 'text-retro-cyan border-retro-cyan shadow-[0_0_20px_rgba(0,255,255,0.2)]',
    green: 'text-retro-green border-retro-green shadow-[0_0_20px_rgba(0,255,0,0.2)]',
    yellow: 'text-retro-yellow border-retro-yellow shadow-[0_0_20px_rgba(255,255,0,0.2)]',
    magenta: 'text-retro-magenta border-retro-magenta shadow-[0_0_20px_rgba(255,0,255,0.2)]',
  };

  return (
    <div className={`retro-card ${colorClasses[color]} hover:scale-105 transform transition-all duration-300`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-mono uppercase tracking-wider opacity-70">{title}</p>
          <p className="text-2xl font-retro font-bold mt-2 animate-glow">{value}</p>
          {subtitle && (
            <p className="text-xs opacity-50 mt-1">{subtitle}</p>
          )}
        </div>
        <Icon className="w-12 h-12 opacity-60" />
      </div>
    </div>
  );
};

const Dashboard = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchMetrics = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await invoke<DashboardMetrics>('get_dashboard_metrics');
      setMetrics(data);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err as string);
      console.error('Failed to fetch dashboard metrics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR'
    }).format(value);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <RefreshCw className="w-16 h-16 text-retro-cyan animate-spin mx-auto mb-4" />
          <p className="text-retro-cyan font-mono">LOADING DASHBOARD...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center retro-card max-w-md">
          <AlertTriangle className="w-16 h-16 text-retro-magenta mx-auto mb-4" />
          <h2 className="text-xl font-retro text-retro-magenta mb-2">CONNECTION ERROR</h2>
          <p className="text-sm text-retro-cyan/70 mb-4">{error}</p>
          <button 
            onClick={fetchMetrics}
            className="retro-button"
          >
            RETRY CONNECTION
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-retro font-bold text-retro-cyan animate-glow">
            DASHBOARD
          </h1>
          <p className="text-retro-cyan/70 font-mono mt-1">
            Real-time system overview and metrics
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-xs text-retro-cyan/50 font-mono">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </span>
          <button 
            onClick={fetchMetrics}
            disabled={isLoading}
            className="retro-button-success flex items-center space-x-2"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>REFRESH</span>
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Inventory Value"
          value={formatCurrency(metrics?.total_inventory_value || 0)}
          icon={DollarSign}
          color="green"
          subtitle="Current market value"
        />
        <MetricCard
          title="Monthly Sales"
          value={formatCurrency(metrics?.monthly_sales || 0)}
          icon={TrendingUp}
          color="cyan"
          subtitle="This month"
        />
        <MetricCard
          title="Active Listings"
          value={metrics?.active_listings.toString() || '0'}
          icon={Package}
          color="yellow"
          subtitle="Items for sale"
        />
        <MetricCard
          title="Profit Margin"
          value={`${(metrics?.profit_margin || 0).toFixed(1)}%`}
          icon={Activity}
          color="magenta"
          subtitle="Average margin"
        />
      </div>

      {/* Recent Activity */}
      <div className="retro-card">
        <h2 className="text-xl font-retro text-retro-cyan mb-4">RECENT ACTIVITY</h2>
        {metrics?.recent_transactions && metrics.recent_transactions.length > 0 ? (
          <div className="space-y-2">
            {metrics.recent_transactions.slice(0, 5).map((transaction, index) => (
              <div 
                key={index}
                className="flex justify-between items-center p-3 bg-dark-card border border-dark-border hover:border-retro-cyan/30 transition-colors"
              >
                <div className="font-mono text-sm">
                  <span className="text-retro-cyan">{transaction.product_name}</span>
                  <span className="text-retro-cyan/50 ml-2">#{transaction.id}</span>
                </div>
                <div className="text-right font-mono text-sm">
                  <div className="text-retro-green">{formatCurrency(transaction.amount)}</div>
                  <div className="text-retro-cyan/50 text-xs">
                    {new Date(transaction.date).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-retro-cyan/50">
            <Activity className="w-12 h-12 mx-auto mb-2" />
            <p className="font-mono">No recent transactions</p>
          </div>
        )}
      </div>

      {/* System Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="retro-card">
          <h3 className="text-lg font-retro text-retro-cyan mb-3">IMPORT STATUS</h3>
          <div className="flex items-center justify-between">
            <span className="font-mono">Pending Imports:</span>
            <span className="text-retro-yellow font-bold">
              {metrics?.pending_imports || 0}
            </span>
          </div>
        </div>
        
        <div className="retro-card">
          <h3 className="text-lg font-retro text-retro-cyan mb-3">SYSTEM HEALTH</h3>
          <div className="space-y-2 font-mono text-sm">
            <div className="flex justify-between">
              <span>API Status:</span>
              <span className="status-healthy">ONLINE</span>
            </div>
            <div className="flex justify-between">
              <span>Database:</span>
              <span className="status-healthy">CONNECTED</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;