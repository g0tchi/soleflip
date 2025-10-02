-- Test if StockX listings are actually stored in database
SELECT COUNT(*) as listings_in_db FROM products.listings;

-- Check sample of listings in database
SELECT
    id,
    stockx_listing_id,
    status,
    amount,
    created_at
FROM products.listings
ORDER BY created_at DESC
LIMIT 5;