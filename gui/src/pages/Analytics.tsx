import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { BarChart3, TrendingUp, PieChart, RefreshCw } from 'lucide-react';

interface ProductStats {
  total_products: number;
  total_value: number;
  brands_count: number;
  avg_profit_margin: number;
  top_brands: [string, number][];
}

const Analytics = () => {
  const [stats, setStats] = useState<ProductStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await invoke<ProductStats>('get_product_stats');
      setStats(data);
    } catch (err) {
      setError(err as string);
      console.error('Failed to fetch analytics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
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
          <BarChart3 className="w-16 h-16 text-retro-cyan animate-pulse mx-auto mb-4" />
          <p className="text-retro-cyan font-mono">LOADING ANALYTICS...</p>
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
            ANALYTICS
          </h1>
          <p className="text-retro-cyan/70 font-mono mt-1">
            Business intelligence and performance metrics
          </p>
        </div>
        <button 
          onClick={fetchStats}
          className="retro-button flex items-center space-x-2"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>REFRESH</span>
        </button>
      </div>

      {error ? (
        <div className="retro-card text-center">
          <p className="text-retro-magenta font-mono">{error}</p>
          <button onClick={fetchStats} className="retro-button mt-4">RETRY</button>
        </div>
      ) : (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="retro-card text-center">
              <BarChart3 className="w-12 h-12 text-retro-cyan mx-auto mb-3" />
              <p className="text-sm font-mono uppercase tracking-wider opacity-70">Total Products</p>
              <p className="text-3xl font-retro font-bold text-retro-green mt-2">
                {stats?.total_products || 0}
              </p>
            </div>
            
            <div className="retro-card text-center">
              <TrendingUp className="w-12 h-12 text-retro-green mx-auto mb-3" />
              <p className="text-sm font-mono uppercase tracking-wider opacity-70">Total Value</p>
              <p className="text-3xl font-retro font-bold text-retro-yellow mt-2">
                {formatCurrency(stats?.total_value || 0)}
              </p>
            </div>
            
            <div className="retro-card text-center">
              <PieChart className="w-12 h-12 text-retro-magenta mx-auto mb-3" />
              <p className="text-sm font-mono uppercase tracking-wider opacity-70">Brands</p>
              <p className="text-3xl font-retro font-bold text-retro-magenta mt-2">
                {stats?.brands_count || 0}
              </p>
            </div>
            
            <div className="retro-card text-center">
              <TrendingUp className="w-12 h-12 text-retro-yellow mx-auto mb-3" />
              <p className="text-sm font-mono uppercase tracking-wider opacity-70">Avg Profit Margin</p>
              <p className="text-3xl font-retro font-bold text-retro-cyan mt-2">
                {(stats?.avg_profit_margin || 0).toFixed(1)}%
              </p>
            </div>
          </div>

          {/* Top Brands Chart */}
          <div className="retro-card">
            <h2 className="text-xl font-retro text-retro-cyan mb-6">TOP BRANDS BY VOLUME</h2>
            {stats?.top_brands && stats.top_brands.length > 0 ? (
              <div className="space-y-4">
                {stats.top_brands.slice(0, 10).map(([brand, count], index) => {
                  const maxCount = stats.top_brands[0][1];
                  const percentage = (count / maxCount) * 100;
                  
                  return (
                    <div key={brand} className="flex items-center space-x-4">
                      <div className="w-4 text-retro-cyan font-mono text-sm">
                        #{index + 1}
                      </div>
                      <div className="w-32 text-retro-yellow font-mono text-sm truncate">
                        {brand}
                      </div>
                      <div className="flex-1 h-8 bg-dark-card border border-retro-cyan/30 relative">
                        <div 
                          className="h-full bg-retro-cyan transition-all duration-1000 relative"
                          style={{ width: `${percentage}%` }}
                        >
                          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-scan"></div>
                        </div>
                        <div className="absolute inset-0 flex items-center justify-end pr-2">
                          <span className="text-xs font-mono text-retro-cyan/80">
                            {count} items
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8 text-retro-cyan/50">
                <PieChart className="w-12 h-12 mx-auto mb-2" />
                <p className="font-mono">No brand data available</p>
              </div>
            )}
          </div>

          {/* Performance Insights */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="retro-card">
              <h3 className="text-lg font-retro text-retro-cyan mb-4">PERFORMANCE INSIGHTS</h3>
              <div className="space-y-3 font-mono text-sm">
                <div className="flex justify-between">
                  <span>Average Value per Item:</span>
                  <span className="text-retro-green">
                    {formatCurrency(stats?.total_products 
                      ? (stats.total_value / stats.total_products)
                      : 0
                    )}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Items per Brand:</span>
                  <span className="text-retro-cyan">
                    {stats?.brands_count 
                      ? Math.round(stats.total_products / stats.brands_count)
                      : 0
                    }
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Portfolio Diversity:</span>
                  <span className={stats?.brands_count && stats.brands_count > 20 ? 'text-retro-green' : 'text-retro-yellow'}>
                    {stats?.brands_count && stats.brands_count > 20 ? 'HIGH' : 'MODERATE'}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="retro-card">
              <h3 className="text-lg font-retro text-retro-cyan mb-4">RECOMMENDATIONS</h3>
              <div className="space-y-2 font-mono text-sm text-retro-cyan/80">
                {(stats?.avg_profit_margin || 0) < 20 && (
                  <div className="p-2 border border-retro-yellow/30 bg-retro-yellow/5">
                    • Consider focusing on higher-margin items
                  </div>
                )}
                {(stats?.brands_count || 0) < 10 && (
                  <div className="p-2 border border-retro-magenta/30 bg-retro-magenta/5">
                    • Diversify brand portfolio for better risk distribution
                  </div>
                )}
                {(stats?.total_products || 0) > 1000 && (
                  <div className="p-2 border border-retro-green/30 bg-retro-green/5">
                    • Strong inventory volume - optimize turnover rate
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Analytics;