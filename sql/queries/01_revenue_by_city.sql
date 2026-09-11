-- Answer: Total revenue per city from collected orders, highest first.

SELECT
    s.city,
    SUM(o.qty * d.price_inr) AS total_revenue
FROM orders o
JOIN drinks d ON d.id = o.drink_id
JOIN stores s ON s.id = o.store_id
WHERE o.status = 'collected'
GROUP BY s.city
ORDER BY total_revenue DESC;
