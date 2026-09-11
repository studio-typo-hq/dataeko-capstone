-- Find orders that do not have a delivery record.
SELECT
    o.id,
    o.customer_id,
    o.drink_id,
    o.store_id,
    o.ordered_at,
    o.status
FROM orders o
LEFT JOIN deliveries d ON d.order_id = o.id
WHERE d.order_id IS NULL
ORDER BY o.id;
