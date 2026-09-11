-- Answer:
-- Bengaluru: 15600780 INR
-- Hyderabad: 15599610 INR
-- Pune: 9333560 INR
-- Chennai: 9333100 INR
-- Delhi: 4666810 INR
-- Mumbai: 4666550 INR

SELECT
    s.city,
    SUM(o.qty * d.price_inr) AS total_revenue_inr
FROM orders AS o
JOIN drinks AS d
    ON d.id = o.drink_id
JOIN stores AS s
    ON s.id = o.store_id
WHERE o.status = 'collected'
GROUP BY s.city
ORDER BY total_revenue_inr DESC;
