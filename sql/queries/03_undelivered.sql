-- Answer: 80,000 orders have no delivery row.

SELECT
    COUNT(*) AS undelivered_orders
FROM orders o
LEFT JOIN deliveries del
    ON del.order_id = o.id
WHERE del.order_id IS NULL;

