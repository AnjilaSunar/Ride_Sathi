-- Real Nepal Bike Fleet Setup for RideSathi
-- Run this if you need to reset the bikes table with real data

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE ridesathi_db.bookings;
TRUNCATE ridesathi_db.bikes;
SET FOREIGN_KEY_CHECKS = 1;

INSERT INTO ridesathi_db.bikes (model, category, price_per_day, image, status, description) VALUES 
('Honda Dio', 'Scooter', 1300, '/static/assets/image/honda_dio_rental_1774704737092.png', 'available', 'Reliable and fuel-efficient urban scooter.'),
('TVS Ntorq 125', 'Scooter', 1500, '/static/assets/image/tvs_ntorq_rental_1774704757821.png', 'available', 'Sporty and powerful 125cc scooter.'),
('NIU N-Series', 'Electric', 1800, '/static/assets/image/niu_electric_scooter_1774704779461.png', 'available', 'Modern smart electric scooter for urban commuting.'),
('Yatri Project One', 'Electric', 6000, '/static/assets/image/yatri_project_one_nepal_1774704796428.png', 'available', 'Premium Nepali engineering, high-performance electric bike.'),
('Bajaj Pulsar NS200', 'Standard', 2500, '/static/assets/image/pulsar_ns200_rental_1774704818476.png', 'available', 'High-performance naked street bike for Nepal roads.'),
('Royal Enfield Classic 350', 'Standard', 3500, '/static/assets/image/royal_enfield_classic_350_rental_1774704843243.png', 'available', 'Timeless retro cruiser, perfect for highway rides.'),
('Hero X-pulse 200', 'Dirt/Off-road', 2200, '/static/assets/image/hero_xpulse_200_rental_1774704860350.png', 'available', 'Agile adventure bike for versatile terrains.'),
('Royal Enfield Himalayan 411', 'Dirt/Off-road', 4500, '/static/assets/image/royal_enfield_himalayan_rental_1774704881313.png', 'available', 'Rugged adventure tourer for tough mountain roads.');
