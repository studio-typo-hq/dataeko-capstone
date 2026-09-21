-- Answer: 80000 orders have no delivery row.
SELECT count(*) AS undelivered_orders
FROM orders o
LEFT JOIN deliveries d ON d.order_id = o.id
WHERE d.id IS NULL;