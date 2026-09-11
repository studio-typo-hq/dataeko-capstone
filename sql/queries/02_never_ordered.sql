-- Answer: Drinks that have never appeared in any order.

SELECT
    d.id,
    d.name
FROM drinks d
LEFT JOIN orders o ON o.drink_id = d.id
WHERE o.id IS NULL
ORDER BY d.id;
