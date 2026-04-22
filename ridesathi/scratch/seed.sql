-- Entry 1
INSERT INTO bookings (user_id, bike_id, start_date, end_date, total_days, total_cost, status, created_at, payment_status) 
VALUES (2, 1, '2026-04-14', '2026-04-15', 1, 2500, 'confirmed', '2026-04-12 10:00:00', 'paid');
SET @bid = LAST_INSERT_ID();
INSERT INTO payments (booking_id, user_id, amount, payment_status, transaction_id, payment_date) 
VALUES (@bid, 2, 2500, 'paid', 'FAKE-1111', '2026-04-12 10:00:00');
SET @pid = LAST_INSERT_ID();
INSERT INTO invoices (booking_id, payment_id, invoice_date) 
VALUES (@bid, @pid, '2026-04-12 10:00:00');

-- Entry 2
INSERT INTO bookings (user_id, bike_id, start_date, end_date, total_days, total_cost, status, created_at, payment_status) 
VALUES (4, 2, '2026-04-15', '2026-04-16', 1, 1500, 'confirmed', '2026-04-13 11:30:00', 'paid');
SET @bid = LAST_INSERT_ID();
INSERT INTO payments (booking_id, user_id, amount, payment_status, transaction_id, payment_date) 
VALUES (@bid, 4, 1500, 'paid', 'FAKE-2222', '2026-04-13 11:30:00');
SET @pid = LAST_INSERT_ID();
INSERT INTO invoices (booking_id, payment_id, invoice_date) 
VALUES (@bid, @pid, '2026-04-13 11:30:00');

-- Entry 3
INSERT INTO bookings (user_id, bike_id, start_date, end_date, total_days, total_cost, status, created_at, payment_status) 
VALUES (5, 3, '2026-04-16', '2026-04-18', 2, 3000, 'confirmed', '2026-04-14 09:15:00', 'paid');
SET @bid = LAST_INSERT_ID();
INSERT INTO payments (booking_id, user_id, amount, payment_status, transaction_id, payment_date) 
VALUES (@bid, 5, 3000, 'paid', 'FAKE-3333', '2026-04-14 09:15:00');
SET @pid = LAST_INSERT_ID();
INSERT INTO invoices (booking_id, payment_id, invoice_date) 
VALUES (@bid, @pid, '2026-04-14 09:15:00');

-- Entry 4
INSERT INTO bookings (user_id, bike_id, start_date, end_date, total_days, total_cost, status, created_at, payment_status) 
VALUES (2, 2, '2026-04-17', '2026-04-17', 1, 1500, 'confirmed', '2026-04-15 16:45:00', 'paid');
SET @bid = LAST_INSERT_ID();
INSERT INTO payments (booking_id, user_id, amount, payment_status, transaction_id, payment_date) 
VALUES (@bid, 2, 1500, 'paid', 'FAKE-4444', '2026-04-15 16:45:00');
SET @pid = LAST_INSERT_ID();
INSERT INTO invoices (booking_id, payment_id, invoice_date) 
VALUES (@bid, @pid, '2026-04-15 16:45:00');

-- Entry 5
INSERT INTO bookings (user_id, bike_id, start_date, end_date, total_days, total_cost, status, created_at, payment_status) 
VALUES (4, 1, '2026-04-18', '2026-04-20', 2, 5000, 'confirmed', '2026-04-16 14:20:00', 'paid');
SET @bid = LAST_INSERT_ID();
INSERT INTO payments (booking_id, user_id, amount, payment_status, transaction_id, payment_date) 
VALUES (@bid, 4, 5000, 'paid', 'FAKE-5555', '2026-04-16 14:20:00');
SET @pid = LAST_INSERT_ID();
INSERT INTO invoices (booking_id, payment_id, invoice_date) 
VALUES (@bid, @pid, '2026-04-16 14:20:00');

-- Entry 6
INSERT INTO bookings (user_id, bike_id, start_date, end_date, total_days, total_cost, status, created_at, payment_status) 
VALUES (5, 2, '2026-04-19', '2026-04-21', 2, 3000, 'confirmed', '2026-04-17 10:10:00', 'paid');
SET @bid = LAST_INSERT_ID();
INSERT INTO payments (booking_id, user_id, amount, payment_status, transaction_id, payment_date) 
VALUES (@bid, 5, 3000, 'paid', 'FAKE-6666', '2026-04-17 10:10:00');
SET @pid = LAST_INSERT_ID();
INSERT INTO invoices (booking_id, payment_id, invoice_date) 
VALUES (@bid, @pid, '2026-04-17 10:10:00');

-- Entry 7
INSERT INTO bookings (user_id, bike_id, start_date, end_date, total_days, total_cost, status, created_at, payment_status) 
VALUES (2, 3, '2026-04-20', '2026-04-22', 2, 3000, 'confirmed', '2026-04-18 12:00:00', 'paid');
SET @bid = LAST_INSERT_ID();
INSERT INTO payments (booking_id, user_id, amount, payment_status, transaction_id, payment_date) 
VALUES (@bid, 2, 3000, 'paid', 'FAKE-7777', '2026-04-18 12:00:00');
SET @pid = LAST_INSERT_ID();
INSERT INTO invoices (booking_id, payment_id, invoice_date) 
VALUES (@bid, @pid, '2026-04-18 12:00:00');

-- Entry 8
INSERT INTO bookings (user_id, bike_id, start_date, end_date, total_days, total_cost, status, created_at, payment_status) 
VALUES (4, 3, '2026-04-21', '2026-04-22', 1, 1500, 'confirmed', '2026-04-19 08:30:00', 'paid');
SET @bid = LAST_INSERT_ID();
INSERT INTO payments (booking_id, user_id, amount, payment_status, transaction_id, payment_date) 
VALUES (@bid, 4, 1500, 'paid', 'FAKE-8888', '2026-04-19 08:30:00');
SET @pid = LAST_INSERT_ID();
INSERT INTO invoices (booking_id, payment_id, invoice_date) 
VALUES (@bid, @pid, '2026-04-19 08:30:00');
