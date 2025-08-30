import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { BarChart3, TrendingUp, PieChart, RefreshCw, Zap, CheckCircle, AlertCircle } from 'lucide-react';

interface BrandStats {
  name: string;
  total_products: number;
  total_items: number;
  avg_price: number;
  total_value: number;
}

interface ProductStats {
  total_products: number;
  total_value: number;
  total_brands: number;
  avg_profit_margin: number;
  top_brands: BrandStats[];
}

interface EnrichmentStats {
  completed: number;
  missing: number;
  completion_percentage: number;
}

interface EnrichmentStatusResponse {
  timestamp: string;
  total_products: number;
  enrichment_stats: {
    stockx_id: EnrichmentStats;
    description: EnrichmentStats;
    retail_price: EnrichmentStats;
    release_date: EnrichmentStats;
  };
  overall_completion: number;
}

const ModernAnalytics = () => {
  const [stats, setStats] = useState<ProductStats | null>(null);
  const [enrichmentStatus, setEnrichmentStatus] = useState<EnrichmentStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEnriching, setIsEnriching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const [statsData, enrichmentData] = await Promise.all([
        invoke<ProductStats>('get_product_stats'),
        invoke<EnrichmentStatusResponse>('get_enrichment_status')
      ]);
      setStats(statsData);
      setEnrichmentStatus(enrichmentData);
    } catch (err) {
      setError(err as string);
      console.error('Failed to fetch analytics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const startEnrichment = async () => {
    setIsEnriching(true);
    try {
      const response = await invoke<{message: string; target_products: string}>('start_product_enrichment', {
        productIds: null
      });
      console.log('Enrichment started:', response.message);
      setTimeout(() => {
        fetchStats();
      }, 2000);
    } catch (err) {
      console.error('Failed to start enrichment:', err);
    } finally {
      setIsEnriching(false);
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
      <div className="h-full w-full flex items-center justify-center" style={{background: '#16161a'}}>
        <div className="text-center">
          <BarChart3 className="w-16 h-16 text-purple-400 animate-pulse mx-auto mb-4" />
          <p className="text-gray-200 text-xl">Loading Analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full p-8 space-y-8 overflow-y-auto" style={{background: '#16161a', color: '#94a1b2'}}>
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-4xl font-bold modern-heading mb-2">
            Analytics
          </h1>
          <p className="text-xl modern-subheading">
            Business intelligence and performance metrics
          </p>
        </div>
        <button 
          onClick={fetchStats}
          className="modern-button-outline flex items-center space-x-2"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error ? (
        <div className="modern-card text-center">
          <p className="text-red-400 text-lg">{error}</p>
          <button onClick={fetchStats} className="modern-button mt-4">Retry</button>
        </div>
      ) : (
        <>
          {/* Product Data Enrichment */}
          <div className="modern-card">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold modern-heading">Product Data Enrichment</h2>
              <button 
                onClick={startEnrichment}
                disabled={isEnriching}
                className={`modern-button flex items-center space-x-2 ${isEnriching ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <Zap className={`w-4 h-4 ${isEnriching ? 'animate-spin' : ''}`} />
                <span>{isEnriching ? 'Enriching...' : 'Start Enrichment'}</span>
              </button>
            </div>

            {enrichmentStatus && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
                {Object.entries(enrichmentStatus.enrichment_stats).map(([field, stats]) => (
                  <div key={field} className="modern-card">
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-sm modern-heading uppercase tracking-wider">
                        {field.replace('_', ' ')}
                      </span>
                      {stats.completion_percentage >= 80 ? (
                        <CheckCircle className="w-5 h-5 text-green-400" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-yellow-400" />
                      )}
                    </div>
                    <div className="text-3xl font-bold modern-heading mb-2">
                      {stats.completion_percentage.toFixed(1)}%
                    </div>
                    <div className="text-sm modern-subheading mb-4">
                      {stats.completed} / {stats.completed + stats.missing} complete
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-3">
                      <div 
                        className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full transition-all duration-1000"
                        style={{ width: `${stats.completion_percentage}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="text-center">
              <div className="text-lg modern-subheading mb-2">Overall Data Completeness</div>
              <div className="text-5xl font-bold modern-heading text-purple-400">
                {enrichmentStatus?.overall_completion?.toFixed(1) || '0.0'}%
              </div>
            </div>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="modern-card text-center">
              <div className="p-4 rounded-xl bg-blue-500/10 mb-4 inline-block">
                <BarChart3 className="w-8 h-8 text-blue-400" />
              </div>
              <p className="text-sm modern-subheading uppercase tracking-wider mb-2">Total Products</p>
              <p className="text-3xl font-bold modern-heading">
                {stats?.total_products || 0}
              </p>
            </div>
            
            <div className="modern-card text-center">
              <div className="p-4 rounded-xl bg-green-500/10 mb-4 inline-block">
                <TrendingUp className="w-8 h-8 text-green-400" />
              </div>
              <p className="text-sm modern-subheading uppercase tracking-wider mb-2">Total Value</p>
              <p className="text-3xl font-bold modern-heading">
                {formatCurrency(stats?.total_value || 0)}
              </p>
            </div>
            
            <div className="modern-card text-center">
              <div className="p-4 rounded-xl bg-purple-500/10 mb-4 inline-block">
                <PieChart className="w-8 h-8 text-purple-400" />
              </div>
              <p className="text-sm modern-subheading uppercase tracking-wider mb-2">Brands</p>
              <p className="text-3xl font-bold modern-heading">
                {stats?.total_brands || 0}
              </p>
            </div>
            
            <div className="modern-card text-center">
              <div className="p-4 rounded-xl bg-orange-500/10 mb-4 inline-block">
                <TrendingUp className="w-8 h-8 text-orange-400" />
              </div>
              <p className="text-sm modern-subheading uppercase tracking-wider mb-2">Avg Profit Margin</p>
              <p className="text-3xl font-bold modern-heading">
                {(stats?.avg_profit_margin || 0).toFixed(1)}%
              </p>
            </div>
          </div>

          {/* Top Brands Chart */}
          <div className="modern-card">
            <h2 className="text-2xl font-bold modern-heading mb-6">Top Brands by Volume</h2>
            {stats?.top_brands && stats.top_brands.length > 0 ? (
              <div className="space-y-4">
                {stats.top_brands.slice(0, 10).map((brandStats, index) => {
                  const maxCount = Math.max(...stats.top_brands.map(b => b.total_items));
                  const percentage = maxCount > 0 ? (brandStats.total_items / maxCount) * 100 : 0;
                  
                  return (
                    <div key={brandStats.name} className="flex items-center space-x-4">
                      <div className="w-8 text-center">
                        <span className="text-sm font-bold modern-heading">
                          #{index + 1}
                        </span>
                      </div>
                      <div className="w-32">
                        <span className="text-sm font-medium modern-heading">
                          {brandStats.name}
                        </span>
                      </div>
                      <div className="flex-1 h-10 bg-gray-800 rounded-full relative overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full transition-all duration-1000"
                          style={{ width: `${percentage}%` }}
                        />
                        <div className="absolute inset-0 flex items-center justify-end pr-4">
                          <span className="text-sm font-medium modern-subheading">
                            {brandStats.total_items} items
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-12">
                <PieChart className="w-16 h-16 text-gray-500 mx-auto mb-4" />
                <p className="modern-subheading text-lg">No brand data available</p>
              </div>
            )}
          </div>

          {/* Performance Insights */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="modern-card">
              <h3 className="text-xl font-bold modern-heading mb-6">Performance Insights</h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center py-2">
                  <span className="modern-subheading">Average Value per Item:</span>
                  <span className="font-bold modern-heading text-green-400">
                    {formatCurrency(stats?.total_products 
                      ? (stats.total_value / stats.total_products)
                      : 0
                    )}
                  </span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="modern-subheading">Items per Brand:</span>
                  <span className="font-bold modern-heading">
                    {stats?.total_brands 
                      ? Math.round(stats.total_products / stats.total_brands)
                      : 0
                    }
                  </span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="modern-subheading">Portfolio Diversity:</span>
                  <span className={`font-bold ${stats?.total_brands && stats.total_brands > 20 ? 'text-green-400' : 'text-yellow-400'}`}>
                    {stats?.total_brands && stats.total_brands > 20 ? 'HIGH' : 'MODERATE'}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="modern-card">
              <h3 className="text-xl font-bold modern-heading mb-6">Recommendations</h3>
              <div className="space-y-3">
                {(stats?.avg_profit_margin || 0) < 20 && (
                  <div className="p-4 border border-yellow-500/30 bg-yellow-500/10 rounded-xl">
                    <p className="text-sm modern-subheading">
                      • Consider focusing on higher-margin items
                    </p>
                  </div>
                )}
                {(stats?.total_brands || 0) < 10 && (
                  <div className="p-4 border border-purple-500/30 bg-purple-500/10 rounded-xl">
                    <p className="text-sm modern-subheading">
                      • Diversify brand portfolio for better risk distribution
                    </p>
                  </div>
                )}
                {(stats?.total_products || 0) > 1000 && (
                  <div className="p-4 border border-green-500/30 bg-green-500/10 rounded-xl">
                    <p className="text-sm modern-subheading">
                      • Strong inventory volume - optimize turnover rate
                    </p>
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

export default ModernAnalytics;