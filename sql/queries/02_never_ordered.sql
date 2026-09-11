-- Answer: 3 drinks — turmeric latte, rose cardamom, affogato

SELECT d.id, d.name
FROM drinks d
LEFT JOIN orders o
    ON d.id = o.drink_id
WHERE o.drink_id IS NULL
ORDER BY d.name;
