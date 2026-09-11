-- Answer: Customers with more than 25 orders, showing order count and total spend.

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
ORDER BY order_count DESC;
