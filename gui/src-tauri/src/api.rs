use reqwest::Client;
use serde::{Deserialize, Deserializer, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use uuid::Uuid;
use chrono::{DateTime, Utc};
use crate::commands::{StockXListingRequest, StockXListingResponse};


#[derive(Debug, Clone)]
pub struct ApiClient {
    client: Client,
    base_url: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ApiResponse<T> {
    pub data: Option<T>,
    pub error: Option<String>,
    pub status: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HealthStatus {
    pub status: String,
    pub timestamp: String,
    pub version: String,
    pub environment: String,
    pub uptime_seconds: u64,
    pub checks_summary: HashMap<String, String>,
    pub components: HashMap<String, Value>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct InventoryItem {
    pub id: Uuid,
    pub product_id: Option<Uuid>,
    pub product_name: String,
    pub brand_name: Option<String>,
    pub category_name: Option<String>,
    pub size: String,
    pub quantity: i32,
    pub purchase_price: Option<f64>,
    pub purchase_date: Option<String>,
    pub supplier: String,
    pub status: String,
    pub notes: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}


#[derive(Debug, Serialize, Deserialize)]
pub struct ProductStats {
    pub total_products: i64,
    #[serde(rename = "total_inventory_value")]
    pub total_value: f64,
    pub total_brands: i64,
    #[serde(default)]
    pub avg_profit_margin: f64,
    pub top_brands: Vec<BrandStats>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BrandStats {
    pub name: String,
    pub total_products: i64,
    pub total_items: i64,
    pub avg_price: f64,
    pub total_value: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ImportRequest {
    pub from_date: String,
    pub to_date: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ImportResponse {
    pub status: String,
    pub message: String,
    pub batch_id: Uuid,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ImportStatus {
    pub id: Uuid,
    pub source_type: String,
    pub status: String,
    pub progress: f32,
    pub records_processed: i32,
    pub records_failed: i32,
    pub created_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DashboardMetrics {
    pub total_inventory_value: f64,
    pub monthly_sales: f64,
    pub profit_margin: f64,
    pub active_listings: i64,
    pub pending_imports: i64,
    pub recent_transactions: Vec<Value>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ApiDashboardMetrics {
    pub timestamp: String,
    pub inventory: InventoryMetrics,
    pub sales: SalesMetrics,
    pub system: SystemMetrics,
    pub performance: PerformanceMetrics,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct InventoryMetrics {
    pub total_items: i64,
    pub items_in_stock: i64,
    pub items_sold: i64,
    pub items_listed: i64,
    pub total_inventory_value: f64,
    pub average_purchase_price: f64,
    pub top_brands: Vec<Value>,
    pub status_breakdown: HashMap<String, Value>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SalesMetrics {
    pub recent_activity: Vec<Value>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SystemMetrics {
    pub status: String,
    pub uptime_seconds: f64,  // Changed to f64 to handle floating point values
    pub environment: String,
    pub version: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PerformanceMetrics {
    pub total_requests: i64,
    pub error_rate: f64,
    pub avg_response_time: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct EnrichmentStats {
    pub completed: i64,
    pub missing: i64,
    pub completion_percentage: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct EnrichmentStatusResponse {
    pub timestamp: String,
    pub total_products: i64,
    pub enrichment_stats: EnrichmentStatsBreakdown,
    pub overall_completion: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct EnrichmentStatsBreakdown {
    pub sku: EnrichmentStats,
    pub description: EnrichmentStats,
    pub retail_price: EnrichmentStats,
    pub release_date: EnrichmentStats,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct EnrichmentResponse {
    pub message: String,
    pub target_products: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PricingRequest {
    pub product_id: String,
    pub inventory_id: Option<String>,
    pub strategy: Option<String>,
    pub target_margin: Option<f64>,
    pub condition: String,
    pub size: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PricingRecommendation {
    pub product_id: String,
    pub suggested_price: f64,
    pub strategy_used: String,
    pub confidence_score: f64,
    pub margin_percent: f64,
    pub markup_percent: f64,
    pub reasoning: Vec<String>,
    pub market_position: Option<String>,
    pub price_range: Option<HashMap<String, f64>>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct MarketAnalysis {
    pub product_id: String,
    pub current_market_price: Option<f64>,
    pub price_trend: String,
    pub market_position: String,
    pub competitor_count: i32,
    pub demand_score: f64,
    pub supply_score: f64,
    pub recommended_action: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PricingInsights {
    pub timestamp: String,
    pub summary: PricingInsightsSummary,
    pub recommendations: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PricingInsightsSummary {
    pub total_products_analyzed: i32,
    pub average_price: f64,
    pub average_margin_percent: f64,
    pub total_price_updates: i32,
    pub recent_updates_30d: i32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ForecastRequest {
    pub product_id: Option<String>,
    pub brand_id: Option<String>,
    pub category_id: Option<String>,
    pub horizon_days: i32,
    pub model: Option<String>,
    pub confidence_level: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SalesForecast {
    pub target_id: String,
    pub target_type: String,
    pub forecast_date: String,
    pub horizon_days: i32,
    pub predicted_sales: f64,
    pub predicted_revenue: f64,
    pub confidence_interval_lower: f64,
    pub confidence_interval_upper: f64,
    pub model_used: String,
    pub accuracy_score: Option<f64>,
    pub trend: String,
    pub seasonality_factor: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ForecastAnalysis {
    pub forecast: SalesForecast,
    pub historical_data: Vec<HashMap<String, Value>>,
    pub key_insights: Vec<String>,
    pub recommendations: Vec<String>,
    pub model_performance: HashMap<String, Value>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct MarketTrend {
    pub period: String,
    pub trend_direction: String,
    pub strength: f64,
    pub key_drivers: Vec<String>,
    pub forecast_impact: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PredictiveInsights {
    pub timestamp: String,
    pub business_metrics: BusinessMetrics,
    pub predictive_insights: Vec<String>,
    pub growth_opportunities: Vec<String>,
    pub risk_factors: Vec<String>,
    pub recommendations: Vec<String>,
    pub confidence_score: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BusinessMetrics {
    pub transactions_90d: i32,
    pub revenue_90d: f64,
    pub avg_transaction_value: f64,
    pub active_products: i32,
    pub active_brands: i32,
}

// Smart Pricing Types
#[derive(Debug, Serialize, Deserialize)]
pub struct SmartPricingOptimization {
    pub total_items_analyzed: i32,
    pub items_optimized: i32,
    pub potential_profit_increase: f64,
    pub pricing_strategy: String,
    pub market_conditions: String,
    pub timestamp: String,
    pub recommendations: Vec<PricingOptimizationRecommendation>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PricingOptimizationRecommendation {
    pub product_name: String,
    pub current_price: f64,
    pub recommended_price: f64,
    pub profit_increase: f64,
    pub confidence: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AutoRepricingStatus {
    pub enabled: bool,
    pub last_run: Option<String>,
    pub items_repriced: i32,
    pub strategy: String,
    pub next_run: Option<String>,
    pub rules_applied: i32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct MarketTrendData {
    pub current_condition: String,
    pub trend_strength: f64,
    pub volatility_level: String,
    pub price_momentum: String,
    pub recommended_action: String,
    pub confidence_score: f64,
    pub key_insights: Vec<String>,
}

// Auto-Listing Types
#[derive(Debug, Serialize, Deserialize)]
pub struct AutoListingStatus {
    pub enabled: bool,
    pub total_rules: i32,
    pub active_rules: i32,
    pub last_run: Option<String>,
    pub next_scheduled_run: Option<String>,
    pub items_processed_today: i32,
    pub items_listed_today: i32,
    pub success_rate_percent: f64,
    pub rules: Vec<ListingRule>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ListingRule {
    pub name: String,
    pub active: bool,
    pub priority: i32,
    pub conditions_count: i32,
    pub items_matched_today: Option<i32>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AutoListingExecution {
    pub execution_id: String,
    pub started_at: String,
    pub max_items: i32,
    pub dry_run: bool,
    pub items_evaluated: i32,
    pub items_listed: i32,
    pub rules_matched: i32,
    pub errors: i32,
    pub skipped: i32,
    pub execution_time: f64,
    pub listings_created: Vec<ListingCreated>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ListingCreated {
    pub item_id: String,
    pub product_name: String,
    pub rule_applied: String,
    pub price: Option<f64>,
    pub platform: Option<String>,
    pub dry_run: Option<bool>,
    pub would_list: Option<bool>,
    pub estimated_price: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AutoListingSimulation {
    pub simulation_complete: bool,
    pub rule_tested: String,
    pub items_evaluated: i32,
    pub items_that_would_be_listed: i32,
    pub rules_matched: i32,
    pub potential_revenue: f64,
    pub average_markup_percent: f64,
    pub execution_time: f64,
    pub matched_items: Vec<SimulatedListingItem>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SimulatedListingItem {
    pub item_id: String,
    pub product_name: String,
    pub rule_matched: String,
    pub current_status: String,
    pub purchase_price: f64,
    pub estimated_listing_price: f64,
    pub profit_margin_percent: f64,
    pub confidence: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RuleToggleResponse {
    pub success: bool,
    pub rule_name: String,
    pub previous_state: bool,
    pub new_state: bool,
    pub message: String,
    pub updated_at: String,
}

// Dead Stock Types
#[derive(Debug, Serialize, Deserialize)]
pub struct DeadStockSummary {
    pub total_items_at_risk: i32,
    pub risk_breakdown: HashMap<String, i32>,
    pub financial_impact: DeadStockFinancialImpact,
    pub top_priorities: Vec<DeadStockItem>,
    pub last_analysis: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DeadStockFinancialImpact {
    pub locked_capital: f64,
    pub potential_loss: f64,
    pub loss_percentage: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DeadStockItem {
    pub item_id: String,
    pub product_name: String,
    pub brand_name: String,
    pub size_value: String,
    pub purchase_price: f64,
    pub current_market_price: Option<f64>,
    pub days_in_inventory: i32,
    pub risk_score: f64,
    pub risk_level: String,
    pub locked_capital: f64,
    pub potential_loss: f64,
    pub recommended_actions: Vec<String>,
    pub market_trend: Option<String>,
    pub velocity_score: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DeadStockAnalysis {
    pub analysis_id: String,
    pub started_at: String,
    pub total_items_analyzed: i32,
    pub filters_applied: HashMap<String, Value>,
    pub dead_stock_items: Vec<DeadStockItem>,
    pub risk_summary: HashMap<String, i32>,
    pub financial_impact: DeadStockDetailedFinancialImpact,
    pub recommendations: Vec<String>,
    pub analysis_timestamp: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DeadStockDetailedFinancialImpact {
    pub total_locked_capital: f64,
    pub total_potential_loss: f64,
    pub loss_percentage: f64,
    pub locked_capital_by_risk: HashMap<String, f64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ClearanceExecution {
    pub execution_id: String,
    pub started_at: String,
    pub success: bool,
    pub dry_run: bool,
    pub risk_levels_targeted: Vec<String>,
    pub items_processed: i32,
    pub actions_taken: Vec<ClearanceAction>,
    pub total_price_reductions: f64,
    pub estimated_capital_freed: f64,
    pub projected_outcomes: ClearanceProjection,
    pub execution_time: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ClearanceAction {
    pub item_id: String,
    pub product_name: String,
    pub original_price: Option<f64>,
    pub new_price: Option<f64>,
    pub discount_percent: f64,
    pub action_type: String,
    pub estimated_sale_probability: Option<f64>,
    pub would_reduce_from: Option<f64>,
    pub would_reduce_to: Option<f64>,
    pub dry_run: Option<bool>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ClearanceProjection {
    pub estimated_sales_within_30d: i32,
    pub estimated_revenue: f64,
    pub capital_recovery_rate: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RiskLevelDefinitions {
    pub risk_levels: HashMap<String, RiskLevelDefinition>,
    pub calculation_factors: HashMap<String, f64>,
    pub automation_triggers: HashMap<String, f64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RiskLevelDefinition {
    pub name: String,
    pub description: String,
    pub risk_score_range: String,
    pub age_threshold_days: i32,
    pub color: String,
    pub icon: String,
    pub action_priority: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DeadStockTrends {
    pub trend_period: String,
    pub trend_data: Vec<DeadStockTrendData>,
    pub insights: DeadStockInsights,
    pub recommendations: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DeadStockTrendData {
    pub date: String,
    pub total_dead_stock_items: i32,
    pub locked_capital: f64,
    pub items_liquidated: i32,
    pub capital_freed: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DeadStockInsights {
    pub trend_direction: String,
    pub avg_liquidation_success_rate: f64,
    pub most_problematic_category: String,
    pub most_problematic_brand: String,
    pub seasonal_pattern: String,
}

// Predictive Insights Types
#[derive(Debug, Serialize, Deserialize)]
pub struct PredictiveInsight {
    pub insight_id: String,
    pub insight_type: String,
    pub priority: String,
    pub title: String,
    pub description: String,
    pub product_id: Option<String>,
    pub product_name: Option<String>,
    pub confidence_score: f64,
    pub recommended_actions: Vec<serde_json::Value>,
    pub supporting_data: serde_json::Value,
    pub expires_at: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct InventoryForecast {
    pub product_id: String,
    pub product_name: String,
    pub current_stock: i32,
    pub predicted_demand_30d: f64,
    pub predicted_demand_90d: f64,
    pub restock_recommendation: String,
    pub optimal_restock_quantity: i32,
    pub days_until_stockout: Option<i32>,
    pub confidence_level: f64,
    pub seasonal_factors: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RestockRecommendation {
    pub product_id: String,
    pub product_name: String,
    pub current_stock: i32,
    pub recommended_quantity: i32,
    pub investment_required: f64,
    pub projected_revenue: f64,
    pub projected_profit: f64,
    pub roi_estimate: f64,
    pub optimal_timing: String,
    pub risk_level: String,
    pub supporting_insights: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PredictiveInsightsSummary {
    pub timestamp: String,
    pub insights_generated: i32,
    pub critical_insights: i32,
    pub high_priority_insights: i32,
    pub restock_opportunities: i32,
    pub profit_optimizations: i32,
    pub market_shifts_detected: i32,
    pub seasonal_trends: i32,
    pub clearance_alerts: i32,
    pub total_potential_revenue: f64,
    pub total_potential_profit: f64,
    pub avg_forecast_confidence: f64,
    pub categories: serde_json::Value,
    pub recommendations: Vec<String>,
    pub next_analysis_at: String,
}

impl ApiClient {
    pub fn new(base_url: String) -> Self {
        Self {
            client: Client::new(),
            base_url,
        }
    }

    pub async fn health_check(&self) -> Result<HealthStatus, reqwest::Error> {
        let url = format!("{}/health", self.base_url);
        let response = self.client.get(&url).send().await?;
        let health: HealthStatus = response.json().await?;
        Ok(health)
    }

    pub async fn get_inventory_items(&self, limit: Option<i32>) -> Result<Vec<InventoryItem>, reqwest::Error> {
        let mut url = format!("{}/api/v1/inventory", self.base_url);
        if let Some(limit) = limit {
            url = format!("{}?limit={}", url, limit);
        }
        
        let response = self.client.get(&url).send().await?;
        
        // Parse the response which contains items and pagination info
        let response_json: serde_json::Value = response.json().await?;
        
        // Extract just the items array from the response
        if let Some(items_value) = response_json.get("items") {
            match serde_json::from_value::<Vec<InventoryItem>>(items_value.clone()) {
                Ok(items) => Ok(items),
                Err(e) => {
                    eprintln!("Failed to deserialize inventory items: {:?}", e);
                    eprintln!("Sample item data: {:?}", 
                        items_value.as_array()
                            .and_then(|arr| arr.get(0))
                            .map(|item| serde_json::to_string_pretty(item).unwrap_or_default())
                            .unwrap_or_default()
                    );
                    Ok(vec![]) // Return empty for now, but we'll see the error
                }
            }
        } else {
            // Fallback: try to parse the entire response as an array (for compatibility)
            match serde_json::from_value::<Vec<InventoryItem>>(response_json) {
                Ok(items) => Ok(items),
                Err(e) => {
                    eprintln!("Failed to deserialize entire response as inventory items: {:?}", e);
                    Ok(vec![]) // Return empty for now, but we'll see the error
                }
            }
        }
    }

    pub async fn get_product_stats(&self) -> Result<ProductStats, reqwest::Error> {
        let url = format!("{}/api/v1/products/stats", self.base_url);
        let response = self.client.get(&url).send().await?;
        let stats: ProductStats = response.json().await?;
        Ok(stats)
    }

    pub async fn import_stockx_data(&self, request: ImportRequest) -> Result<ImportResponse, reqwest::Error> {
        let url = format!("{}/api/v1/integration/stockx/import", self.base_url);
        let response = self.client.post(&url).json(&request).send().await?;
        let import_response: ImportResponse = response.json().await?;
        Ok(import_response)
    }

    pub async fn get_import_status(&self, batch_id: Uuid) -> Result<ImportStatus, reqwest::Error> {
        let url = format!("{}/api/v1/integration/import/{}/status", self.base_url, batch_id);
        let response = self.client.get(&url).send().await?;
        let status: ImportStatus = response.json().await?;
        Ok(status)
    }

    pub async fn get_dashboard_metrics(&self) -> Result<DashboardMetrics, reqwest::Error> {
        let url = format!("{}/api/v1/dashboard/metrics", self.base_url);
        let response = self.client.get(&url).send().await?;
        let api_metrics: ApiDashboardMetrics = response.json().await?;
        
        // Convert API response to simplified DashboardMetrics
        let metrics = DashboardMetrics {
            total_inventory_value: api_metrics.inventory.total_inventory_value,
            monthly_sales: 0.0, // TODO: calculate from recent_activity
            profit_margin: 0.0, // TODO: calculate profit margin
            active_listings: api_metrics.inventory.items_listed,
            pending_imports: 0, // TODO: get from import status
            recent_transactions: api_metrics.sales.recent_activity,
        };
        
        Ok(metrics)
    }

    pub async fn run_database_query(&self, query: String) -> Result<Vec<HashMap<String, Value>>, reqwest::Error> {
        let url = format!("{}/api/v1/admin/query", self.base_url);
        let payload = serde_json::json!({"query": query});
        let response = self.client.post(&url).json(&payload).send().await?;
        let results: Vec<HashMap<String, Value>> = response.json().await?;
        Ok(results)
    }

    pub async fn export_data_csv(&self, table: String, filters: Option<HashMap<String, String>>) -> Result<String, reqwest::Error> {
        let mut url = format!("{}/api/v1/export/csv/{}", self.base_url, table);
        
        if let Some(filters) = filters {
            let query_params: Vec<String> = filters
                .iter()
                .map(|(k, v)| format!("{}={}", k, v))
                .collect();
            if !query_params.is_empty() {
                url = format!("{}?{}", url, query_params.join("&"));
            }
        }
        
        let response = self.client.get(&url).send().await?;
        let csv_data = response.text().await?;
        Ok(csv_data)
    }

    pub async fn get_enrichment_status(&self) -> Result<EnrichmentStatusResponse, reqwest::Error> {
        let url = format!("{}/api/v1/products/enrichment/status", self.base_url);
        let response = self.client.get(&url).send().await?;
        let status: EnrichmentStatusResponse = response.json().await?;
        Ok(status)
    }

    pub async fn start_product_enrichment(&self, product_ids: Option<Vec<String>>) -> Result<EnrichmentResponse, reqwest::Error> {
        let mut url = format!("{}/api/v1/products/enrich", self.base_url);
        
        if let Some(ids) = product_ids {
            let query_params: Vec<String> = ids
                .iter()
                .map(|id| format!("product_ids={}", id))
                .collect();
            if !query_params.is_empty() {
                url = format!("{}?{}", url, query_params.join("&"));
            }
        }
        
        let response = self.client.post(&url).send().await?;
        let enrichment_response: EnrichmentResponse = response.json().await?;
        Ok(enrichment_response)
    }

    pub async fn get_pricing_recommendation(&self, request: PricingRequest) -> Result<PricingRecommendation, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/recommend", self.base_url);
        let response = self.client.post(&url).json(&request).send().await?;
        let recommendation: PricingRecommendation = response.json().await?;
        Ok(recommendation)
    }

    pub async fn get_market_analysis(&self, product_id: String) -> Result<MarketAnalysis, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/market-analysis/{}", self.base_url, product_id);
        let response = self.client.get(&url).send().await?;
        let analysis: MarketAnalysis = response.json().await?;
        Ok(analysis)
    }

    pub async fn get_pricing_insights(&self) -> Result<PricingInsights, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/insights", self.base_url);
        let response = self.client.get(&url).send().await?;
        let insights: PricingInsights = response.json().await?;
        Ok(insights)
    }

    pub async fn get_pricing_strategies(&self) -> Result<HashMap<String, Value>, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/strategies", self.base_url);
        let response = self.client.get(&url).send().await?;
        let strategies: HashMap<String, Value> = response.json().await?;
        Ok(strategies)
    }

    pub async fn generate_sales_forecast(&self, request: ForecastRequest) -> Result<ForecastAnalysis, reqwest::Error> {
        let url = format!("{}/api/v1/analytics/forecast/sales", self.base_url);
        let response = self.client.post(&url).json(&request).send().await?;
        let forecast: ForecastAnalysis = response.json().await?;
        Ok(forecast)
    }

    pub async fn get_market_trends(&self, days_back: Option<i32>) -> Result<Vec<MarketTrend>, reqwest::Error> {
        let mut url = format!("{}/api/v1/analytics/trends/market", self.base_url);
        if let Some(days) = days_back {
            url = format!("{}?days_back={}", url, days);
        }
        let response = self.client.get(&url).send().await?;
        let trends: Vec<MarketTrend> = response.json().await?;
        Ok(trends)
    }

    pub async fn get_forecast_models(&self) -> Result<HashMap<String, Value>, reqwest::Error> {
        let url = format!("{}/api/v1/analytics/models", self.base_url);
        let response = self.client.get(&url).send().await?;
        let models: HashMap<String, Value> = response.json().await?;
        Ok(models)
    }

    pub async fn get_predictive_insights(&self) -> Result<PredictiveInsights, reqwest::Error> {
        let url = format!("{}/api/v1/analytics/insights/predictive", self.base_url);
        let response = self.client.get(&url).send().await?;
        let insights: PredictiveInsights = response.json().await?;
        Ok(insights)
    }

    pub async fn get_stockx_listings(&self, status: Option<String>, limit: Option<i32>) -> Result<Vec<HashMap<String, Value>>, reqwest::Error> {
        let mut url = format!("{}/api/v1/inventory/stockx-listings", self.base_url);
        let mut params = Vec::new();
        
        if let Some(s) = status {
            params.push(format!("status={}", s));
        }
        if let Some(l) = limit {
            params.push(format!("limit={}", l));
        }
        
        if !params.is_empty() {
            url.push_str("?");
            url.push_str(&params.join("&"));
        }

        let response = self.client.get(&url).send().await?;
        let data: Value = response.json().await?;
        
        if let Some(listings) = data["data"]["listings"].as_array() {
            Ok(listings.iter().map(|v| {
                let mut map = HashMap::new();
                if let Some(obj) = v.as_object() {
                    for (key, value) in obj {
                        map.insert(key.clone(), value.clone());
                    }
                }
                map
            }).collect())
        } else {
            Ok(Vec::new())
        }
    }

    pub async fn create_stockx_listing(&self, request: StockXListingRequest) -> Result<StockXListingResponse, reqwest::Error> {
        let url = format!("{}/api/v1/inventory/items/{}/stockx-listing", self.base_url, request.item_id);
        let response = self.client.post(&url)
            .json(&serde_json::json!({
                "listing_type": request.listing_type
            }))
            .send()
            .await?;
        let listing_response: StockXListingResponse = response.json().await?;
        Ok(listing_response)
    }

    pub async fn get_alias_listings(&self, status: Option<String>, limit: Option<i32>) -> Result<Vec<HashMap<String, Value>>, reqwest::Error> {
        let mut url = format!("{}/api/v1/inventory/alias-listings", self.base_url);
        let mut params = Vec::new();
        
        if let Some(s) = status {
            params.push(format!("status={}", s));
        }
        if let Some(l) = limit {
            params.push(format!("limit={}", l));
        }
        
        if !params.is_empty() {
            url.push_str("?");
            url.push_str(&params.join("&"));
        }

        let response = self.client.get(&url).send().await?;
        let data: Value = response.json().await?;
        
        if let Some(listings) = data["data"]["listings"].as_array() {
            Ok(listings.iter().map(|v| {
                let mut map = HashMap::new();
                if let Some(obj) = v.as_object() {
                    for (key, value) in obj {
                        map.insert(key.clone(), value.clone());
                    }
                }
                map
            }).collect())
        } else {
            Ok(Vec::new())
        }
    }

    pub async fn sync_inventory_from_stockx(&self) -> Result<HashMap<String, Value>, reqwest::Error> {
        let url = format!("{}/api/v1/inventory/sync-from-stockx", self.base_url);
        let response = self.client.post(&url).send().await?;
        let data: Value = response.json().await?;
        
        let mut result = HashMap::new();
        if let Some(obj) = data.as_object() {
            for (key, value) in obj {
                result.insert(key.clone(), value.clone());
            }
        }
        Ok(result)
    }

    pub async fn get_system_status(&self) -> Result<crate::commands::SystemStatus, reqwest::Error> {
        let url = format!("{}/api/v1/system/status", self.base_url);
        let response = self.client.get(&url).send().await?;
        let status: crate::commands::SystemStatus = response.json().await?;
        Ok(status)
    }

    // Smart Pricing API Methods
    pub async fn optimize_inventory_pricing(&self, strategy: String, limit: i32) -> Result<SmartPricingOptimization, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/smart/optimize-inventory?strategy={}&limit={}", self.base_url, strategy, limit);
        let response = self.client.post(&url).send().await?;
        let optimization: SmartPricingOptimization = response.json().await?;
        Ok(optimization)
    }

    pub async fn get_auto_repricing_status(&self) -> Result<AutoRepricingStatus, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/smart/auto-repricing/status", self.base_url);
        let response = self.client.get(&url).send().await?;
        let status: AutoRepricingStatus = response.json().await?;
        Ok(status)
    }

    pub async fn toggle_auto_repricing(&self, enabled: bool) -> Result<HashMap<String, Value>, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/smart/auto-repricing/toggle", self.base_url);
        let payload = serde_json::json!({"enabled": enabled});
        let response = self.client.post(&url).json(&payload).send().await?;
        let result: HashMap<String, Value> = response.json().await?;
        Ok(result)
    }

    pub async fn get_smart_market_trends(&self) -> Result<MarketTrendData, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/smart/market-trends", self.base_url);
        let response = self.client.get(&url).send().await?;
        let trends: MarketTrendData = response.json().await?;
        Ok(trends)
    }

    // Auto-Listing API Methods
    pub async fn get_auto_listing_status(&self) -> Result<AutoListingStatus, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/auto-listing/status", self.base_url);
        let response = self.client.get(&url).send().await?;
        let status: AutoListingStatus = response.json().await?;
        Ok(status)
    }

    pub async fn execute_auto_listing(&self, max_items: i32, dry_run: bool) -> Result<AutoListingExecution, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/auto-listing/execute", self.base_url);
        let payload = serde_json::json!({"max_items": max_items, "dry_run": dry_run});
        let response = self.client.post(&url).json(&payload).send().await?;
        let execution: AutoListingExecution = response.json().await?;
        Ok(execution)
    }

    pub async fn simulate_auto_listing(&self, rule_name: Option<String>, max_items: i32) -> Result<AutoListingSimulation, reqwest::Error> {
        let mut url = format!("{}/api/v1/pricing/auto-listing/simulate?max_items={}", self.base_url, max_items);
        if let Some(rule) = rule_name {
            url = format!("{}&rule_name={}", url, rule);
        }
        let response = self.client.post(&url).send().await?;
        let simulation: AutoListingSimulation = response.json().await?;
        Ok(simulation)
    }

    pub async fn toggle_listing_rule(&self, rule_name: String, active: bool) -> Result<RuleToggleResponse, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/auto-listing/toggle-rule", self.base_url);
        let payload = serde_json::json!({"rule_name": rule_name, "active": active});
        let response = self.client.post(&url).json(&payload).send().await?;
        let toggle_response: RuleToggleResponse = response.json().await?;
        Ok(toggle_response)
    }

    // Dead Stock API Methods
    pub async fn get_dead_stock_summary(&self) -> Result<DeadStockSummary, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/dead-stock/summary", self.base_url);
        let response = self.client.get(&url).send().await?;
        let summary: DeadStockSummary = response.json().await?;
        Ok(summary)
    }

    pub async fn analyze_dead_stock(&self, brand_filter: Option<String>, category_filter: Option<String>, min_risk_score: f64) -> Result<DeadStockAnalysis, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/dead-stock/analyze", self.base_url);
        let payload = serde_json::json!({
            "brand_filter": brand_filter,
            "category_filter": category_filter,
            "min_risk_score": min_risk_score
        });
        let response = self.client.post(&url).json(&payload).send().await?;
        let analysis: DeadStockAnalysis = response.json().await?;
        Ok(analysis)
    }

    pub async fn execute_clearance(&self, risk_levels: Vec<String>, max_items: i32, dry_run: bool) -> Result<ClearanceExecution, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/dead-stock/clearance", self.base_url);
        let payload = serde_json::json!({
            "risk_levels": risk_levels,
            "max_items": max_items,
            "dry_run": dry_run
        });
        let response = self.client.post(&url).json(&payload).send().await?;
        let execution: ClearanceExecution = response.json().await?;
        Ok(execution)
    }

    pub async fn get_risk_level_definitions(&self) -> Result<RiskLevelDefinitions, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/dead-stock/risk-levels", self.base_url);
        let response = self.client.get(&url).send().await?;
        let definitions: RiskLevelDefinitions = response.json().await?;
        Ok(definitions)
    }

    pub async fn get_dead_stock_trends(&self) -> Result<DeadStockTrends, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/dead-stock/trends", self.base_url);
        let response = self.client.get(&url).send().await?;
        let trends: DeadStockTrends = response.json().await?;
        Ok(trends)
    }

    // Predictive Insights API Methods
    pub async fn get_predictive_insights(&self, insight_types: Option<String>, days_ahead: i32, limit: i32) -> Result<Vec<PredictiveInsight>, reqwest::Error> {
        let mut url = format!("{}/api/v1/pricing/predictive/insights?days_ahead={}&limit={}", self.base_url, days_ahead, limit);
        if let Some(types) = insight_types {
            url = format!("{}&insight_types={}", url, types);
        }
        let response = self.client.get(&url).send().await?;
        let insights: Vec<PredictiveInsight> = response.json().await?;
        Ok(insights)
    }

    pub async fn get_inventory_forecasts(&self, product_ids: Option<String>, horizon_days: i32) -> Result<Vec<InventoryForecast>, reqwest::Error> {
        let mut url = format!("{}/api/v1/pricing/predictive/forecasts?horizon_days={}", self.base_url, horizon_days);
        if let Some(ids) = product_ids {
            url = format!("{}&product_ids={}", url, ids);
        }
        let response = self.client.get(&url).send().await?;
        let forecasts: Vec<InventoryForecast> = response.json().await?;
        Ok(forecasts)
    }

    pub async fn get_restock_recommendations(&self, investment_budget: Option<f64>, min_roi: f64, max_products: i32) -> Result<Vec<RestockRecommendation>, reqwest::Error> {
        let mut url = format!("{}/api/v1/pricing/predictive/restock-recommendations?min_roi={}&max_products={}", self.base_url, min_roi, max_products);
        if let Some(budget) = investment_budget {
            url = format!("{}&investment_budget={}", url, budget);
        }
        let response = self.client.get(&url).send().await?;
        let recommendations: Vec<RestockRecommendation> = response.json().await?;
        Ok(recommendations)
    }

    pub async fn get_predictive_insights_summary(&self) -> Result<PredictiveInsightsSummary, reqwest::Error> {
        let url = format!("{}/api/v1/pricing/predictive/summary", self.base_url);
        let response = self.client.get(&url).send().await?;
        let summary: PredictiveInsightsSummary = response.json().await?;
        Ok(summary)
    }
}