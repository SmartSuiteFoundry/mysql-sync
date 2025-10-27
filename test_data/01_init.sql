-- Sample database schema for testing the sync
CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    company VARCHAR(255),
    status ENUM('active', 'inactive', 'pending') DEFAULT 'active',
    credit_limit DECIMAL(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_status (status)
);

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    order_date DATE NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status ENUM('pending', 'processing', 'shipped', 'delivered', 'cancelled') DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX idx_customer (customer_id),
    INDEX idx_order_number (order_number),
    INDEX idx_status (status)
);

-- Insert sample customers
INSERT INTO customers (customer_name, email, phone, company, status, credit_limit) VALUES
('John Smith', 'john.smith@example.com', '555-0101', 'Acme Corp', 'active', 5000.00),
('Jane Doe', 'jane.doe@example.com', '555-0102', 'Tech Solutions Inc', 'active', 10000.00),
('Bob Johnson', 'bob.johnson@example.com', '555-0103', 'Global Industries', 'active', 7500.00),
('Alice Williams', 'alice.williams@example.com', '555-0104', 'Innovation Labs', 'pending', 3000.00),
('Charlie Brown', 'charlie.brown@example.com', '555-0105', 'Enterprise Systems', 'inactive', 0.00);

-- Insert sample orders
INSERT INTO orders (customer_id, order_number, order_date, total_amount, status, notes) VALUES
(1, 'ORD-2024-001', '2024-01-15', 1250.00, 'delivered', 'Rush order completed on time'),
(1, 'ORD-2024-002', '2024-01-20', 750.50, 'delivered', NULL),
(2, 'ORD-2024-003', '2024-01-18', 3200.00, 'shipped', 'Large equipment order'),
(2, 'ORD-2024-004', '2024-02-01', 450.00, 'processing', NULL),
(3, 'ORD-2024-005', '2024-01-25', 1800.00, 'delivered', NULL),
(3, 'ORD-2024-006', '2024-02-05', 2100.00, 'pending', 'Awaiting payment confirmation'),
(4, 'ORD-2024-007', '2024-02-10', 890.00, 'pending', 'New customer order');
