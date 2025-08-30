import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { 
  TrendingUp, 
  DollarSign, 
  Target, 
  Brain, 
  BarChart3, 
  Activity,
  Zap,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Info
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
  forecast: {
    target_id: string;
    target_type: string;
    predicted_sales: number;
    predicted_revenue: number;
    confidence_interval_lower: number;
    confidence_interval_upper: number;
    model_used: string;
    trend: string;
  };
  key_insights: string[];
  recommendations: string[];
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

  const getTrendIcon = (trend: string) => {
    switch (trend.toLowerCase()) {
      case 'increasing':
        return <TrendingUp className="w-4 h-4 text-retro-green" />;
      case 'decreasing':
        return <TrendingUp className="w-4 h-4 text-retro-magenta rotate-180" />;
      default:
        return <Activity className="w-4 h-4 text-retro-yellow" />;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Brain className="w-16 h-16 text-retro-cyan animate-pulse mx-auto mb-4" />
          <p className="text-retro-cyan font-mono">LOADING AI INSIGHTS...</p>
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
            PRICING & FORECAST
          </h1>
          <p className="text-retro-cyan/70 font-mono mt-1">
            AI-powered pricing optimization and sales forecasting
          </p>
        </div>
        <button 
          onClick={fetchData}
          className="retro-button flex items-center space-x-2"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>REFRESH</span>
        </button>
      </div>

      {error ? (
        <div className="retro-card text-center">
          <AlertTriangle className="w-8 h-8 text-retro-magenta mx-auto mb-2" />
          <p className="text-retro-magenta font-mono">{error}</p>
          <button onClick={fetchData} className="retro-button mt-4">RETRY</button>
        </div>
      ) : (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="retro-card text-center">
              <DollarSign className="w-12 h-12 text-retro-green mx-auto mb-3" />
              <p className="text-sm font-mono uppercase tracking-wider opacity-70">Avg Price</p>
              <p className="text-3xl font-retro font-bold text-retro-green mt-2">
                {formatCurrency(pricingInsights?.summary.average_price || 0)}
              </p>
            </div>
            
            <div className="retro-card text-center">
              <Target className="w-12 h-12 text-retro-cyan mx-auto mb-3" />
              <p className="text-sm font-mono uppercase tracking-wider opacity-70">Avg Margin</p>
              <p className="text-3xl font-retro font-bold text-retro-cyan mt-2">
                {(pricingInsights?.summary.average_margin_percent || 0).toFixed(1)}%
              </p>
            </div>
            
            <div className="retro-card text-center">
              <Activity className="w-12 h-12 text-retro-yellow mx-auto mb-3" />
              <p className="text-sm font-mono uppercase tracking-wider opacity-70">90d Revenue</p>
              <p className="text-3xl font-retro font-bold text-retro-yellow mt-2">
                {formatCurrency(predictiveInsights?.business_metrics.revenue_90d || 0)}
              </p>
            </div>
            
            <div className="retro-card text-center">
              <BarChart3 className="w-12 h-12 text-retro-magenta mx-auto mb-3" />
              <p className="text-sm font-mono uppercase tracking-wider opacity-70">Active Products</p>
              <p className="text-3xl font-retro font-bold text-retro-magenta mt-2">
                {predictiveInsights?.business_metrics.active_products || 0}
              </p>
            </div>
          </div>

          {/* Sales Forecast Generator */}
          <div className="retro-card">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-retro text-retro-cyan">AI SALES FORECAST</h2>
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <label className="text-sm font-mono text-retro-cyan">Days:</label>
                  <select 
                    value={forecastDays}
                    onChange={(e) => setForecastDays(Number(e.target.value))}
                    className="retro-input w-20"
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
                  className={`retro-button flex items-center space-x-2 ${isGeneratingForecast ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <Brain className={`w-4 h-4 ${isGeneratingForecast ? 'animate-spin' : ''}`} />
                  <span>{isGeneratingForecast ? 'GENERATING...' : 'GENERATE FORECAST'}</span>
                </button>
              </div>
            </div>

            {forecastResult && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-4 bg-dark-surface border border-retro-green/30 rounded">
                  <h3 className="text-lg font-mono text-retro-green mb-4">Forecast Results</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="font-mono text-sm">Predicted Sales:</span>
                      <span className="font-retro text-retro-green">
                        {Math.round(forecastResult.forecast.predicted_sales)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-mono text-sm">Predicted Revenue:</span>
                      <span className="font-retro text-retro-green">
                        {formatCurrency(forecastResult.forecast.predicted_revenue)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-mono text-sm">Confidence Range:</span>
                      <span className="font-mono text-retro-cyan text-xs">
                        {formatCurrency(forecastResult.forecast.confidence_interval_lower)} - {formatCurrency(forecastResult.forecast.confidence_interval_upper)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-mono text-sm">Trend:</span>
                      <div className="flex items-center space-x-2">
                        {getTrendIcon(forecastResult.forecast.trend)}
                        <span className="font-mono text-sm capitalize">{forecastResult.forecast.trend}</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="p-4 bg-dark-surface border border-retro-cyan/30 rounded">
                  <h3 className="text-lg font-mono text-retro-cyan mb-4">Key Insights</h3>
                  <ul className="space-y-2 text-sm font-mono text-retro-cyan/80">
                    {forecastResult.key_insights.slice(0, 4).map((insight, index) => (
                      <li key={index} className="flex items-start space-x-2">
                        <Info className="w-3 h-3 mt-0.5 text-retro-yellow flex-shrink-0" />
                        <span>{insight}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Market Trends */}
          <div className="retro-card">
            <h2 className="text-xl font-retro text-retro-cyan mb-6">MARKET TRENDS</h2>
            {marketTrends && marketTrends.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {marketTrends.slice(0, 6).map((trend, index) => (
                  <div key={index} className="p-4 bg-dark-surface border border-retro-cyan/30 rounded">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-sm text-retro-cyan uppercase">{trend.period}</span>
                      {getTrendIcon(trend.trend_direction)}
                    </div>
                    <div className="text-lg font-retro text-retro-yellow mb-1">
                      {trend.trend_direction.toUpperCase()}
                    </div>
                    <div className="text-xs text-retro-cyan/70 mb-2">
                      Strength: {Math.round(trend.strength * 100)}%
                    </div>
                    <div className="text-xs font-mono text-retro-cyan/60">
                      Impact: {trend.forecast_impact}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-retro-cyan/50">
                <TrendingUp className="w-12 h-12 mx-auto mb-2" />
                <p className="font-mono">No trend data available</p>
              </div>
            )}
          </div>

          {/* AI Insights & Recommendations */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="retro-card">
              <h3 className="text-lg font-retro text-retro-cyan mb-4">PREDICTIVE INSIGHTS</h3>
              <div className="space-y-2 font-mono text-sm">
                {predictiveInsights?.predictive_insights.slice(0, 5).map((insight, index) => (
                  <div key={index} className="flex items-start space-x-2">
                    <Brain className="w-3 h-3 mt-0.5 text-retro-cyan flex-shrink-0" />
                    <span className="text-retro-cyan/80">{insight}</span>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="retro-card">
              <h3 className="text-lg font-retro text-retro-cyan mb-4">GROWTH OPPORTUNITIES</h3>
              <div className="space-y-2 font-mono text-sm">
                {predictiveInsights?.growth_opportunities.slice(0, 5).map((opportunity, index) => (
                  <div key={index} className="flex items-start space-x-2">
                    <Zap className="w-3 h-3 mt-0.5 text-retro-green flex-shrink-0" />
                    <span className="text-retro-green/80">{opportunity}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Risk Factors & Recommendations */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="retro-card">
              <h3 className="text-lg font-retro text-retro-magenta mb-4">RISK FACTORS</h3>
              <div className="space-y-2 font-mono text-sm">
                {predictiveInsights?.risk_factors.slice(0, 4).map((risk, index) => (
                  <div key={index} className="flex items-start space-x-2">
                    <AlertTriangle className="w-3 h-3 mt-0.5 text-retro-magenta flex-shrink-0" />
                    <span className="text-retro-magenta/80">{risk}</span>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="retro-card">
              <h3 className="text-lg font-retro text-retro-yellow mb-4">RECOMMENDATIONS</h3>
              <div className="space-y-2 font-mono text-sm">
                {predictiveInsights?.recommendations.slice(0, 4).map((rec, index) => (
                  <div key={index} className="flex items-start space-x-2">
                    <CheckCircle className="w-3 h-3 mt-0.5 text-retro-yellow flex-shrink-0" />
                    <span className="text-retro-yellow/80">{rec}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* AI Confidence Score */}
          <div className="retro-card text-center">
            <h3 className="text-lg font-retro text-retro-cyan mb-4">AI CONFIDENCE SCORE</h3>
            <div className="relative w-32 h-32 mx-auto">
              <div className="absolute inset-0 bg-gradient-to-r from-retro-magenta via-retro-yellow to-retro-green rounded-full opacity-20"></div>
              <div className="absolute inset-2 bg-dark-card rounded-full flex items-center justify-center">
                <div className="text-center">
                  <div className="text-2xl font-retro text-retro-cyan">
                    {Math.round((predictiveInsights?.confidence_score || 0.7) * 100)}%
                  </div>
                  <div className="text-xs font-mono text-retro-cyan/70">CONFIDENCE</div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default PricingForecast;