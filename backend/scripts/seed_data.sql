-- =====================================================================
-- Script de poblacion completa para el sistema de facturacion electronica
-- Ejecutar en el editor SQL de Supabase
-- =====================================================================

-- Usuarios (passwords hasheados con bcrypt)
-- admin123, contador123, vendedor123, ana123
INSERT INTO users (nombre, email, password_hash, rol, activo) VALUES
('Carlos Administrador', 'admin@empresa.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'administrador', TRUE),
('Maria Contadora', 'contador@empresa.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'contador', TRUE),
('Juan Vendedor', 'vendedor@empresa.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'vendedor', TRUE),
('Ana Vendedora', 'ana@empresa.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'vendedor', TRUE)
ON CONFLICT (email) DO NOTHING;

-- Clientes
INSERT INTO clients (tipo_documento, numero_documento, nombre_razon_social, direccion, email, telefono) VALUES
('RUC', '20123456789', 'Inversiones Generales S.A.C.', 'Av. Principal 123, Lima', 'contacto@inversiones.com', '01-555-1234'),
('RUC', '20567890123', 'Comercializadora del Norte E.I.R.L.', 'Jr. Comercio 456, Trujillo', 'ventas@comercializadora.com', '044-123-456'),
('DNI', '12345678', 'Pedro Perez Lopez', 'Calle Los Olivos 789, Lima', 'pedro.perez@gmail.com', '999-888-777'),
('RUC', '20678901234', 'Tecnologia Avanzada S.A.', 'Av. Industrial 321, Arequipa', 'info@tecnologiaavanzada.com', '054-456-789'),
('DNI', '87654321', 'Luisa Martinez Sanchez', 'Av. Brasil 654, Lima', 'luisa.martinez@yahoo.com', '999-777-888'),
('RUC', '20901234567', 'Constructora del Sur S.A.C.', 'Av. Sur 987, Cusco', 'proyectos@constructorasur.com', '084-234-567'),
('DNI', '45678901', 'Roberto Garcia Torres', 'Calle San Martin 123, Piura', 'roberto.garcia@hotmail.com', '999-666-555'),
('RUC', '20345678901', 'Importadora Global E.I.R.L.', 'Av. Espana 456, Chiclayo', 'ventas@importadoraglobal.com', '074-345-678')
ON CONFLICT (numero_documento) DO NOTHING;

-- Facturas e Items (con IDs de usuarios y clientes)
-- Nota: Los IDs de usuarios y clientes deben obtenerse dinamicamente

-- Factura 1: Pagada - Inversiones Generales
WITH admin_id AS (SELECT id FROM users WHERE email = 'admin@empresa.com' LIMIT 1),
     client1_id AS (SELECT id FROM clients WHERE numero_documento = '20123456789' LIMIT 1)
INSERT INTO invoices (serie, numero, client_id, fecha_emision, fecha_vencimiento, subtotal, igv, total, estado, created_by)
SELECT 'F001', 1, client1_id.id, CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE - INTERVAL '15 days', 19750.00, 3555.00, 23305.00, 'pagada', admin_id.id
FROM admin_id, client1_id
WHERE NOT EXISTS (SELECT 1 FROM invoices WHERE serie = 'F001' AND numero = 1);

-- Items Factura 1
WITH invoice_id AS (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 1 LIMIT 1)
INSERT INTO invoice_items (invoice_id, descripcion, cantidad, precio_unitario, subtotal)
SELECT invoice_id.id, 'Laptop HP ProBook', 5, 3500.00, 17500.00 FROM invoice_id
WHERE NOT EXISTS (SELECT 1 FROM invoice_items WHERE descripcion = 'Laptop HP ProBook' AND invoice_id = (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 1));

WITH invoice_id AS (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 1 LIMIT 1)
INSERT INTO invoice_items (invoice_id, descripcion, cantidad, precio_unitario, subtotal)
SELECT invoice_id.id, 'Monitor LG 24 pulgadas', 5, 450.00, 2250.00 FROM invoice_id
WHERE NOT EXISTS (SELECT 1 FROM invoice_items WHERE descripcion = 'Monitor LG 24 pulgadas' AND invoice_id = (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 1));

-- Pago Factura 1
WITH invoice_id AS (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 1 LIMIT 1),
     admin_id AS (SELECT id FROM users WHERE email = 'admin@empresa.com' LIMIT 1)
INSERT INTO payments (invoice_id, fecha_pago, monto, metodo_pago, registrado_por)
SELECT invoice_id.id, CURRENT_DATE - INTERVAL '20 days', 23305.00, 'transferencia', admin_id.id
FROM invoice_id, admin_id
WHERE NOT EXISTS (SELECT 1 FROM payments WHERE invoice_id = (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 1));

-- Factura 2: Pagada - Comercializadora del Norte
WITH admin_id AS (SELECT id FROM users WHERE email = 'admin@empresa.com' LIMIT 1),
     client2_id AS (SELECT id FROM clients WHERE numero_documento = '20567890123' LIMIT 1)
INSERT INTO invoices (serie, numero, client_id, fecha_emision, fecha_vencimiento, subtotal, igv, total, estado, created_by)
SELECT 'F001', 2, client2_id.id, CURRENT_DATE - INTERVAL '25 days', CURRENT_DATE - INTERVAL '10 days', 15000.00, 2700.00, 17700.00, 'pagada', admin_id.id
FROM admin_id, client2_id
WHERE NOT EXISTS (SELECT 1 FROM invoices WHERE serie = 'F001' AND numero = 2);

-- Items Factura 2
WITH invoice_id AS (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 2 LIMIT 1)
INSERT INTO invoice_items (invoice_id, descripcion, cantidad, precio_unitario, subtotal)
SELECT invoice_id.id, 'Escritorio ergonómico', 10, 850.00, 8500.00 FROM invoice_id
WHERE NOT EXISTS (SELECT 1 FROM invoice_items WHERE descripcion = 'Escritorio ergonómico' AND invoice_id = (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 2));

WITH invoice_id AS (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 2 LIMIT 1)
INSERT INTO invoice_items (invoice_id, descripcion, cantidad, precio_unitario, subtotal)
SELECT invoice_id.id, 'Silla ejecutiva', 10, 650.00, 6500.00 FROM invoice_id
WHERE NOT EXISTS (SELECT 1 FROM invoice_items WHERE descripcion = 'Silla ejecutiva' AND invoice_id = (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 2));

-- Pago Factura 2
WITH invoice_id AS (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 2 LIMIT 1),
     admin_id AS (SELECT id FROM users WHERE email = 'admin@empresa.com' LIMIT 1)
INSERT INTO payments (invoice_id, fecha_pago, monto, metodo_pago, registrado_por)
SELECT invoice_id.id, CURRENT_DATE - INTERVAL '15 days', 17700.00, 'transferencia', admin_id.id
FROM invoice_id, admin_id
WHERE NOT EXISTS (SELECT 1 FROM payments WHERE invoice_id = (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 2));

-- Factura 3: Pendiente - Pedro Perez
WITH admin_id AS (SELECT id FROM users WHERE email = 'admin@empresa.com' LIMIT 1),
     client3_id AS (SELECT id FROM clients WHERE numero_documento = '12345678' LIMIT 1)
INSERT INTO invoices (serie, numero, client_id, fecha_emision, fecha_vencimiento, subtotal, igv, total, estado, created_by)
SELECT 'F001', 3, client3_id.id, CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE + INTERVAL '5 days', 1900.00, 342.00, 2242.00, 'pendiente', admin_id.id
FROM admin_id, client3_id
WHERE NOT EXISTS (SELECT 1 FROM invoices WHERE serie = 'F001' AND numero = 3);

-- Items Factura 3
WITH invoice_id AS (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 3 LIMIT 1)
INSERT INTO invoice_items (invoice_id, descripcion, cantidad, precio_unitario, subtotal)
SELECT invoice_id.id, 'Impresora multifuncional Epson', 1, 1200.00, 1200.00 FROM invoice_id
WHERE NOT EXISTS (SELECT 1 FROM invoice_items WHERE descripcion = 'Impresora multifuncional Epson' AND invoice_id = (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 3));

WITH invoice_id AS (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 3 LIMIT 1)
INSERT INTO invoice_items (invoice_id, descripcion, cantidad, precio_unitario, subtotal)
SELECT invoice_id.id, 'Cartuchos de tinta (pack)', 2, 350.00, 700.00 FROM invoice_id
WHERE NOT EXISTS (SELECT 1 FROM invoice_items WHERE descripcion = 'Cartuchos de tinta (pack)' AND invoice_id = (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 3));

-- Factura 4: Vencida - Tecnologia Avanzada
WITH admin_id AS (SELECT id FROM users WHERE email = 'admin@empresa.com' LIMIT 1),
     client4_id AS (SELECT id FROM clients WHERE numero_documento = '20678901234' LIMIT 1)
INSERT INTO invoices (serie, numero, client_id, fecha_emision, fecha_vencimiento, subtotal, igv, total, estado, created_by)
SELECT 'F001', 4, client4_id.id, CURRENT_DATE - INTERVAL '15 days', CURRENT_DATE - INTERVAL '2 days', 19400.00, 3492.00, 22892.00, 'vencida', admin_id.id
FROM admin_id, client4_id
WHERE NOT EXISTS (SELECT 1 FROM invoices WHERE serie = 'F001' AND numero = 4);

-- Items Factura 4
WITH invoice_id AS (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 4 LIMIT 1)
INSERT INTO invoice_items (invoice_id, descripcion, cantidad, precio_unitario, subtotal)
SELECT invoice_id.id, 'Servidor Dell PowerEdge', 2, 8500.00, 17000.00 FROM invoice_id
WHERE NOT EXISTS (SELECT 1 FROM invoice_items WHERE descripcion = 'Servidor Dell PowerEdge' AND invoice_id = (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 4));

WITH invoice_id AS (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 4 LIMIT 1)
INSERT INTO invoice_items (invoice_id, descripcion, cantidad, precio_unitario, subtotal)
SELECT invoice_id.id, 'RAID Controller', 2, 1200.00, 2400.00 FROM invoice_id
WHERE NOT EXISTS (SELECT 1 FROM invoice_items WHERE descripcion = 'RAID Controller' AND invoice_id = (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 4));

-- Factura 5: Pendiente - Luisa Martinez
WITH admin_id AS (SELECT id FROM users WHERE email = 'admin@empresa.com' LIMIT 1),
     client5_id AS (SELECT id FROM clients WHERE numero_documento = '87654321' LIMIT 1)
INSERT INTO invoices (serie, numero, client_id, fecha_emision, fecha_vencimiento, subtotal, igv, total, estado, created_by)
SELECT 'F001', 5, client5_id.id, CURRENT_DATE - INTERVAL '10 days', CURRENT_DATE + INTERVAL '20 days', 13650.00, 2457.00, 16107.00, 'pendiente', admin_id.id
FROM admin_id, client5_id
WHERE NOT EXISTS (SELECT 1 FROM invoices WHERE serie = 'F001' AND numero = 5);

-- Items Factura 5
WITH invoice_id AS (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 5 LIMIT 1)
INSERT INTO invoice_items (invoice_id, descripcion, cantidad, precio_unitario, subtotal)
SELECT invoice_id.id, 'Tablet iPad Pro', 3, 4200.00, 12600.00 FROM invoice_id
WHERE NOT EXISTS (SELECT 1 FROM invoice_items WHERE descripcion = 'Tablet iPad Pro' AND invoice_id = (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 5));

WITH invoice_id AS (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 5 LIMIT 1)
INSERT INTO invoice_items (invoice_id, descripcion, cantidad, precio_unitario, subtotal)
SELECT invoice_id.id, 'Apple Pencil', 3, 350.00, 1050.00 FROM invoice_id
WHERE NOT EXISTS (SELECT 1 FROM invoice_items WHERE descripcion = 'Apple Pencil' AND invoice_id = (SELECT id FROM invoices WHERE serie = 'F001' AND numero = 5));

-- Configuracion de la aplicacion
INSERT INTO app_settings (clave, valor) VALUES
('empresa_razon_social', 'Mi Empresa S.A.C.'),
('empresa_ruc', '20123456789'),
('empresa_direccion', 'Av. Principal 123, Lima, Peru'),
('empresa_telefono', '01-555-1234'),
('empresa_email', 'contacto@miempresa.com'),
('igv_porcentaje', '18'),
('factura_serie', 'F001'),
('factura_correlativo', '100'),
('moneda', 'PEN')
ON CONFLICT (clave) DO NOTHING;
