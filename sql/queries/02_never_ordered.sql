-- Answer: turmeric latte, rose cardamom, affogato.

SELECT
    d.name
FROM drinks AS d
LEFT JOIN orders AS o
    ON o.drink_id = d.id
WHERE o.id IS NULL
ORDER BY d.name;
