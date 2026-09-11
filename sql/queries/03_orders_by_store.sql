-- Order volume and quantity by store.
SELECT
    s.id,
    s.name,
    COUNT(o.id) AS order_count,
    COALESCE(SUM(o.qty), 0) AS total_quantity
FROM stores s
LEFT JOIN orders o ON o.store_id = s.id
GROUP BY s.id, s.name
ORDER BY order_count DESC;
