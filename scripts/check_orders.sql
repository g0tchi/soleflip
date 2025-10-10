-- Check recent orders in the database
-- Run this to see if today's sales were captured

-- 1. Check all orders from today (2025-10-08)
SELECT
    id,
    stockx_order_number,
    status,
    amount,
    currency_code,
    sold_at,
    gross_sale,
    net_proceeds,
    payout_received,
    created_at,
    stockx_created_at
FROM transactions.orders
WHERE DATE(created_at) = '2025-10-08'
   OR DATE(sold_at) = '2025-10-08'
   OR DATE(stockx_created_at) = '2025-10-08'
ORDER BY created_at DESC;

-- 2. Check all orders from the last 7 days
SELECT
    DATE(COALESCE(sold_at, stockx_created_at, created_at)) as order_date,
    COUNT(*) as order_count,
    SUM(amount) as total_amount,
    status
FROM transactions.orders
WHERE COALESCE(sold_at, stockx_created_at, created_at) >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(COALESCE(sold_at, stockx_created_at, created_at)), status
ORDER BY order_date DESC;

-- 3. Check the most recent orders regardless of date
SELECT
    id,
    stockx_order_number,
    status,
    amount,
    sold_at,
    created_at,
    stockx_created_at
FROM transactions.orders
ORDER BY created_at DESC
LIMIT 10;

-- 4. Total count of orders
SELECT COUNT(*) as total_orders FROM transactions.orders;
