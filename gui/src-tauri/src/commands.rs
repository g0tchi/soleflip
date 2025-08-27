use crate::api::{ApiClient, HealthStatus, InventoryItem, ProductStats, ImportRequest, ImportResponse, ImportStatus, DashboardMetrics};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use tauri::State;
use uuid::Uuid;

// Global API client state
pub struct AppState {
    pub api_client: ApiClient,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SystemStatus {
    pub api_connected: bool,
    pub database_healthy: bool,
    pub last_check: String,
    pub version: String,
    pub environment: String,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            api_client: ApiClient::new("http://localhost:8000".to_string()),
        }
    }
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
        Ok(health) => Ok(SystemStatus {
            api_connected: true,
            database_healthy: health.status == "healthy",
            last_check: health.timestamp,
            version: health.version,
            environment: health.environment,
        }),
        Err(e) => Ok(SystemStatus {
            api_connected: false,
            database_healthy: false,
            last_check: chrono::Utc::now().to_rfc3339(),
            version: "unknown".to_string(),
            environment: "unknown".to_string(),
        }),
    }
}