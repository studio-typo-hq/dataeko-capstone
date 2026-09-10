-- Add an index to speed up lookups of orders by customer.
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
