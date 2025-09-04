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

const Analytics = () => {
  const [stats, setStats] = useState<ProductStats | null>(null);
  const [enrichmentStatus, setEnrichmentStatus] = useState<EnrichmentStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEnriching, setIsEnriching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Check if we're in Tauri or web environment
      const isTauri = window.__TAURI__ !== undefined;
      
      if (isTauri) {
        // Use Tauri invoke for desktop app
        const [statsData, enrichmentData] = await Promise.all([
          invoke<ProductStats>('get_product_stats'),
          invoke<EnrichmentStatusResponse>('get_enrichment_status')
        ]);
        setStats(statsData);
        setEnrichmentStatus(enrichmentData);
      } else {
        // Use HTTP fetch for web app
        const [statsResponse, enrichmentResponse] = await Promise.all([
          fetch('http://localhost:8000/api/v1/products/stats'),
          fetch('http://localhost:8000/api/v1/products/enrichment/status')
        ]);
        
        if (!statsResponse.ok || !enrichmentResponse.ok) {
          throw new Error('Failed to fetch data from API');
        }
        
        const statsData = await statsResponse.json();
        const enrichmentData = await enrichmentResponse.json();
        
        setStats(statsData);
        setEnrichmentStatus(enrichmentData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      console.error('Failed to fetch analytics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const startEnrichment = async () => {
    setIsEnriching(true);
    try {
      // Check if we're in Tauri or web environment
      const isTauri = window.__TAURI__ !== undefined;
      
      if (isTauri) {
        // Use Tauri invoke for desktop app
        const response = await invoke<{message: string; target_products: string}>('start_product_enrichment', {
          productIds: null
        });
        console.log('Enrichment started:', response.message);
      } else {
        // Use HTTP fetch for web app
        const response = await fetch('http://localhost:8000/api/v1/products/enrichment/start', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ product_ids: null })
        });
        
        if (!response.ok) {
          throw new Error('Failed to start enrichment');
        }
        
        const result = await response.json();
        console.log('Enrichment started:', result.message);
      }
      
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
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <BarChart3 className="w-16 h-16 text-purple-400 animate-pulse mx-auto mb-4" />
          <p className="modern-heading text-xl">Loading Analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4 sm:gap-0">
        <div>
          <h1 className="text-2xl font-bold modern-heading mb-1">
            Analytics
          </h1>
          <p className="text-sm modern-subheading">
            Business intelligence and performance metrics
          </p>
        </div>
        <button 
          onClick={fetchStats}
          className="modern-button-outline flex items-center space-x-2 w-full sm:w-auto justify-center"
        >
          <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
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
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-4 sm:gap-0">
              <h2 className="text-xl sm:text-2xl font-bold modern-heading">Product Data Enrichment</h2>
              <button 
                onClick={startEnrichment}
                disabled={isEnriching}
                className={`modern-button flex items-center space-x-2 w-full sm:w-auto justify-center ${isEnriching ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <Zap className={`w-5 h-5 ${isEnriching ? 'animate-spin' : ''}`} />
                <span>{isEnriching ? 'Enriching...' : 'Start Enrichment'}</span>
              </button>
            </div>

            {enrichmentStatus && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                {Object.entries(enrichmentStatus.enrichment_stats).map(([field, stats]) => (
                  <div key={field} className="modern-card px-6 py-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs modern-heading uppercase tracking-wider">
                        {field.replace('_', ' ')}
                      </span>
                      {stats.completion_percentage >= 80 ? (
                        <CheckCircle className="w-5 h-5 text-green-400" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-yellow-400" />
                      )}
                    </div>
                    <div className="text-xl font-bold modern-heading mb-1">
                      {stats.completion_percentage.toFixed(1)}%
                    </div>
                    <div className="text-xs modern-subheading mb-2">
                      {stats.completed} / {stats.completed + stats.missing}
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-2">
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
              <div className="text-sm modern-subheading mb-1">Overall Data Completeness</div>
              <div className="text-2xl font-bold modern-heading text-purple-400">
                {enrichmentStatus?.overall_completion?.toFixed(1) || '0.0'}%
              </div>
            </div>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="modern-card px-6 py-3">
              <div className="flex items-center space-x-4">
                <div className="p-2 rounded-xl bg-blue-500/10">
                  <BarChart3 className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <div className="text-xl font-bold modern-heading">
                    {stats?.total_products || 0}
                  </div>
                  <div className="text-xs modern-subheading">
                    Total Products
                  </div>
                </div>
              </div>
            </div>
            
            <div className="modern-card px-6 py-3">
              <div className="flex items-center space-x-4">
                <div className="p-2 rounded-xl bg-green-500/10">
                  <TrendingUp className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <div className="text-xl font-bold modern-heading">
                    {formatCurrency(stats?.total_value || 0)}
                  </div>
                  <div className="text-xs modern-subheading">
                    Total Value
                  </div>
                </div>
              </div>
            </div>
            
            <div className="modern-card px-6 py-3">
              <div className="flex items-center space-x-4">
                <div className="p-2 rounded-xl bg-purple-500/10">
                  <PieChart className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <div className="text-xl font-bold modern-heading">
                    {stats?.total_brands || 0}
                  </div>
                  <div className="text-xs modern-subheading">
                    Brands
                  </div>
                </div>
              </div>
            </div>
            
            <div className="modern-card px-6 py-3">
              <div className="flex items-center space-x-4">
                <div className="p-2 rounded-xl bg-orange-500/10">
                  <TrendingUp className="w-5 h-5 text-orange-400" />
                </div>
                <div>
                  <div className="text-xl font-bold modern-heading">
                    {(stats?.avg_profit_margin || 0).toFixed(1)}%
                  </div>
                  <div className="text-xs modern-subheading">
                    Avg Profit Margin
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Top Brands Chart */}
          <div className="modern-card">
            <h2 className="text-xl font-bold modern-heading mb-3">Top Brands by Volume</h2>
            {stats?.top_brands && stats.top_brands.length > 0 ? (
              <div className="space-y-2">
                {stats.top_brands.slice(0, 8).map((brandStats, index) => {
                  const maxCount = Math.max(...stats.top_brands.map(b => b.total_items));
                  const percentage = maxCount > 0 ? (brandStats.total_items / maxCount) * 100 : 0;
                  
                  return (
                    <div key={brandStats.name} className="space-y-2">
                      {/* Mobile Layout - Stacked */}
                      <div className="block sm:hidden">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-bold modern-heading w-6">
                              #{index + 1}
                            </span>
                            <span className="text-sm font-medium modern-heading">
                              {brandStats.name}
                            </span>
                          </div>
                          <span className="text-xs font-medium modern-subheading">
                            {brandStats.total_items} items
                          </span>
                        </div>
                        <div className="h-6 bg-gray-800 rounded-full relative overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full transition-all duration-1000"
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                      
                      {/* Desktop Layout - Horizontal */}
                      <div className="hidden sm:flex items-center space-x-4">
                        <div className="w-8 text-center flex-shrink-0">
                          <span className="text-sm font-bold modern-heading">
                            #{index + 1}
                          </span>
                        </div>
                        <div className="w-32 flex-shrink-0">
                          <span className="text-sm font-medium modern-heading truncate block">
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
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="modern-card">
              <h3 className="text-xl font-bold modern-heading mb-3">Performance Insights</h3>
              <div className="space-y-2">
                <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center py-2 gap-1 sm:gap-0">
                  <span className="modern-subheading text-sm sm:text-base">Average Value per Item:</span>
                  <span className="font-bold modern-heading text-green-400 text-sm sm:text-base">
                    {formatCurrency(stats?.total_products 
                      ? (stats.total_value / stats.total_products)
                      : 0
                    )}
                  </span>
                </div>
                <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center py-2 gap-1 sm:gap-0">
                  <span className="modern-subheading text-sm sm:text-base">Items per Brand:</span>
                  <span className="font-bold modern-heading text-sm sm:text-base">
                    {stats?.total_brands 
                      ? Math.round(stats.total_products / stats.total_brands)
                      : 0
                    }
                  </span>
                </div>
                <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center py-2 gap-1 sm:gap-0">
                  <span className="modern-subheading text-sm sm:text-base">Portfolio Diversity:</span>
                  <span className={`font-bold text-sm sm:text-base ${stats?.total_brands && stats.total_brands > 20 ? 'text-green-400' : 'text-yellow-400'}`}>
                    {stats?.total_brands && stats.total_brands > 20 ? 'HIGH' : 'MODERATE'}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="modern-card">
              <h3 className="text-lg sm:text-xl font-bold modern-heading mb-4 sm:mb-6">Recommendations</h3>
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

export default Analytics;