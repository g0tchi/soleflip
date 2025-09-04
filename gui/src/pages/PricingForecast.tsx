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
  Star
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

const PricingForecast = () => {
  const [pricingInsights, setPricingInsights] = useState<PricingInsights | null>(null);
  const [predictiveInsights, setPredictiveInsights] = useState<PredictiveInsights | null>(null);
  const [marketTrends, setMarketTrends] = useState<MarketTrend[]>([]);
  const [forecastResult, setForecastResult] = useState<ForecastAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
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
        const [pricing, predictive, trends] = await Promise.all([
          invoke<PricingInsights>('get_pricing_insights'),
          invoke<PredictiveInsights>('get_predictive_insights'),
          invoke<MarketTrend[]>('get_market_trends', { daysBack: 90 })
        ]);
        
        setPricingInsights(pricing);
        setPredictiveInsights(predictive);
        setMarketTrends(trends);
      } else {
        // Use HTTP fetch for web app
        const [pricingResponse, predictiveResponse, trendsResponse] = await Promise.all([
          fetch('http://localhost:8000/api/v1/pricing/insights'),
          fetch('http://localhost:8000/api/v1/analytics/insights/predictive'),
          fetch('http://localhost:8000/api/v1/analytics/trends/market?days_back=90')
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

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Brain className="w-16 h-16 animate-pulse mx-auto mb-4 text-purple-500" />
          <p className={`${headingClasses} text-xl`}>
            Loading AI Insights...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={containerClasses}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
        <div>
          <h1 className={`${headingClasses} text-3xl lg:text-4xl mb-2`}>
            AI Pricing & Forecasting
          </h1>
          <p className={`${subheadingClasses} text-base lg:text-lg`}>
            AI-powered pricing optimization and sales forecasting
          </p>
        </div>
        <button 
          onClick={fetchData}
          disabled={isLoading}
          className="modern-button-outline flex items-center space-x-2 text-sm px-4 py-2"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
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