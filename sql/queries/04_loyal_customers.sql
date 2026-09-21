-- Answer: customers with more than 25 orders and their total spend.
SELECT o.customer_id, count(*) AS order_count,
       SUM(o.qty * d.price_inr) AS total_spend_inr
FROM orders o
JOIN drinks d ON d.id = o.drink_id
GROUP BY o.customer_id
HAVING count(*) > 25
ORDER BY order_count DESC, o.customer_id;