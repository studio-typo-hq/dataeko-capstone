-- Answer: 80000 orders have no delivery row.

SELECT
    COUNT(*) AS undelivered_orders
FROM orders AS o
LEFT JOIN deliveries AS d
    ON d.order_id = o.id
WHERE d.id IS NULL;
