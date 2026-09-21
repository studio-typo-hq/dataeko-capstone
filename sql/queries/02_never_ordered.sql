-- Answer: turmeric latte, rose cardamom, and affogato.
SELECT d.name
FROM drinks d
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.drink_id = d.id)
ORDER BY d.id;