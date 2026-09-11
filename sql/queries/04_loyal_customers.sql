-- Answer:
-- No customers have more than 25 orders in the current dataset.

SELECT
    c.id AS customer_id,
    COUNT(o.id) AS order_count,
    SUM(o.qty * d.price_inr) AS total_spend_inr
FROM customers AS c
JOIN orders AS o
    ON o.customer_id = c.id
JOIN drinks AS d
    ON d.id = o.drink_id
GROUP BY c.id
HAVING COUNT(o.id) > 25
ORDER BY order_count DESC, customer_id;
