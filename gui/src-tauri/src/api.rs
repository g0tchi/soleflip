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
    pub sku: String,
    pub name: String,
    pub brand: String,
    pub size: String,
    pub condition: String,
    pub purchase_price: f64,
    pub current_value: f64,
    pub status: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ProductStats {
    pub total_products: i64,
    pub total_value: f64,
    pub brands_count: i64,
    pub avg_profit_margin: f64,
    pub top_brands: Vec<(String, i64)>,
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
        let items: Vec<InventoryItem> = response.json().await?;
        Ok(items)
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
        let metrics: DashboardMetrics = response.json().await?;
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
}