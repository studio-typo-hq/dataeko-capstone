-- Answer: Total revenue per city, highest first

SELECT
    s.city,
    SUM(o.qty * d.price_inr) AS total_revenue
FROM orders o
JOIN drinks d
    ON o.drink_id = d.id
JOIN stores s
    ON o.store_id = s.id
WHERE o.status = 'collected'
GROUP BY s.city
ORDER BY total_revenue DESC;
