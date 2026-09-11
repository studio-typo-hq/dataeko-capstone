-- Answer: 80,000 orders have no delivery row

SELECT COUNT(*) AS undelivered_orders
FROM orders o
LEFT JOIN deliveries d
    ON o.id = d.order_id
WHERE d.order_id IS NULL;
