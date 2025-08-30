// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod api;
mod commands;

use tauri::generate_handler;

#[tokio::main]
async fn main() {
    tauri::Builder::default()
        .invoke_handler(generate_handler![
            commands::health_check,
            commands::get_inventory_items,
            commands::get_product_stats,
            commands::import_stockx_data,
            commands::get_import_status,
            commands::get_dashboard_metrics,
            commands::run_database_query,
            commands::export_data_csv,
            commands::get_system_status,
            commands::get_enrichment_status,
            commands::start_product_enrichment,
            commands::get_pricing_recommendation,
            commands::get_market_analysis,
            commands::get_pricing_insights,
            commands::get_pricing_strategies,
            commands::generate_sales_forecast,
            commands::get_market_trends,
            commands::get_forecast_models,
            commands::get_predictive_insights
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}