-- Top 10 drinks by total quantity sold.
SELECT
    d.id,
    d.name,
    SUM(o.qty) AS total_quantity
FROM orders o
JOIN drinks d ON d.id = o.drink_id
GROUP BY d.id, d.name
ORDER BY total_quantity DESC
LIMIT 10;
