-- Customers with more than 25 orders, showing order count and total spend

SELECT
    o.customer_id,
    COUNT(*) AS order_count,
    SUM(o.qty * d.price_inr) AS total_spend
FROM orders o
JOIN drinks d
    ON o.drink_id = d.id
GROUP BY o.customer_id
HAVING COUNT(*) > 25
ORDER BY order_count DESC;
