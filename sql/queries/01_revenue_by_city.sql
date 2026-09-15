-- Answer: Total collected-order revenue per city, highest first.

SELECT
    s.city,
    SUM(o.qty * d.price_inr) AS total_revenue
FROM orders AS o
JOIN drinks AS d
    ON d.id = o.drink_id
JOIN stores AS s
    ON s.id = o.store_id
WHERE o.status = 'collected'
GROUP BY s.city
ORDER BY total_revenue DESC;
