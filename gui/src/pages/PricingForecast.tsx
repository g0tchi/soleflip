import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { 
  TrendingUp, 
  Banknote, 
  Target, 
  Brain, 
  BarChart3, 
  Activity,
  Zap,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Star,
  Bot,
  TrendingDown,
  Play,
  Pause
} from 'lucide-react';

// TypeScript interfaces
interface PricingInsights {
  timestamp: string;
  summary: {
    total_products_analyzed: number;
    average_price: number;
    average_margin_percent: number;
    total_price_updates: number;
    recent_updates_30d: number;
  };
  recommendations: string[];
}


interface PredictiveInsights {
  timestamp: string;
  business_metrics: {
    transactions_90d: number;
    revenue_90d: number;
    avg_transaction_value: number;
    active_products: number;
    active_brands: number;
  };
  predictive_insights: string[];
  growth_opportunities: string[];
  risk_factors: string[];
  recommendations: string[];
  confidence_score: number;
}

interface MarketTrend {
  period: string;
  trend_direction: string;
  strength: number;
  key_drivers: string[];
  forecast_impact: string;
}

interface ForecastRequest {
  product_id?: string;
  brand_id?: string;
  category_id?: string;
  horizon_days: number;
  model?: string;
  confidence_level: number;
}

interface ForecastAnalysis {
  forecast?: {
    target_id: string;
    target_type: string;
    predicted_sales: number;
    predicted_revenue: number;
    confidence_interval_lower: number;
    confidence_interval_upper: number;
    model_used: string;
    trend: string;
  };
  // Alternative direct response format
  target_id?: string;
  target_type?: string;
  predicted_sales?: number;
  predicted_revenue?: number;
  confidence_interval_lower?: number;
  confidence_interval_upper?: number;
  model_used?: string;
  trend?: string;
  key_insights?: string[];
  recommendations?: string[];
}

interface SmartPricingOptimization {
  total_items_analyzed: number;
  items_optimized: number;
  potential_profit_increase: number;
  pricing_strategy: string;
  market_conditions: string;
  timestamp: string;
  recommendations: Array<{
    product_name: string;
    current_price: number;
    recommended_price: number;
    profit_increase: number;
    confidence: number;
  }>;
}

interface AutoRepricingStatus {
  enabled: boolean;
  last_run: string | null;
  items_repriced: number;
  strategy: string;
  next_run: string | null;
  rules_applied: number;
}

interface MarketTrendData {
  current_condition: string;
  trend_strength: number;
  volatility_level: string;
  price_momentum: string;
  recommended_action: string;
  confidence_score: number;
  key_insights: string[];
}

const PricingForecast = () => {
  const [pricingInsights, setPricingInsights] = useState<PricingInsights | null>(null);
  const [predictiveInsights, setPredictiveInsights] = useState<PredictiveInsights | null>(null);
  const [marketTrends, setMarketTrends] = useState<MarketTrend[]>([]);
  const [forecastResult, setForecastResult] = useState<ForecastAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Smart Pricing states
  const [smartPricingResult, setSmartPricingResult] = useState<SmartPricingOptimization | null>(null);
  const [autoRepricingStatus, setAutoRepricingStatus] = useState<AutoRepricingStatus | null>(null);
  const [marketTrendData, setMarketTrendData] = useState<MarketTrendData | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState('profit_maximization');
  const [showSmartPricing, setShowSmartPricing] = useState(true);
  
  // Forecast settings
  const [forecastDays, setForecastDays] = useState(30);
  const [confidenceLevel] = useState(0.95);
  const [isGeneratingForecast, setIsGeneratingForecast] = useState(false);

  // Modern theme styles
  const containerClasses = 'min-h-screen p-6 space-y-6';
  const cardClasses = 'modern-card';
  const headingClasses = 'modern-heading';
  const subheadingClasses = 'modern-subheading';

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Check if we're in Tauri or web environment
      const isTauri = window.__TAURI__ !== undefined;
      
      if (isTauri) {
        // Use Tauri invoke for desktop app
        const [pricing, predictive, trends, autoStatus, marketData] = await Promise.all([
          invoke<PricingInsights>('get_pricing_insights'),
          // Use real predictive insights API call
          invoke<PredictiveInsights>('get_predictive_insights_summary'),
          invoke<MarketTrend[]>('get_market_trends', { daysBack: 90 }),
          invoke<AutoRepricingStatus>('get_auto_repricing_status').catch(() => null),
          invoke<MarketTrendData>('get_smart_market_trends').catch(() => null)
        ]);
        
        setPricingInsights(pricing);
        setPredictiveInsights(predictive);
        setMarketTrends(trends);
        setAutoRepricingStatus(autoStatus);
        setMarketTrendData(marketData);
      } else {
        // Use HTTP fetch for web app
        const [pricingResponse, predictiveResponse, trendsResponse, autoStatusResponse, marketDataResponse] = await Promise.all([
          fetch('http://localhost:8000/api/v1/pricing/insights'),
          fetch('http://localhost:8000/api/v1/analytics/insights/predictive'),
          fetch('http://localhost:8000/api/v1/analytics/trends/market?days_back=90'),
          fetch('http://localhost:8000/api/v1/pricing/smart/auto-repricing/status').catch(() => null),
          fetch('http://localhost:8000/api/v1/pricing/smart/market-trends').catch(() => null)
        ]);
        
        if (!pricingResponse.ok || !predictiveResponse.ok || !trendsResponse.ok) {
          throw new Error('Failed to fetch data from API');
        }
        
        const pricing = await pricingResponse.json();
        const predictive = await predictiveResponse.json();
        const trends = await trendsResponse.json();
        
        setPricingInsights(pricing);
        setPredictiveInsights(predictive);
        setMarketTrends(trends);
        
        // Smart pricing data (optional)
        if (autoStatusResponse && autoStatusResponse.ok) {
          setAutoRepricingStatus(await autoStatusResponse.json());
        }
        if (marketDataResponse && marketDataResponse.ok) {
          setMarketTrendData(await marketDataResponse.json());
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      console.error('Failed to fetch pricing/forecast data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const generateForecast = async () => {
    setIsGeneratingForecast(true);
    
    try {
      const request: ForecastRequest = {
        horizon_days: forecastDays,
        confidence_level: confidenceLevel,
        model: 'ensemble'
      };
      
      // Check if we're in Tauri or web environment
      const isTauri = window.__TAURI__ !== undefined;
      
      if (isTauri) {
        // Use Tauri invoke for desktop app
        const forecast = await invoke<ForecastAnalysis>('generate_sales_forecast', { request });
        setForecastResult(forecast);
      } else {
        // Use HTTP fetch for web app
        const response = await fetch('http://localhost:8000/api/v1/analytics/forecast/sales', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request)
        });
        
        if (!response.ok) {
          throw new Error('Failed to generate forecast');
        }
        
        const forecast = await response.json();
        setForecastResult(forecast);
      }
    } catch (err) {
      console.error('Failed to generate forecast:', err);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsGeneratingForecast(false);
    }
  };

  const optimizeInventoryPricing = async () => {
    setIsOptimizing(true);
    
    try {
      // Check if we're in Tauri or web environment
      const isTauri = window.__TAURI__ !== undefined;
      
      if (isTauri) {
        // Use Tauri invoke for desktop app
        const optimization = await invoke<SmartPricingOptimization>('optimize_inventory_pricing', { 
          strategy: selectedStrategy,
          limit: 50 
        });
        setSmartPricingResult(optimization);
      } else {
        // Use HTTP fetch for web app
        const response = await fetch(`http://localhost:8000/api/v1/pricing/smart/optimize-inventory?strategy=${selectedStrategy}&limit=50`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          }
        });
        
        if (!response.ok) {
          throw new Error('Failed to optimize pricing');
        }
        
        const optimization = await response.json();
        setSmartPricingResult(optimization);
      }
      
      // Refresh auto-repricing status after optimization
      await fetchAutoRepricingStatus();
    } catch (err) {
      console.error('Failed to optimize pricing:', err);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsOptimizing(false);
    }
  };

  const toggleAutoRepricing = async () => {
    try {
      const isTauri = window.__TAURI__ !== undefined;
      const newStatus = !autoRepricingStatus?.enabled;
      
      if (isTauri) {
        await invoke('toggle_auto_repricing', { enabled: newStatus });
      } else {
        const response = await fetch('http://localhost:8000/api/v1/pricing/smart/auto-repricing/toggle', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ enabled: newStatus })
        });
        
        if (!response.ok) {
          throw new Error('Failed to toggle auto-repricing');
        }
      }
      
      await fetchAutoRepricingStatus();
    } catch (err) {
      console.error('Failed to toggle auto-repricing:', err);
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const fetchAutoRepricingStatus = async () => {
    try {
      const isTauri = window.__TAURI__ !== undefined;
      
      if (isTauri) {
        const status = await invoke<AutoRepricingStatus>('get_auto_repricing_status');
        setAutoRepricingStatus(status);
      } else {
        const response = await fetch('http://localhost:8000/api/v1/pricing/smart/auto-repricing/status');
        if (response.ok) {
          setAutoRepricingStatus(await response.json());
        }
      }
    } catch (err) {
      console.error('Failed to fetch auto-repricing status:', err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR'
    }).format(value);
  };

  // Helper function to get forecast data regardless of response structure
  const getForecastData = (result: ForecastAnalysis) => {
    if (result.forecast) {
      return result.forecast;
    }
    // Direct response format
    return {
      target_id: result.target_id || '',
      target_type: result.target_type || '',
      predicted_sales: result.predicted_sales || 0,
      predicted_revenue: result.predicted_revenue || 0,
      confidence_interval_lower: result.confidence_interval_lower || 0,
      confidence_interval_upper: result.confidence_interval_upper || 0,
      model_used: result.model_used || '',
      trend: result.trend || 'stable'
    };
  };


  const getTrendIcon = (trend: string) => {
    switch (trend.toLowerCase()) {
      case 'increasing':
        return <TrendingUp className="w-4 h-4 text-green-400" />;
      case 'decreasing':
        return <TrendingUp className="w-4 h-4 rotate-180 text-red-400" />;
      default:
        return <Activity className="w-4 h-4 text-yellow-400" />;
    }
  };

  const getImpactStars = (impact: string, strength: number) => {
    let starCount = 1;
    
    if (impact.toLowerCase().includes('high') || strength > 0.7) {
      starCount = 3;
    } else if (impact.toLowerCase().includes('medium') || impact.toLowerCase().includes('moderate') || strength > 0.4) {
      starCount = 2;
    }
    
    return Array.from({ length: 3 }, (_, index) => (
      <Star 
        key={index}
        className={`w-3 h-3 ${
          index < starCount 
            ? 'text-yellow-400 fill-yellow-400'
            : 'text-gray-600'
        }`}
      />
    ));
  };

  const getMarketConditionColor = (condition: string) => {
    switch (condition.toLowerCase()) {
      case 'bullish':
        return 'text-green-400';
      case 'bearish':
        return 'text-red-400';
      case 'volatile':
        return 'text-orange-400';
      default:
        return 'text-blue-400';
    }
  };

  const getMarketConditionIcon = (condition: string) => {
    switch (condition.toLowerCase()) {
      case 'bullish':
        return <TrendingUp className="w-4 h-4 text-green-400" />;
      case 'bearish':
        return <TrendingDown className="w-4 h-4 text-red-400" />;
      case 'volatile':
        return <Activity className="w-4 h-4 text-orange-400" />;
      default:
        return <BarChart3 className="w-4 h-4 text-blue-400" />;
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-element">
          <div className="pulse-glow rounded-full w-20 h-20 mx-auto mb-6 flex items-center justify-center" style={{
            backgroundColor: 'rgba(127, 90, 240, 0.1)',
            border: '1px solid rgba(127, 90, 240, 0.2)'
          }}>
            <Brain className="w-12 h-12 animate-spin" style={{ color: '#7f5af0' }} />
          </div>
          <h2 className="heading-md mb-2">Loading AI Insights...</h2>
          <p className="body-lg">Analyzing pricing intelligence and forecasts</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen padding-section space-section fade-in">
      {/* Enhanced Header */}
      <div className="flex justify-between items-start mb-12">
        <div className="space-tight">
          <h1 className="heading-xl mb-2">AI Pricing & Forecasting</h1>
          <p className="body-lg" style={{ color: '#94a1b2' }}>
            AI-powered pricing optimization and sales forecasting
          </p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setShowSmartPricing(!showSmartPricing)}
            className="modern-button-secondary flex items-center space-x-3 transition-transform hover:scale-105"
            style={{
              background: showSmartPricing
                ? 'linear-gradient(135deg, #2cb67d 0%, #35c487 100%)'
                : 'rgba(44, 182, 125, 0.1)',
              color: showSmartPricing ? '#fffffe' : '#2cb67d',
              border: `1px solid ${showSmartPricing ? 'transparent' : 'rgba(44, 182, 125, 0.3)'}`
            }}
          >
            <Bot className="w-5 h-5" />
            <span>Smart Pricing</span>
          </button>
          <button
            onClick={fetchData}
            disabled={isLoading}
            className="modern-button flex items-center space-x-3 hover:scale-105 transition-transform"
            style={{
              background: 'linear-gradient(135deg, #7f5af0 0%, #8b66f5 100%)',
              color: '#fffffe'
            }}
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh Data</span>
          </button>
        </div>
      </div>

      {error ? (
        <div className={`${cardClasses} text-center`}>
          <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-red-400" />
          <p className="text-red-400 text-lg mb-4">{error}</p>
          <button 
            onClick={fetchData} 
            className="modern-button"
          >
            Retry
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Smart Pricing Section */}
          {showSmartPricing && (
            <div className="space-y-6">
              {/* Smart Pricing Controls */}
              <div className={`${cardClasses} p-6`}>
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-3">
                    <Bot className="w-6 h-6 text-purple-400" />
                    <h2 className={`${headingClasses} text-xl`}>
                      Smart Pricing Engine
                    </h2>
                  </div>
                  <div className="flex items-center space-x-3">
                    <select 
                      value={selectedStrategy}
                      onChange={(e) => setSelectedStrategy(e.target.value)}
                      className="modern-select text-sm"
                    >
                      <option value="profit_maximization">Profit Maximization</option>
                      <option value="market_competitive">Market Competitive</option>
                      <option value="volume_optimization">Volume Optimization</option>
                      <option value="margin_protection">Margin Protection</option>
                    </select>
                    <button 
                      onClick={optimizeInventoryPricing}
                      disabled={isOptimizing}
                      className={`modern-button flex items-center space-x-2 text-sm px-4 py-2 ${
                        isOptimizing ? 'opacity-50 cursor-not-allowed' : ''
                      }`}
                    >
                      <Zap className={`w-4 h-4 ${isOptimizing ? 'animate-pulse' : ''}`} />
                      <span>{isOptimizing ? 'Optimizing...' : 'Optimize Pricing'}</span>
                    </button>
                  </div>
                </div>

                {/* Auto-Repricing Status */}
                {autoRepricingStatus && (
                  <div className="mb-6 p-4 rounded-lg bg-gray-800 border border-blue-400/30">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-medium text-blue-400">Auto-Repricing Engine</h4>
                      <button 
                        onClick={toggleAutoRepricing}
                        className={`flex items-center space-x-2 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                          autoRepricingStatus.enabled 
                            ? 'bg-green-500/20 text-green-400 border border-green-400/30'
                            : 'bg-gray-600/20 text-gray-400 border border-gray-600/30'
                        }`}
                      >
                        {autoRepricingStatus.enabled ? (
                          <><Play className="w-3 h-3" /> Enabled</>
                        ) : (
                          <><Pause className="w-3 h-3" /> Disabled</>
                        )}
                      </button>
                    </div>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
                      <div>
                        <span className="text-gray-400">Items Repriced:</span>
                        <div className="font-semibold text-white mt-1">{autoRepricingStatus.items_repriced}</div>
                      </div>
                      <div>
                        <span className="text-gray-400">Strategy:</span>
                        <div className="font-semibold text-white mt-1 capitalize">{autoRepricingStatus.strategy}</div>
                      </div>
                      <div>
                        <span className="text-gray-400">Last Run:</span>
                        <div className="font-semibold text-white mt-1">
                          {autoRepricingStatus.last_run ? new Date(autoRepricingStatus.last_run).toLocaleDateString() : 'Never'}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-400">Rules Applied:</span>
                        <div className="font-semibold text-white mt-1">{autoRepricingStatus.rules_applied}</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Market Condition Indicator */}
                {marketTrendData && (
                  <div className="mb-6 p-4 rounded-lg bg-gray-800 border border-orange-400/30">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-medium text-orange-400">Current Market Conditions</h4>
                      <div className="flex items-center space-x-2">
                        {getMarketConditionIcon(marketTrendData.current_condition)}
                        <span className={`text-sm font-semibold ${getMarketConditionColor(marketTrendData.current_condition)}`}>
                          {marketTrendData.current_condition.toUpperCase()}
                        </span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
                      <div>
                        <span className="text-gray-400">Trend Strength:</span>
                        <div className="font-semibold text-white mt-1">{Math.round(marketTrendData.trend_strength * 100)}%</div>
                      </div>
                      <div>
                        <span className="text-gray-400">Volatility:</span>
                        <div className="font-semibold text-white mt-1 capitalize">{marketTrendData.volatility_level}</div>
                      </div>
                      <div>
                        <span className="text-gray-400">Momentum:</span>
                        <div className="font-semibold text-white mt-1 capitalize">{marketTrendData.price_momentum}</div>
                      </div>
                      <div>
                        <span className="text-gray-400">Confidence:</span>
                        <div className="font-semibold text-white mt-1">{Math.round(marketTrendData.confidence_score * 100)}%</div>
                      </div>
                    </div>
                    {marketTrendData.recommended_action && (
                      <div className="mt-3 p-2 rounded bg-orange-400/10 border border-orange-400/20">
                        <span className="text-xs text-orange-400 font-medium">Recommended Action: </span>
                        <span className="text-xs text-white">{marketTrendData.recommended_action}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Optimization Results */}
                {smartPricingResult && (
                  <div className="p-4 rounded-lg bg-green-500/10 border border-green-400/30">
                    <h4 className="text-sm font-medium mb-3 text-green-400">Latest Optimization Results</h4>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                      <div className="text-center">
                        <div className="text-lg font-bold text-white">{smartPricingResult.total_items_analyzed}</div>
                        <div className="text-xs text-gray-400">Items Analyzed</div>
                      </div>
                      <div className="text-center">
                        <div className="text-lg font-bold text-green-400">{smartPricingResult.items_optimized}</div>
                        <div className="text-xs text-gray-400">Items Optimized</div>
                      </div>
                      <div className="text-center">
                        <div className="text-lg font-bold text-green-400">+{formatCurrency(smartPricingResult.potential_profit_increase)}</div>
                        <div className="text-xs text-gray-400">Potential Profit</div>
                      </div>
                      <div className="text-center">
                        <div className="text-lg font-bold text-purple-400 capitalize">{smartPricingResult.market_conditions}</div>
                        <div className="text-xs text-gray-400">Market Condition</div>
                      </div>
                    </div>
                    
                    {smartPricingResult.recommendations.length > 0 && (
                      <div>
                        <h5 className="text-sm font-medium mb-2 text-green-400">Top Recommendations:</h5>
                        <div className="space-y-2">
                          {smartPricingResult.recommendations.slice(0, 3).map((rec, index) => (
                            <div key={index} className="flex items-center justify-between p-2 rounded bg-gray-800 text-xs">
                              <div className="flex-1 min-w-0">
                                <div className="font-medium text-white truncate">{rec.product_name}</div>
                                <div className="text-gray-400">
                                  {formatCurrency(rec.current_price)} → {formatCurrency(rec.recommended_price)}
                                </div>
                              </div>
                              <div className="text-right ml-2">
                                <div className="font-semibold text-green-400">+{formatCurrency(rec.profit_increase)}</div>
                                <div className="text-gray-400">{Math.round(rec.confidence * 100)}% confidence</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="modern-card px-6 py-3">
              <div className="flex items-center space-x-4">
                <div className="p-2 rounded-xl bg-green-500/10">
                  <Banknote className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <div className="text-xl font-bold modern-heading">
                    €{(pricingInsights?.summary.average_price || 0).toLocaleString()}
                  </div>
                  <div className="text-xs modern-subheading">
                    Average Price
                  </div>
                </div>
              </div>
            </div>
            
            <div className="modern-card px-6 py-3">
              <div className="flex items-center space-x-4">
                <div className="p-2 rounded-xl bg-blue-500/10">
                  <Target className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <div className="text-xl font-bold modern-heading">
                    {(pricingInsights?.summary.average_margin_percent || 0).toFixed(1)}%
                  </div>
                  <div className="text-xs modern-subheading">
                    Average Margin
                  </div>
                </div>
              </div>
            </div>
            
            <div className="modern-card px-6 py-3">
              <div className="flex items-center space-x-4">
                <div className="p-2 rounded-xl bg-orange-500/10">
                  <Activity className="w-5 h-5 text-orange-400" />
                </div>
                <div>
                  <div className="text-xl font-bold modern-heading">
                    €{(predictiveInsights?.business_metrics.revenue_90d || 0).toLocaleString()}
                  </div>
                  <div className="text-xs modern-subheading">
                    90d Revenue
                  </div>
                </div>
              </div>
            </div>
            
            <div className="modern-card px-6 py-3">
              <div className="flex items-center space-x-4">
                <div className="p-2 rounded-xl bg-purple-500/10">
                  <BarChart3 className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <div className="text-xl font-bold modern-heading">
                    {predictiveInsights?.business_metrics.active_products || 0}
                  </div>
                  <div className="text-xs modern-subheading">
                    Active Products
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Main Content Grid - Responsive */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Sales Forecast Generator - Left Column */}
            <div className={`${cardClasses} lg:col-span-4`}>
              <div className="flex items-center justify-between mb-6">
                <h2 className={`${headingClasses} text-xl`}>
                  AI Sales Forecast
                </h2>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-gray-300">
                    Forecast Days:
                  </label>
                  <select 
                    value={forecastDays}
                    onChange={(e) => setForecastDays(Number(e.target.value))}
                    className="modern-select w-24"
                  >
                    <option value={7}>7</option>
                    <option value={14}>14</option>
                    <option value={30}>30</option>
                    <option value={60}>60</option>
                    <option value={90}>90</option>
                  </select>
                </div>
                
                <button 
                  onClick={generateForecast}
                  disabled={isGeneratingForecast}
                  className={`modern-button w-full flex items-center justify-center space-x-2 py-3 ${isGeneratingForecast ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <Brain className={`w-4 h-4 ${isGeneratingForecast ? 'animate-spin' : ''}`} />
                  <span>{isGeneratingForecast ? 'Generating...' : 'Generate Forecast'}</span>
                </button>
              </div>

              {forecastResult && (
                <div className="mt-6 space-y-4">
                  <div className="p-4 rounded-lg bg-gray-800 border border-green-400/30">
                    <h4 className="text-lg font-medium mb-4 text-green-400">
                      Forecast Results
                    </h4>
                    <div className="space-y-3">
                      {(() => {
                        const forecast = getForecastData(forecastResult);
                        return (
                          <>
                            <div className="flex justify-between items-center">
                              <span className="text-sm text-gray-300">Predicted Sales:</span>
                              <span className="font-semibold text-green-400">
                                {Math.round(forecast.predicted_sales)}
                              </span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-sm text-gray-300">Predicted Revenue:</span>
                              <span className="font-semibold text-green-400">
                                {formatCurrency(forecast.predicted_revenue)}
                              </span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-sm text-gray-300">Trend:</span>
                              <div className="flex items-center space-x-2">
                                {getTrendIcon(forecast.trend)}
                                <span className="text-sm capitalize text-gray-300">
                                  {forecast.trend}
                                </span>
                              </div>
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Market Trends - Middle Column */}
            <div className={`${cardClasses} lg:col-span-4`}>
              <h2 className={`${headingClasses} text-xl mb-4`}>
                Market Trends
              </h2>
              <div className="space-y-3">
                {marketTrends && marketTrends.length > 0 ? (
                  marketTrends.slice(0, 4).map((trend, index) => (
                    <div key={index} className="p-3 rounded-lg bg-gray-800 border border-purple-400/30">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-purple-400">
                          {trend.period}
                        </span>
                        <div className="flex items-center space-x-2">
                          {getTrendIcon(trend.trend_direction)}
                          <div className="flex gap-0.5">
                            {getImpactStars(trend.forecast_impact, trend.strength)}
                          </div>
                        </div>
                      </div>
                      <div className="text-sm font-semibold mb-1 text-white">
                        {trend.trend_direction.charAt(0).toUpperCase() + trend.trend_direction.slice(1)}
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-400">
                          Strength: {Math.round(trend.strength * 100)}%
                        </span>
                        <span className="text-xs text-gray-500">
                          {trend.forecast_impact}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <TrendingUp className="w-10 h-10 mx-auto mb-3" />
                    <p className="text-sm">No trend data available</p>
                  </div>
                )}
                
                {/* Show count if more trends available */}
                {marketTrends && marketTrends.length > 4 && (
                  <div className="text-center pt-2 border-t border-gray-700 text-gray-400">
                    <span className="text-xs">
                      +{marketTrends.length - 4} more trends
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* AI Insights & Confidence - Right Column */}
            <div className={`${cardClasses} lg:col-span-4`}>
              <h3 className={`${headingClasses} text-xl mb-6`}>
                AI Insights
              </h3>
              
              {/* Confidence Score */}
              <div className="text-center mb-8">
                <div className="relative w-24 h-24 mx-auto mb-4">
                  <div className="absolute inset-0 rounded-full opacity-20 bg-gradient-to-r from-purple-500 via-yellow-400 to-green-400"></div>
                  <div className="absolute inset-2 rounded-full flex items-center justify-center bg-gray-800">
                    <div className="text-center">
                      <div className="text-xl font-bold text-purple-400">
                        {Math.round((predictiveInsights?.confidence_score || 0.7) * 100)}%
                      </div>
                    </div>
                  </div>
                </div>
                <p className="text-sm text-gray-400">
                  AI Confidence
                </p>
              </div>
              
              {/* Insights Lists */}
              <div className="space-y-6">
                <div>
                  <h4 className="text-lg font-semibold mb-3 text-green-400">
                    Growth Opportunities
                  </h4>
                  <div className="space-y-2">
                    {predictiveInsights?.growth_opportunities.slice(0, 3).map((opportunity, index) => (
                      <div key={index} className="flex items-start gap-3">
                        <Zap className="w-4 h-4 mt-0.5 flex-shrink-0 text-green-400" />
                        <span className="text-sm text-gray-300">
                          {opportunity}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div>
                  <h4 className="text-lg font-semibold mb-3 text-yellow-400">
                    Recommendations
                  </h4>
                  <div className="space-y-2">
                    {predictiveInsights?.recommendations.slice(0, 3).map((rec, index) => (
                      <div key={index} className="flex items-start gap-3">
                        <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-yellow-400" />
                        <span className="text-sm text-gray-300">
                          {rec}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PricingForecast;