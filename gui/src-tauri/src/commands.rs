use crate::api::{ApiClient, HealthStatus, InventoryItem, ProductStats, ImportRequest, ImportResponse, ImportStatus, DashboardMetrics, EnrichmentStatusResponse, EnrichmentResponse, PricingRequest, PricingRecommendation, MarketAnalysis, PricingInsights, ForecastRequest, ForecastAnalysis, MarketTrend, PredictiveInsights};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize)]
pub struct SystemStatus {
    pub api_connected: bool,
    pub database_healthy: bool,
    pub last_check: String,
    pub version: String,
    pub environment: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct StockXListingRequest {
    pub item_id: String,
    pub listing_type: String, // 'immediate' or 'presale'
}

#[derive(Debug, Serialize, Deserialize)]
pub struct StockXListingResponse {
    pub success: bool,
    pub listing_id: Option<String>,
    pub message: String,
}

#[tauri::command]
pub async fn health_check() -> Result<HealthStatus, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.health_check().await {
        Ok(health) => Ok(health),
        Err(e) => Err(format!("Health check failed: {}", e)),
    }
}

#[tauri::command]
pub async fn get_inventory_items(limit: Option<i32>) -> Result<Vec<InventoryItem>, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.get_inventory_items(limit).await {
        Ok(items) => Ok(items),
        Err(e) => Err(format!("Failed to fetch inventory: {}", e)),
    }
}

#[tauri::command]
pub async fn get_product_stats() -> Result<ProductStats, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.get_product_stats().await {
        Ok(stats) => Ok(stats),
        Err(e) => Err(format!("Failed to fetch product stats: {}", e)),
    }
}

#[tauri::command]
pub async fn import_stockx_data(from_date: String, to_date: String) -> Result<ImportResponse, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    let request = ImportRequest { from_date, to_date };
    
    match client.import_stockx_data(request).await {
        Ok(response) => Ok(response),
        Err(e) => Err(format!("Failed to start import: {}", e)),
    }
}

#[tauri::command]
pub async fn get_import_status(batch_id: String) -> Result<ImportStatus, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    let uuid = Uuid::parse_str(&batch_id)
        .map_err(|e| format!("Invalid batch ID: {}", e))?;
    
    match client.get_import_status(uuid).await {
        Ok(status) => Ok(status),
        Err(e) => Err(format!("Failed to fetch import status: {}", e)),
    }
}

#[tauri::command]
pub async fn get_dashboard_metrics() -> Result<DashboardMetrics, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.get_dashboard_metrics().await {
        Ok(metrics) => Ok(metrics),
        Err(e) => Err(format!("Failed to fetch dashboard metrics: {}", e)),
    }
}

#[tauri::command]
pub async fn run_database_query(query: String) -> Result<Vec<HashMap<String, Value>>, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    // Security check - only allow SELECT queries
    let query_trimmed = query.trim().to_lowercase();
    if !query_trimmed.starts_with("select") {
        return Err("Only SELECT queries are allowed for security reasons".to_string());
    }
    
    match client.run_database_query(query).await {
        Ok(results) => Ok(results),
        Err(e) => Err(format!("Query failed: {}", e)),
    }
}

#[tauri::command]
pub async fn export_data_csv(table: String, filters: Option<HashMap<String, String>>) -> Result<String, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.export_data_csv(table, filters).await {
        Ok(csv_data) => Ok(csv_data),
        Err(e) => Err(format!("Export failed: {}", e)),
    }
}

#[tauri::command]
pub async fn get_system_status() -> Result<SystemStatus, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.health_check().await {
        Ok(health) => {
            // Check if database component is healthy
            let database_healthy = health.components
                .get("database")
                .and_then(|db| db.get("status"))
                .and_then(|status| status.as_str())
                .map_or(false, |status| status == "healthy");
            
            Ok(SystemStatus {
                api_connected: true,
                database_healthy,
                last_check: health.timestamp,
                version: health.version,
                environment: health.environment,
            })
        },
        Err(_e) => Ok(SystemStatus {
            api_connected: false,
            database_healthy: false,
            last_check: chrono::Utc::now().to_rfc3339(),
            version: "unknown".to_string(),
            environment: "unknown".to_string(),
        }),
    }
}

#[tauri::command]
pub async fn get_enrichment_status() -> Result<EnrichmentStatusResponse, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.get_enrichment_status().await {
        Ok(status) => Ok(status),
        Err(e) => Err(format!("Failed to fetch enrichment status: {}", e)),
    }
}

#[tauri::command]
pub async fn start_product_enrichment(product_ids: Option<Vec<String>>) -> Result<EnrichmentResponse, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.start_product_enrichment(product_ids).await {
        Ok(response) => Ok(response),
        Err(e) => Err(format!("Failed to start product enrichment: {}", e)),
    }
}

// Pricing Commands
#[tauri::command]
pub async fn get_pricing_recommendation(request: PricingRequest) -> Result<PricingRecommendation, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.get_pricing_recommendation(request).await {
        Ok(recommendation) => Ok(recommendation),
        Err(e) => Err(format!("Failed to get pricing recommendation: {}", e)),
    }
}

#[tauri::command]
pub async fn get_market_analysis(product_id: String) -> Result<MarketAnalysis, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.get_market_analysis(product_id).await {
        Ok(analysis) => Ok(analysis),
        Err(e) => Err(format!("Failed to get market analysis: {}", e)),
    }
}

#[tauri::command]
pub async fn get_pricing_insights() -> Result<PricingInsights, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.get_pricing_insights().await {
        Ok(insights) => Ok(insights),
        Err(e) => Err(format!("Failed to get pricing insights: {}", e)),
    }
}

#[tauri::command]
pub async fn get_pricing_strategies() -> Result<HashMap<String, Value>, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.get_pricing_strategies().await {
        Ok(strategies) => Ok(strategies),
        Err(e) => Err(format!("Failed to get pricing strategies: {}", e)),
    }
}

// Analytics/Forecast Commands
#[tauri::command]
pub async fn generate_sales_forecast(request: ForecastRequest) -> Result<ForecastAnalysis, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.generate_sales_forecast(request).await {
        Ok(forecast) => Ok(forecast),
        Err(e) => Err(format!("Failed to generate sales forecast: {}", e)),
    }
}

#[tauri::command]
pub async fn get_market_trends(days_back: Option<i32>) -> Result<Vec<MarketTrend>, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.get_market_trends(days_back).await {
        Ok(trends) => Ok(trends),
        Err(e) => Err(format!("Failed to get market trends: {}", e)),
    }
}

#[tauri::command]
pub async fn get_forecast_models() -> Result<HashMap<String, Value>, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.get_forecast_models().await {
        Ok(models) => Ok(models),
        Err(e) => Err(format!("Failed to get forecast models: {}", e)),
    }
}

#[tauri::command]
pub async fn get_predictive_insights() -> Result<PredictiveInsights, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.get_predictive_insights().await {
        Ok(insights) => Ok(insights),
        Err(e) => Err(format!("Failed to get predictive insights: {}", e)),
    }
}

#[tauri::command]
pub async fn create_stockx_listing(item_id: String, listing_type: String) -> Result<StockXListingResponse, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    let request = StockXListingRequest { item_id, listing_type };
    
    match client.create_stockx_listing(request).await {
        Ok(response) => Ok(response),
        Err(e) => Err(format!("Failed to create StockX listing: {}", e)),
    }
}

#[tauri::command]
pub async fn get_stockx_listings(status: Option<String>, limit: Option<i32>) -> Result<Vec<HashMap<String, Value>>, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.get_stockx_listings(status, limit).await {
        Ok(listings) => Ok(listings),
        Err(e) => Err(format!("Failed to get StockX listings: {}", e)),
    }
}

#[tauri::command]
pub async fn get_alias_listings(status: Option<String>, limit: Option<i32>) -> Result<Vec<HashMap<String, Value>>, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.get_alias_listings(status, limit).await {
        Ok(listings) => Ok(listings),
        Err(e) => Err(format!("Failed to get Alias listings: {}", e)),
    }
}

#[tauri::command]
pub async fn sync_inventory_from_stockx() -> Result<HashMap<String, Value>, String> {
    let client = ApiClient::new("http://localhost:8000".to_string());
    
    match client.sync_inventory_from_stockx().await {
        Ok(response) => Ok(response),
        Err(e) => Err(format!("Failed to sync inventory from StockX: {}", e)),
    }
}

