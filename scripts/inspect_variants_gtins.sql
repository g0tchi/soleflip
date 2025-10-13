-- Check variants for GTINs in enrichment_data
-- Run this to see if variants contain EAN/GTIN codes

SELECT
    id,
    name,
    sku,
    jsonb_array_length(enrichment_data->'variants') as variant_count,
    enrichment_data->'variants'->0->>'id' as first_variant_id,
    enrichment_data->'variants'->0->>'gtin' as first_variant_gtin,
    enrichment_data->'variants'->0->'gtins' as first_variant_gtins,
    enrichment_data->'variants'->0->'sizeAllTypes'->>'us' as first_variant_size
FROM products.products
WHERE enrichment_data IS NOT NULL
  AND enrichment_data->'variants' IS NOT NULL
LIMIT 10;

-- Check how many have GTINs
SELECT
    COUNT(*) as products_with_enrichment,
    COUNT(CASE WHEN enrichment_data->'variants'->0->>'gtin' IS NOT NULL THEN 1 END) as products_with_gtin,
    COUNT(CASE WHEN enrichment_data->'variants'->0->'gtins' IS NOT NULL THEN 1 END) as products_with_gtins_array
FROM products.products
WHERE enrichment_data IS NOT NULL;
