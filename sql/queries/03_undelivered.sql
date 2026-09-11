-- Answer: 80000 orders have no delivery row in the original 400000-order seed.
-- The current database returns 80200 because Phase 1 added 200 valid orders without delivery rows.

SELECT COUNT(*) AS undelivered_orders
FROM orders o
LEFT JOIN deliveries d ON d.order_id = o.id
WHERE d.id IS NULL;
