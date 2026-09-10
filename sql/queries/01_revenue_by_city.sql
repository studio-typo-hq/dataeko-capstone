-- Answer: Bengaluru 15600780, Hyderabad 15599610, Pune 9333560,
-- Chennai 9333100, Delhi 4666810, Mumbai 4666550.

SELECT
    s.city,
    SUM(o.qty * d.price_inr) AS total_revenue
FROM orders o
JOIN drinks d ON d.id = o.drink_id
JOIN stores s ON s.id = o.store_id
WHERE o.status = 'collected'
GROUP BY s.city
ORDER BY total_revenue DESC;
