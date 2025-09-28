-- =====================================================
-- SUPPLIER DATA ANALYSIS - Debug Queries
-- =====================================================

-- 1. Alle unique Supplier-Werte analysieren
-- Query Name: debug_suppliers_overview
SELECT
    i.supplier,
    COUNT(*) as item_count,
    COUNT(CASE WHEN i.status = 'listed' THEN 1 END) as listed_count,
    MIN(i.created_at) as first_seen,
    MAX(i.created_at) as last_seen,
    ARRAY_AGG(DISTINCT i.status) as statuses_used
FROM products.inventory i
WHERE i.supplier IS NOT NULL
GROUP BY i.supplier
ORDER BY item_count DESC;

-- 2. Sample der Supplier-Daten mit Product Info
-- Query Name: debug_supplier_samples
SELECT
    i.supplier,
    p.name as product_name,
    b.name as brand_name,
    i.status,
    i.created_at,
    i.notes
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE i.supplier IS NOT NULL
ORDER BY i.supplier, i.created_at DESC
LIMIT 20;

-- 3. Supplier vs echte Supplier-Tabelle vergleichen
-- Query Name: debug_supplier_vs_supplier_table
SELECT
    'From inventory.supplier field' as source,
    i.supplier as supplier_name,
    COUNT(*) as usage_count
FROM products.inventory i
WHERE i.supplier IS NOT NULL
GROUP BY i.supplier

UNION ALL

SELECT
    'From core.suppliers table' as source,
    s.name as supplier_name,
    0 as usage_count
FROM core.suppliers s
ORDER BY source, usage_count DESC;

-- 4. Check ob supplier_id auch befüllt ist
-- Query Name: debug_supplier_id_usage
SELECT
    CASE
        WHEN i.supplier_id IS NOT NULL THEN 'Has supplier_id'
        ELSE 'No supplier_id'
    END as supplier_id_status,
    i.supplier as supplier_text,
    COUNT(*) as count
FROM products.inventory i
GROUP BY
    CASE
        WHEN i.supplier_id IS NOT NULL THEN 'Has supplier_id'
        ELSE 'No supplier_id'
    END,
    i.supplier
ORDER BY count DESC;

-- 5. Wenn supplier_id existiert, zeige echte Supplier-Namen
-- Query Name: debug_real_suppliers
SELECT
    s.name as real_supplier_name,
    s.supplier_type,
    s.display_name,
    COUNT(i.id) as inventory_items_count
FROM core.suppliers s
LEFT JOIN products.inventory i ON s.id = i.supplier_id
GROUP BY s.id, s.name, s.supplier_type, s.display_name
ORDER BY inventory_items_count DESC;