-- Answer:
-- 16 | turmeric latte
-- 17 | rose cardamom
-- 18 | affogato

SELECT
    d.id,
    d.name
FROM drinks AS d
LEFT JOIN orders AS o
    ON o.drink_id = d.id
WHERE o.id IS NULL
ORDER BY d.id;
