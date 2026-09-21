-- Answer: revenue per city for collected orders, highest first.
SELECT s.city, SUM(o.qty * d.price_inr) AS revenue_inr
FROM orders o
JOIN drinks d ON d.id = o.drink_id
JOIN stores s ON s.id = o.store_id
WHERE o.status = 'collected'
GROUP BY s.city
ORDER BY revenue_inr DESC;