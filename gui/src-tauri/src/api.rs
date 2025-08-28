use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use uuid::Uuid;
use chrono::{DateTime, Utc};

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
}