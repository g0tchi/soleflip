use reqwest::Client;
use serde::{Deserialize, Serialize};
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
    #[serde(default = "default_sku")]
    pub sku: String,
    #[serde(rename = "product_name")]
    pub name: String,
    #[serde(rename = "brand_name")]
    pub brand: String,
    pub size: String,
    #[serde(default = "default_condition")]
    pub condition: String,
    pub purchase_price: Option<f64>,
    #[serde(default = "default_current_value")]
    pub current_value: f64,
    pub status: String,
}

fn default_sku() -> String {
    "N/A".to_string()
}

fn default_condition() -> String {
    "Unknown".to_string()
}

fn default_current_value() -> f64 {
    0.0
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
                Err(_) => Ok(vec![]), // Return empty vec if parsing fails
            }
        } else {
            // Fallback: try to parse the entire response as an array (for compatibility)
            match serde_json::from_value::<Vec<InventoryItem>>(response_json) {
                Ok(items) => Ok(items),
                Err(_) => Ok(vec![]), // Return empty vec if parsing fails
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
}