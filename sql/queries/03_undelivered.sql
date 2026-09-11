-- Answer:
-- 80200 orders have no delivery row.

SELECT COUNT(*) AS orders_without_delivery
FROM orders AS o
LEFT JOIN deliveries AS d
    ON d.order_id = o.id
WHERE d.id IS NULL;
