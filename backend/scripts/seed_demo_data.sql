
-- Script de SQL para generar datos de demostración
-- Ejecutar en el editor SQL de Supabase

DO $$
DECLARE
    v_admin_user_id UUID;
    v_next_invoice_num INTEGER;
    v_client_rec RECORD;
    v_invoice_rec RECORD;
    v_num_invoices INTEGER;
    i INTEGER;
    v_invoice_id UUID;
    v_fecha_emision DATE;
    v_fecha_vencimiento DATE;
    v_subtotal NUMERIC(12,2);
    v_igv NUMERIC(12,2);
    v_total NUMERIC(12,2);
    v_estado TEXT;
    v_fecha_pago DATE;
    v_num_items INTEGER;
    j INTEGER;
    v_item_descripcion TEXT;
    v_item_cantidad NUMERIC(10,2);
    v_item_precio_unitario NUMERIC(12,2);
    v_item_subtotal NUMERIC(12,2);
    v_fecha_pago_final DATE;
    v_metodo_pago TEXT;
BEGIN
    -- 1. Obtener el ID del usuario administrador
    SELECT id INTO v_admin_user_id FROM users WHERE rol = 'ADMINISTRADOR' LIMIT 1;
    IF v_admin_user_id IS NULL THEN
        RAISE EXCEPTION 'No existe un usuario administrador. Crea uno primero.';
    END IF;

    -- 2. Borrar datos de demostración existentes
    RAISE NOTICE 'Borrando datos de demostración existentes...';
    DELETE FROM payments p
    WHERE p.invoice_id IN (SELECT id FROM invoices WHERE client_id IN (SELECT id FROM clients WHERE nombre_razon_social LIKE 'Demo - %'));
    DELETE FROM invoice_items ii
    WHERE ii.invoice_id IN (SELECT id FROM invoices WHERE client_id IN (SELECT id FROM clients WHERE nombre_razon_social LIKE 'Demo - %'));
    DELETE FROM invoices i
    WHERE i.client_id IN (SELECT id FROM clients WHERE nombre_razon_social LIKE 'Demo - %');
    DELETE FROM clients c WHERE c.nombre_razon_social LIKE 'Demo - %';

    -- 3. Obtener el próximo número de factura
    SELECT COALESCE(MAX(numero), 0) + 1 INTO v_next_invoice_num FROM invoices WHERE serie = 'F001';

    -- 4. Crear 30 clientes de demostración
    RAISE NOTICE 'Creando clientes de demostración...';
    CREATE TEMP TABLE temp_clients (
        id UUID,
        perfil TEXT
    );

    WITH nombres_personas AS (
        SELECT unnest(ARRAY[
            'Juan Pérez', 'María Gómez', 'Carlos Rodríguez', 'Ana López', 'Luis Fernández',
            'Laura García', 'Pedro Martínez', 'Sofía Sánchez', 'Diego González', 'Valentina Ruiz',
            'Jorge Díaz', 'Camila Torres', 'Mateo Flores', 'Isabella Castillo', 'Sebastián Cruz',
            'Martina Morales', 'Leonardo Ortiz', 'Victoria Medina', 'Daniel Gutiérrez', 'Lucía Romero'
        ]) AS nombre
    ),
    nombres_empresas AS (
        SELECT unnest(ARRAY[
            'Comercial ABC S.A.C.', 'Servicios Integrales E.I.R.L.', 'Inversiones XYZ S.R.L.',
            'Tecnología Digital S.A.', 'Distribuidora del Sur S.A.C.', 'Consultoría Estratégica E.I.R.L.',
            'Constructora Nova S.R.L.', 'Importadora Global S.A.', 'Agropecuaria Valle S.A.C.',
            'Transporte y Logística E.I.R.L.'
        ]) AS nombre
    ),
    calles AS (
        SELECT unnest(ARRAY['San Juan', 'Principal', 'Los Olivos', 'Javier Prado', 'Arequipa']) AS calle
    ),
    nuevos_clientes AS (
        INSERT INTO clients (
            id, tipo_documento, numero_documento, nombre_razon_social, direccion, email, telefono, created_at
        )
        SELECT
            gen_random_uuid() AS id,
            CASE WHEN random() < 0.6 THEN 'DNI'::tipo_documento ELSE 'RUC'::tipo_documento END AS tipo_documento,
            CASE
                WHEN random() < 0.6 THEN (floor(random() * 90000000 + 10000000))::text
                ELSE '20' || (floor(random() * 90000000 + 10000000))::text
            END AS numero_documento,
            'Demo - ' || CASE
                WHEN random() < 0.6 THEN (SELECT nombre FROM nombres_personas ORDER BY random() LIMIT 1)
                ELSE (SELECT nombre FROM nombres_empresas ORDER BY random() LIMIT 1)
            END || ' #' || row_number() OVER ()::text AS nombre_razon_social,
            'Av. ' || (SELECT calle FROM calles ORDER BY random() LIMIT 1) || ' ' || (floor(random() * 9900 + 100))::text || ', Lima' AS direccion,
            'demo.' || encode(gen_random_bytes(4), 'hex') || '@example.com' AS email,
            '9' || (floor(random() * 90000000 + 10000000))::text AS telefono,
            NOW() - (random() * INTERVAL '365 days') AS created_at
        FROM generate_series(1, 30)
        ON CONFLICT (numero_documento) DO NOTHING
        RETURNING id
    )
    INSERT INTO temp_clients (id, perfil)
    SELECT
        id,
        CASE
            WHEN row_number() OVER () <= 12 THEN 'buen'
            WHEN row_number() OVER () <= 22 THEN 'intermedio'
            ELSE 'malo'
        END AS perfil
    FROM nuevos_clientes;

    -- 5. Crear facturas para cada cliente
    RAISE NOTICE 'Creando facturas...';
    CREATE TEMP TABLE temp_invoices (
        id UUID,
        client_id UUID,
        fecha_emision DATE,
        fecha_vencimiento DATE,
        total NUMERIC(12,2),
        estado TEXT,
        fecha_pago DATE
    );

    FOR v_client_rec IN SELECT id, perfil FROM temp_clients LOOP
        v_num_invoices := floor(random() * 7 + 2)::INTEGER;
        FOR i IN 1..v_num_invoices LOOP
            v_invoice_id := gen_random_uuid();
            v_fecha_emision := (CURRENT_DATE - (random() * INTERVAL '180 days'))::DATE;
            v_fecha_vencimiento := ((v_fecha_emision + (floor(random() * 24 + 7) * INTERVAL '1 day'))::DATE);
            v_subtotal := 0;

            -- Determinar estado y fecha de pago
            IF v_client_rec.perfil = 'buen' THEN
                IF random() < 0.9 THEN
                    v_estado := 'PAGADA';
                    v_fecha_pago := ((v_fecha_vencimiento + (floor(random() * 5 - 2) * INTERVAL '1 day'))::DATE);
                ELSE
                    v_estado := 'PENDIENTE';
                    v_fecha_pago := NULL;
                END IF;
            ELSIF v_client_rec.perfil = 'intermedio' THEN
                CASE
                    WHEN random() < 0.5 THEN
                        v_estado := 'PAGADA';
                        v_fecha_pago := ((v_fecha_vencimiento + (floor(random() * 31) * INTERVAL '1 day'))::DATE);
                    WHEN random() < 0.8 THEN
                        v_estado := 'VENCIDA';
                        v_fecha_pago := NULL;
                    ELSE
                        v_estado := 'PENDIENTE';
                        v_fecha_pago := NULL;
                END CASE;
            ELSE
                CASE
                    WHEN random() < 0.2 THEN
                        v_estado := 'PAGADA';
                        v_fecha_pago := ((v_fecha_vencimiento + (floor(random() * 61 + 30) * INTERVAL '1 day'))::DATE);
                    WHEN random() < 0.8 THEN
                        v_estado := 'VENCIDA';
                        v_fecha_pago := NULL;
                    ELSE
                        v_estado := 'PENDIENTE';
                        v_fecha_pago := NULL;
                END CASE;
            END IF;

            -- Ajustar estado si está pendiente y ya venció
            IF v_estado = 'PENDIENTE' AND CURRENT_DATE > v_fecha_vencimiento THEN
                v_estado := 'VENCIDA';
            END IF;

            -- Insertar factura primero para poder asociar los items
            INSERT INTO invoices (
                id, serie, numero, client_id, fecha_emision, fecha_vencimiento, subtotal, igv, total, estado, created_by, created_at
            ) VALUES (
                v_invoice_id,
                'F001',
                v_next_invoice_num,
                v_client_rec.id,
                v_fecha_emision,
                v_fecha_vencimiento,
                0,
                0,
                0,
                v_estado::estado_factura,
                v_admin_user_id,
                v_fecha_emision::TIMESTAMP
            );

            -- Crear items para la factura
            v_num_items := floor(random() * 4 + 1)::INTEGER;
            FOR j IN 1..v_num_items LOOP
                SELECT descripcion INTO v_item_descripcion FROM (
                    SELECT unnest(ARRAY[
                        'Consultoría', 'Desarrollo de software', 'Mantenimiento', 'Licencia anual',
                        'Servicio de soporte', 'Capacitación', 'Instalación de equipos', 'Reparación',
                        'Venta de hardware', 'Venta de software'
                    ]) AS descripcion
                ) AS items ORDER BY random() LIMIT 1;
                v_item_cantidad := CAST((floor((random() * 9 + 1) * 100)) / 100.0 AS NUMERIC(10,2));
                v_item_precio_unitario := CAST((floor((random() * 1950 + 50) * 100)) / 100.0 AS NUMERIC(12,2));
                v_item_subtotal := CAST((floor((v_item_cantidad * v_item_precio_unitario) * 100)) / 100.0 AS NUMERIC(12,2));
                v_subtotal := v_subtotal + v_item_subtotal;

                INSERT INTO invoice_items (
                    id, invoice_id, descripcion, cantidad, precio_unitario, subtotal
                ) VALUES (
                    gen_random_uuid(),
                    v_invoice_id,
                    v_item_descripcion,
                    v_item_cantidad,
                    v_item_precio_unitario,
                    v_item_subtotal
                );
            END LOOP;

            v_igv := CAST((floor((v_subtotal * 0.18) * 100)) / 100.0 AS NUMERIC(12,2));
            v_total := CAST((floor((v_subtotal + v_igv) * 100)) / 100.0 AS NUMERIC(12,2));

            UPDATE invoices
            SET subtotal = v_subtotal,
                igv = v_igv,
                total = v_total,
                estado = v_estado::estado_factura
            WHERE id = v_invoice_id;

            -- Guardar factura en temp table
            INSERT INTO temp_invoices (id, client_id, fecha_emision, fecha_vencimiento, total, estado, fecha_pago)
            VALUES (v_invoice_id, v_client_rec.id, v_fecha_emision, v_fecha_vencimiento, v_total, v_estado, v_fecha_pago);

            v_next_invoice_num := v_next_invoice_num + 1;
        END LOOP;
    END LOOP;

    -- 6. Crear pagos para facturas pagadas
    RAISE NOTICE 'Creando pagos...';
    FOR v_invoice_rec IN SELECT id, total, fecha_pago FROM temp_invoices WHERE estado = 'PAGADA' LOOP
        v_fecha_pago_final := CASE WHEN v_invoice_rec.fecha_pago <= CURRENT_DATE THEN v_invoice_rec.fecha_pago ELSE CURRENT_DATE END;
        v_metodo_pago := (ARRAY['transferencia', 'efectivo', 'tarjeta'])[floor(random() * 3 + 1)];

        INSERT INTO payments (
            id, invoice_id, fecha_pago, monto, metodo_pago, registrado_por, created_at
        ) VALUES (
            gen_random_uuid(),
            v_invoice_rec.id,
            v_fecha_pago_final,
            v_invoice_rec.total,
            v_metodo_pago,
            v_admin_user_id,
            v_fecha_pago_final::TIMESTAMP
        );
    END LOOP;

    -- Limpiar tablas temporales
    DROP TABLE temp_clients;
    DROP TABLE temp_invoices;

    RAISE NOTICE '✅ Datos de demostración generados exitosamente!';
    RAISE NOTICE 'Clientes creados: %', (SELECT COUNT(*) FROM clients WHERE nombre_razon_social LIKE 'Demo - %');
    RAISE NOTICE 'Facturas creadas: %', (SELECT COUNT(*) FROM invoices WHERE client_id IN (SELECT id FROM clients WHERE nombre_razon_social LIKE 'Demo - %'));
    RAISE NOTICE 'Items creados: %', (SELECT COUNT(*) FROM invoice_items WHERE invoice_id IN (SELECT id FROM invoices WHERE client_id IN (SELECT id FROM clients WHERE nombre_razon_social LIKE 'Demo - %')));
    RAISE NOTICE 'Pagos creados: %', (SELECT COUNT(*) FROM payments WHERE invoice_id IN (SELECT id FROM invoices WHERE client_id IN (SELECT id FROM clients WHERE nombre_razon_social LIKE 'Demo - %')));
END $$;
