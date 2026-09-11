-- Answer: Count of orders that do not have a delivery record.

SELECT
    COUNT(*) AS undelivered_orders
FROM orders o
LEFT JOIN deliveries d ON d.order_id = o.id
WHERE d.order_id IS NULL;
