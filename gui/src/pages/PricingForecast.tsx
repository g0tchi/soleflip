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
import { useTheme } from '../contexts/ThemeContext';

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
  const { theme } = useTheme();
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

  // Theme-aware styles
  const isModernTheme = theme === 'happy-hues-modern';
  const containerClasses = isModernTheme 
    ? 'min-h-screen p-6 space-y-6' 
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

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const [pricing, predictive, trends] = await Promise.all([
        invoke<PricingInsights>('get_pricing_insights'),
        invoke<PredictiveInsights>('get_predictive_insights'),
        invoke<MarketTrend[]>('get_market_trends', { daysBack: 90 })
      ]);
      
      setPricingInsights(pricing);
      setPredictiveInsights(predictive);
      setMarketTrends(trends);
    } catch (err) {
      setError(err as string);
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
      
      const forecast = await invoke<ForecastAnalysis>('generate_sales_forecast', { request });
      setForecastResult(forecast);
    } catch (err) {
      console.error('Failed to generate forecast:', err);
      setError(err as string);
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
        return <TrendingUp className={`w-4 h-4 ${isModernTheme ? 'text-green-400' : 'text-retro-green'}`} />;
      case 'decreasing':
        return <TrendingUp className={`w-4 h-4 rotate-180 ${isModernTheme ? 'text-red-400' : 'text-retro-magenta'}`} />;
      default:
        return <Activity className={`w-4 h-4 ${isModernTheme ? 'text-yellow-400' : 'text-retro-yellow'}`} />;
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
            ? (isModernTheme ? 'text-yellow-400 fill-yellow-400' : 'text-retro-yellow fill-retro-yellow')
            : (isModernTheme ? 'text-gray-600' : 'text-retro-cyan/20')
        }`}
      />
    ));
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Brain className={`w-16 h-16 animate-pulse mx-auto mb-4 ${
            isModernTheme ? 'text-purple-500' : 'text-retro-cyan'
          }`} />
          <p className={`${headingClasses} text-xl`}>
            {isModernTheme ? 'Loading AI Insights...' : 'LOADING AI INSIGHTS...'}
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
            {isModernTheme ? 'AI Pricing & Forecasting' : 'PRICING & FORECAST'}
          </h1>
          <p className={`${subheadingClasses} text-base lg:text-lg`}>
            AI-powered pricing optimization and sales forecasting
          </p>
        </div>
        <button 
          onClick={fetchData}
          disabled={isLoading}
          className={`${isModernTheme ? 'modern-button-outline' : 'retro-button'} flex items-center gap-2 text-sm px-4 py-2`}
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>{isModernTheme ? 'Refresh' : 'REFRESH'}</span>
        </button>
      </div>

      {error ? (
        <div className={`${cardClasses} text-center`}>
          <AlertTriangle className={`w-12 h-12 mx-auto mb-4 ${
            isModernTheme ? 'text-red-400' : 'text-retro-magenta'
          }`} />
          <p className={`${isModernTheme ? 'text-red-400' : 'text-retro-magenta font-mono'} text-lg mb-4`}>{error}</p>
          <button 
            onClick={fetchData} 
            className={`${isModernTheme ? 'modern-button' : 'retro-button'}`}
          >
            {isModernTheme ? 'Retry' : 'RETRY'}
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className={`${cardClasses} text-center p-6`}>
              <Banknote className={`w-12 h-12 mx-auto mb-4 ${
                isModernTheme ? 'text-green-400' : 'text-retro-green'
              }`} />
              <p className={`text-sm ${isModernTheme ? 'text-gray-400' : 'font-mono uppercase tracking-wider'} opacity-70 mb-2`}>
                {isModernTheme ? 'Average Price' : 'AVG PRICE'}
              </p>
              <p className={`text-2xl lg:text-3xl font-bold ${
                isModernTheme ? 'text-green-400' : 'font-retro text-retro-green'
              }`}>
                €{(pricingInsights?.summary.average_price || 0).toLocaleString()}
              </p>
            </div>
            
            <div className={`${cardClasses} text-center p-6`}>
              <Target className={`w-12 h-12 mx-auto mb-4 ${
                isModernTheme ? 'text-blue-400' : 'text-retro-cyan'
              }`} />
              <p className={`text-sm ${isModernTheme ? 'text-gray-400' : 'font-mono uppercase tracking-wider'} opacity-70 mb-2`}>
                {isModernTheme ? 'Average Margin' : 'AVG MARGIN'}
              </p>
              <p className={`text-2xl lg:text-3xl font-bold ${
                isModernTheme ? 'text-blue-400' : 'font-retro text-retro-cyan'
              }`}>
                {(pricingInsights?.summary.average_margin_percent || 0).toFixed(1)}%
              </p>
            </div>
            
            <div className={`${cardClasses} text-center p-6`}>
              <Activity className={`w-12 h-12 mx-auto mb-4 ${
                isModernTheme ? 'text-yellow-400' : 'text-retro-yellow'
              }`} />
              <p className={`text-sm ${isModernTheme ? 'text-gray-400' : 'font-mono uppercase tracking-wider'} opacity-70 mb-2`}>
                {isModernTheme ? '90d Revenue' : '90D REVENUE'}
              </p>
              <p className={`text-2xl lg:text-3xl font-bold ${
                isModernTheme ? 'text-yellow-400' : 'font-retro text-retro-yellow'
              }`}>
                €{(predictiveInsights?.business_metrics.revenue_90d || 0).toLocaleString()}
              </p>
            </div>
            
            <div className={`${cardClasses} text-center p-6`}>
              <BarChart3 className={`w-12 h-12 mx-auto mb-4 ${
                isModernTheme ? 'text-purple-400' : 'text-retro-magenta'
              }`} />
              <p className={`text-sm ${isModernTheme ? 'text-gray-400' : 'font-mono uppercase tracking-wider'} opacity-70 mb-2`}>
                {isModernTheme ? 'Active Products' : 'ACTIVE PRODUCTS'}
              </p>
              <p className={`text-2xl lg:text-3xl font-bold ${
                isModernTheme ? 'text-purple-400' : 'font-retro text-retro-magenta'
              }`}>
                {predictiveInsights?.business_metrics.active_products || 0}
              </p>
            </div>
          </div>

          {/* Main Content Grid - Responsive */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Sales Forecast Generator - Left Column */}
            <div className={`${cardClasses} lg:col-span-4`}>
              <div className="flex items-center justify-between mb-6">
                <h2 className={`${headingClasses} text-xl`}>
                  {isModernTheme ? 'AI Sales Forecast' : 'AI SALES FORECAST'}
                </h2>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className={`text-sm font-medium ${isModernTheme ? 'text-gray-300' : 'font-mono text-retro-cyan'}`}>
                    Forecast Days:
                  </label>
                  <select 
                    value={forecastDays}
                    onChange={(e) => setForecastDays(Number(e.target.value))}
                    className={`${isModernTheme ? 'modern-select' : 'retro-input'} w-24`}
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
                  className={`${isModernTheme ? 'modern-button' : 'retro-button'} w-full flex items-center justify-center gap-2 py-3 ${isGeneratingForecast ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <Brain className={`w-4 h-4 ${isGeneratingForecast ? 'animate-spin' : ''}`} />
                  <span>{isGeneratingForecast 
                    ? (isModernTheme ? 'Generating...' : 'GENERATING...') 
                    : (isModernTheme ? 'Generate Forecast' : 'GENERATE FORECAST')
                  }</span>
                </button>
              </div>

              {forecastResult && (
                <div className="mt-6 space-y-4">
                  <div className={`p-4 rounded-lg ${isModernTheme ? 'bg-gray-800 border border-green-400/30' : 'bg-dark-surface border border-retro-green/30'}`}>
                    <h4 className={`text-lg font-medium mb-4 ${isModernTheme ? 'text-green-400' : 'font-mono text-retro-green'}`}>
                      Forecast Results
                    </h4>
                    <div className="space-y-3">
                      {(() => {
                        const forecast = getForecastData(forecastResult);
                        return (
                          <>
                            <div className="flex justify-between items-center">
                              <span className={`text-sm ${isModernTheme ? 'text-gray-300' : 'font-mono'}`}>Predicted Sales:</span>
                              <span className={`font-semibold ${isModernTheme ? 'text-green-400' : 'font-retro text-retro-green'}`}>
                                {Math.round(forecast.predicted_sales)}
                              </span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className={`text-sm ${isModernTheme ? 'text-gray-300' : 'font-mono'}`}>Predicted Revenue:</span>
                              <span className={`font-semibold ${isModernTheme ? 'text-green-400' : 'font-retro text-retro-green'}`}>
                                {formatCurrency(forecast.predicted_revenue)}
                              </span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className={`text-sm ${isModernTheme ? 'text-gray-300' : 'font-mono'}`}>Trend:</span>
                              <div className="flex items-center gap-2">
                                {getTrendIcon(forecast.trend)}
                                <span className={`text-sm capitalize ${isModernTheme ? 'text-gray-300' : 'font-mono'}`}>
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
                {isModernTheme ? 'Market Trends' : 'MARKET TRENDS'}
              </h2>
              <div className="space-y-3">
                {marketTrends && marketTrends.length > 0 ? (
                  marketTrends.slice(0, 4).map((trend, index) => (
                    <div key={index} className={`p-3 rounded-lg ${isModernTheme ? 'bg-gray-800 border border-purple-400/30' : 'bg-dark-surface border border-retro-cyan/30'}`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className={`text-xs font-medium ${isModernTheme ? 'text-purple-400' : 'font-mono text-retro-cyan'}`}>
                          {trend.period}
                        </span>
                        <div className="flex items-center gap-2">
                          {getTrendIcon(trend.trend_direction)}
                          <div className="flex gap-0.5">
                            {getImpactStars(trend.forecast_impact, trend.strength)}
                          </div>
                        </div>
                      </div>
                      <div className={`text-sm font-semibold mb-1 ${isModernTheme ? 'text-white' : 'font-retro text-retro-yellow'}`}>
                        {trend.trend_direction.charAt(0).toUpperCase() + trend.trend_direction.slice(1)}
                      </div>
                      <div className="flex justify-between items-center">
                        <span className={`text-xs ${isModernTheme ? 'text-gray-400' : 'text-retro-cyan/70'}`}>
                          Strength: {Math.round(trend.strength * 100)}%
                        </span>
                        <span className={`text-xs ${isModernTheme ? 'text-gray-500' : 'text-retro-cyan/50 font-mono'}`}>
                          {trend.forecast_impact}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className={`text-center py-8 ${isModernTheme ? 'text-gray-500' : 'text-retro-cyan/50'}`}>
                    <TrendingUp className="w-10 h-10 mx-auto mb-3" />
                    <p className={`text-sm ${isModernTheme ? '' : 'font-mono'}`}>No trend data available</p>
                  </div>
                )}
                
                {/* Show count if more trends available */}
                {marketTrends && marketTrends.length > 4 && (
                  <div className={`text-center pt-2 border-t ${isModernTheme ? 'border-gray-700 text-gray-400' : 'border-retro-cyan/20 text-retro-cyan/60'}`}>
                    <span className={`text-xs ${isModernTheme ? '' : 'font-mono'}`}>
                      +{marketTrends.length - 4} more trends
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* AI Insights & Confidence - Right Column */}
            <div className={`${cardClasses} lg:col-span-4`}>
              <h3 className={`${headingClasses} text-xl mb-6`}>
                {isModernTheme ? 'AI Insights' : 'AI INSIGHTS'}
              </h3>
              
              {/* Confidence Score */}
              <div className="text-center mb-8">
                <div className="relative w-24 h-24 mx-auto mb-4">
                  <div className={`absolute inset-0 rounded-full opacity-20 ${
                    isModernTheme 
                      ? 'bg-gradient-to-r from-purple-500 via-yellow-400 to-green-400' 
                      : 'bg-gradient-to-r from-retro-magenta via-retro-yellow to-retro-green'
                  }`}></div>
                  <div className={`absolute inset-2 rounded-full flex items-center justify-center ${
                    isModernTheme ? 'bg-gray-800' : 'bg-dark-card'
                  }`}>
                    <div className="text-center">
                      <div className={`text-xl font-bold ${isModernTheme ? 'text-purple-400' : 'font-retro text-retro-cyan'}`}>
                        {Math.round((predictiveInsights?.confidence_score || 0.7) * 100)}%
                      </div>
                    </div>
                  </div>
                </div>
                <p className={`text-sm ${isModernTheme ? 'text-gray-400' : 'font-mono text-retro-cyan/70'}`}>
                  {isModernTheme ? 'AI Confidence' : 'AI CONFIDENCE'}
                </p>
              </div>
              
              {/* Insights Lists */}
              <div className="space-y-6">
                <div>
                  <h4 className={`text-lg font-semibold mb-3 ${isModernTheme ? 'text-green-400' : 'text-retro-green font-mono'}`}>
                    Growth Opportunities
                  </h4>
                  <div className="space-y-2">
                    {predictiveInsights?.growth_opportunities.slice(0, 3).map((opportunity, index) => (
                      <div key={index} className="flex items-start gap-3">
                        <Zap className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isModernTheme ? 'text-green-400' : 'text-retro-green'}`} />
                        <span className={`text-sm ${isModernTheme ? 'text-gray-300' : 'text-retro-green/80 font-mono'}`}>
                          {opportunity}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div>
                  <h4 className={`text-lg font-semibold mb-3 ${isModernTheme ? 'text-yellow-400' : 'text-retro-yellow font-mono'}`}>
                    Recommendations
                  </h4>
                  <div className="space-y-2">
                    {predictiveInsights?.recommendations.slice(0, 3).map((rec, index) => (
                      <div key={index} className="flex items-start gap-3">
                        <CheckCircle className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isModernTheme ? 'text-yellow-400' : 'text-retro-yellow'}`} />
                        <span className={`text-sm ${isModernTheme ? 'text-gray-300' : 'text-retro-yellow/80 font-mono'}`}>
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