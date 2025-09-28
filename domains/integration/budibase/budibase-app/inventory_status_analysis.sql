-- =====================================================
-- INVENTORY STATUS ANALYSIS - Real Data Distribution
-- =====================================================

-- 1. Status Verteilung deiner Inventory Items
-- Query Name: inventory_status_breakdown
SELECT
    i.status,
    COUNT(*) as item_count,
    SUM(i.purchase_price * i.quantity) as total_value,
    AVG(i.purchase_price) as avg_price,
    MIN(i.created_at) as oldest_item,
    MAX(i.created_at) as newest_item,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM products.inventory i
GROUP BY i.status
ORDER BY item_count DESC;

-- 2. Mögliche Duplikate finden (gleiche Product + Size)
-- Query Name: potential_duplicates
SELECT
    p.name as product_name,
    b.name as brand_name,
    s.value as size,
    COUNT(*) as duplicate_count,
    ARRAY_AGG(i.status) as statuses,
    ARRAY_AGG(i.supplier) as sources,
    ARRAY_AGG(i.purchase_price) as prices,
    STRING_AGG(i.id::text, ', ') as inventory_ids
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
LEFT JOIN core.sizes s ON i.size_id = s.id
GROUP BY p.name, b.name, s.value
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, product_name
LIMIT 20;

-- 3. Aktive vs verkaufte Items
-- Query Name: active_vs_sold_analysis
SELECT
    CASE
        WHEN i.status IN ('listed', 'available', 'in_stock') THEN 'Available for Sale'
        WHEN i.status IN ('sold', 'completed') THEN 'Sold'
        WHEN i.status IN ('pending', 'processing') THEN 'In Process'
        ELSE 'Other Status'
    END as status_category,
    COUNT(*) as item_count,
    SUM(i.purchase_price * i.quantity) as total_value,
    AVG(i.purchase_price) as avg_price
FROM products.inventory i
GROUP BY
    CASE
        WHEN i.status IN ('listed', 'available', 'in_stock') THEN 'Available for Sale'
        WHEN i.status IN ('sold', 'completed') THEN 'Sold'
        WHEN i.status IN ('pending', 'processing') THEN 'In Process'
        ELSE 'Other Status'
    END
ORDER BY item_count DESC;

-- 4. Items nach Datenquelle und Status
-- Query Name: data_source_status_breakdown
SELECT
    i.supplier as data_source,
    i.status,
    COUNT(*) as item_count,
    SUM(i.purchase_price * i.quantity) as total_value
FROM products.inventory i
WHERE i.supplier IS NOT NULL
GROUP BY i.supplier, i.status
ORDER BY i.supplier, item_count DESC;

-- 5. Verkaufbare Items (echte verfügbare Inventory)
-- Query Name: sellable_inventory_summary
SELECT
    COUNT(*) as total_sellable_items,
    SUM(i.purchase_price * i.quantity) as total_sellable_value,
    AVG(i.purchase_price) as avg_price,
    COUNT(DISTINCT b.name) as unique_brands,
    COUNT(DISTINCT s.value) as unique_sizes,
    COUNT(DISTINCT p.name) as unique_products
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
LEFT JOIN core.sizes s ON i.size_id = s.id
WHERE i.status IN ('listed', 'available', 'in_stock');