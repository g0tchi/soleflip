# Proof-of-Concept: Shopify Readiness & Data Integration Guide

This document explains the components developed for the Shopify readiness proof-of-concept and how to use them.

## 1. Overview

This PoC delivers three main components:
1.  **Schema Analyzer:** A tool to automatically scan and document the existing database schema.
2.  **Shopify Compatibility Analysis:** A generated report that maps the local schema to Shopify entities and identifies gaps.
3.  **Awin/CSV Data Connector:** A connector to import external sales data into a staging area in the database, with built-in validation.

## 2. Schema Analysis

A script has been created to introspect the live database schema and generate a detailed Markdown document.

### How to Run the Analyzer

1.  **Ensure the database is running.** If not, you can start it (in the background) using:
    ```bash
    sudo docker compose up -d db
    ```
    *Note: The first time you run this, it may take a minute for the database to initialize.*

2.  **Run the script:**
    ```bash
    python scripts/analysis/schema_analyzer.py
    ```

### Output

The script will generate (or overwrite) the following file:
- `docs/generated/db_schema_analysis.md`

This file contains a complete list of all schemas, tables, columns, data types, and relationships in the database.

## 3. Shopify Compatibility Mapping

Based on the schema analysis, a manual mapping to Shopify entities was performed. The results, including a detailed gap analysis, are available in the following document:

- `docs/shopify_mapping.md`

This document is the primary reference for understanding what changes and additions are needed to make the current schema "Shopify-ready". The most significant identified gap is the lack of a dedicated `Customer` entity.

## 4. Awin/CSV Data Connector

A connector has been implemented to simulate importing sales data from an external source (like an Awin affiliate report).

### Architecture

- **Staging First:** The connector does **not** write directly to production tables. Instead, it writes to the `integration.import_batches` and `integration.import_records` tables. This is a crucial best practice to avoid corrupting live data.
- **Validation:** The connector performs basic validation on each row of the source file. It checks for the presence of required fields (e.g., `TransactionID`, `SaleAmount`, `SKU`).
- **Error Logging:** If a row fails validation, its status is marked as `error`, and the specific validation errors are logged as a JSON object in the `import_records.validation_errors` column. This allows for easy debugging and reprocessing of failed records.

### How to Run the Import

1.  **Ensure the database is running** (see step 2.1).

2.  **Prepare the data file.** A sample file is provided at `data/samples/awin_sales_report.csv`. You can modify this file or create a new one with the same format.

3.  **Run the import script:**
    ```bash
    python scripts/integration/run_awin_import.py
    ```

### Verifying the Import

After running the script, you can connect to the database and inspect the `integration` schema to see the results.

- **Check the batch:**
  ```sql
  SELECT * FROM integration.import_batches ORDER BY created_at DESC LIMIT 1;
  ```
- **Check the imported records (including errors):**
  ```sql
  SELECT id, status, source_data, validation_errors FROM integration.import_records WHERE batch_id = '<your_batch_id>';
  ```
