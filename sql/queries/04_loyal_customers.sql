-- Answer: 0 customers currently have more than 25 orders.

SELECT
    c.id,
    c.name,
    COUNT(o.id) AS order_count,
    SUM(o.qty * d.price_inr) AS total_spend
FROM customers c
JOIN orders o ON o.customer_id = c.id
JOIN drinks d ON d.id = o.drink_id
GROUP BY c.id, c.name
HAVING COUNT(o.id) > 25
ORDER BY order_count DESC, c.id;
