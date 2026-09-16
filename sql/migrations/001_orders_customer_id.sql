-- Add an index for customer-specific order lookups.
CREATE INDEX idx_orders_customer_id
ON orders(customer_id);
