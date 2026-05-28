-- ============================================================================
-- FitoGestión — Script de MIGRACIÓN 002 (ejecutar en Supabase SQL Editor)
-- Asegura: la existencia de las columnas de regionalización en la base de datos
-- Corrige: función fn_generar_informe_inspeccion (añade RETURN faltante)
-- Nutre: base de datos con todos los cultivos, plagas, usuarios, predios,
--        lotes e inspecciones en un único script unificado y compatible con UUID.
-- ============================================================================

-- 1. Asegurar columnas de regionalización en usuarios
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS departamento VARCHAR(100);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS municipio VARCHAR(100);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS vereda VARCHAR(150);

-- 2. Asegurar columnas de regionalización y número de registro ICA en predios
ALTER TABLE predios ADD COLUMN IF NOT EXISTS departamento VARCHAR(100);
ALTER TABLE predios ADD COLUMN IF NOT EXISTS municipio VARCHAR(100);
ALTER TABLE predios ADD COLUMN IF NOT EXISTS vereda VARCHAR(150);
ALTER TABLE predios ADD COLUMN IF NOT EXISTS numero_registro_ica VARCHAR(50);

-- 3. Crear índices de búsqueda rápida por región (si no existen)
CREATE INDEX IF NOT EXISTS idx_predios_region ON predios(departamento, municipio);
CREATE INDEX IF NOT EXISTS idx_usuarios_region ON usuarios(departamento, municipio);

-- 4. Recrear función de informe corregida
CREATE OR REPLACE FUNCTION fn_generar_informe_inspeccion(p_inspeccion_id UUID)
RETURNS JSON AS $$
DECLARE
    v_informe JSON;
    v_total_plantas_evaluadas INT;
    v_total_plantas_enfermas INT;
    v_porcentaje_incidencia DECIMAL;
    v_nivel_alerta VARCHAR(50);
BEGIN
    -- Calcular totales
    SELECT 
        COALESCE(SUM(plantas_evaluadas), 0) INTO v_total_plantas_evaluadas
    FROM sub_inspecciones
    WHERE inspeccion_id = p_inspeccion_id;

    SELECT 
        COUNT(*) INTO v_total_plantas_enfermas
    FROM registro_plantas rp
    JOIN sub_inspecciones si ON rp.sub_inspeccion_id = si.id
    WHERE si.inspeccion_id = p_inspeccion_id AND rp.estado_planta IN ('enferma', 'muerta');

    -- Calcular incidencia
    IF v_total_plantas_evaluadas > 0 THEN
        v_porcentaje_incidencia := (v_total_plantas_enfermas::DECIMAL / v_total_plantas_evaluadas) * 100;
    ELSE
        v_porcentaje_incidencia := 0;
    END IF;

    -- Determinar nivel de alerta
    IF v_porcentaje_incidencia >= 15.0 THEN
        v_nivel_alerta := 'Crítico (Cuarentena Recomendada)';
    ELSIF v_porcentaje_incidencia >= 5.0 THEN
        v_nivel_alerta := 'Alerta (Tratamiento Requerido)';
    ELSE
        v_nivel_alerta := 'Normal (Monitoreo)';
    END IF;

    -- Construir JSON de respuesta
    SELECT json_build_object(
        'inspeccion_id', p_inspeccion_id,
        'fecha_generacion', NOW(),
        'plantas_evaluadas', v_total_plantas_evaluadas,
        'plantas_afectadas', v_total_plantas_enfermas,
        'incidencia_global_pct', ROUND(v_porcentaje_incidencia, 2),
        'nivel_alerta', v_nivel_alerta
    ) INTO v_informe;

    RETURN v_informe;
END;
$$ LANGUAGE plpgsql;

-- 5. Nutrir Catálogo de Cultivos (Completo, 1-10)
INSERT INTO cultivos (id, nombre, nombre_cientifico, variedad, descripcion, activo) VALUES
('c0011111-1111-1111-1111-111111111111', 'Cítricos', 'Citrus spp.', 'Limón Tahití', 'Cultivo de cítricos para exportación de limón y naranja dulce.', true),
('c0022222-2222-2222-2222-222222222222', 'Aguacate', 'Persea americana', 'Hass', 'Aguacate tipo Hass cultivado para mercados nacionales e internacionales.', true),
('c0033333-3333-3333-3333-333333333333', 'Café', 'Coffea arabica', 'Castillo', 'Café especial Castillo de alta resistencia a la roya.', true),
('c0044444-4444-4444-4444-444444444444', 'Cacao', 'Theobroma cacao', 'CCN51', 'Cacao de alta productividad y fermentación controlada.', true),
('c0055555-5555-5555-5555-555555555555', 'Plátano', 'Musa paradisiaca', 'Hartón', 'Plátano clon Hartón utilizado como sombrío temporal y producción.', true),
('c0066666-6666-6666-6666-666666666666', 'Papa', 'Solanum tuberosum', 'Pastusa Suprema', 'Cultivo de papa de clima frío para consumo nacional en zonas altoandinas.', true),
('c0077777-7777-7777-7777-777777777777', 'Maíz', 'Zea mays', 'ICA V-305', 'Maíz amarillo tradicional con alta tolerancia a la sequía.', true),
('c0088888-8888-8888-8888-888888888888', 'Caña de Azúcar', 'Saccharum officinarum', 'CC 85-92', 'Caña de azúcar de alto rendimiento sacaroso cultivada en el Valle del Cauca.', true),
('c0099999-9999-9999-9999-999999999999', 'Flores (Clavel)', 'Dianthus caryophyllus', 'Standard Pink', 'Cultivo ornamental de flores para exportación en la Sabana de Bogotá y Boyacá.', true),
('c0101010-1010-1010-1010-101010101010', 'Palma de Aceite', 'Elaeis guineensis', 'Tenera', 'Palma africana cultivada para extracción de aceite en zonas bajas.', true)
ON CONFLICT (id) DO NOTHING;

-- 6. Nutrir Catálogo de Plagas (Completo, 1-10)
INSERT INTO plagas (id, nombre_comun, nombre_cientifico, tipo, descripcion, activo) VALUES
('f0011111-1111-1111-1111-111111111111', 'Diaphorina citri (Psílido asiático)', 'Diaphorina citri', 'insecto', 'Vector de la bacteria Candidatus Liberibacter que causa el HLB de los cítricos.', true),
('f0022222-2222-2222-2222-222222222222', 'Pudrición del cogollo / Raíz', 'Phytophthora cinnamomi', 'hongo', 'Hongo patógeno que causa pudrición radicular en aguacate y cítricos.', true),
('f0033333-3333-3333-3333-333333333333', 'Broca del Café', 'Hypothenemus hampei', 'insecto', 'Plaga principal que perfora el grano de café afectando calidad y rendimiento.', true),
('f0044444-4444-4444-4444-444444444444', 'Moniliasis del Cacao', 'Moniliophthora roreri', 'hongo', 'Enfermedad limitante que pudre la mazorca de cacao internamente.', true),
('f0055555-5555-5555-5555-555555555555', 'Moko del Plátano', 'Ralstonia solanacearum', 'bacteria', 'Marchitez bacteriana sistémica que destruye plantas de musáceas.', true),
('f0066666-6666-6666-6666-666666666666', 'Gota / Tizón tardío de la Papa', 'Phytophthora infestans', 'hongo', 'Hongo devastador que destruye hojas y tubérculos en condiciones de alta humedad.', true),
('f0077777-7777-7777-7777-777777777777', 'Gusano Cogollero del Maíz', 'Spodoptera frugiperda', 'insecto', 'Plaga devoradora de hojas y cogollos que diezma plantaciones de maíz.', true),
('f0088888-8888-8888-8888-888888888888', 'Carbón de la Caña de Azúcar', 'Sporisorium scitamineum', 'hongo', 'Produce una estructura negra como látigo que inhibe el crecimiento y sacarosa de la caña.', true),
('f0099999-9999-9999-9999-999999999999', 'Nematodo del Nudo Radical', 'Meloidogyne incognita', 'nematodo', 'Parásito radicular que causa agallas debilitando flores y cultivos ornamentales.', true),
('f0101010-1010-1010-1010-101010101010', 'Marchitez Sorpresiva de la Palma', 'Phytomonas sp.', 'bacteria', 'Protozoario flagelado transmitido por chinches que seca la planta rápidamente.', true)
ON CONFLICT (id) DO NOTHING;

-- 7. Asociaciones Plaga-Cultivo (Completo)
INSERT INTO plaga_cultivo (plaga_id, cultivo_id) VALUES
('f0011111-1111-1111-1111-111111111111', 'c0011111-1111-1111-1111-111111111111'), -- Diaphorina en Cítricos
('f0022222-2222-2222-2222-222222222222', 'c0022222-2222-2222-2222-222222222222'), -- Phytophthora en Aguacate
('f0022222-2222-2222-2222-222222222222', 'c0011111-1111-1111-1111-111111111111'), -- Phytophthora en Cítricos
('f0033333-3333-3333-3333-333333333333', 'c0033333-3333-3333-3333-333333333333'), -- Broca en Café
('f0044444-4444-4444-4444-444444444444', 'c0044444-4444-4444-4444-444444444444'), -- Monilia en Cacao
('f0055555-5555-5555-5555-555555555555', 'c0055555-5555-5555-5555-555555555555'), -- Moko en Plátano
('f0066666-6666-6666-6666-666666666666', 'c0066666-6666-6666-6666-666666666666'), -- Gota en Papa
('f0077777-7777-7777-7777-777777777777', 'c0077777-7777-7777-7777-777777777777'), -- Cogollero en Maíz
('f0088888-8888-8888-8888-888888888888', 'c0088888-8888-8888-8888-888888888888'), -- Carbón en Caña
('f0099999-9999-9999-9999-999999999999', 'c0099999-9999-9999-9999-999999999999'), -- Nematodo en Clavel
('f0101010-1010-1010-1010-101010101010', 'c0101010-1010-1010-1010-101010101010')  -- Marchitez en Palma
ON CONFLICT DO NOTHING;

-- 8. Nutrir Usuarios (Originales y Nuevas Regiones)
INSERT INTO usuarios (id, nombre, apellido, email, cedula, rol, telefono, registro_ica, departamento, municipio, vereda, activo) VALUES
-- Originales
('e0011111-1111-1111-1111-111111111111', 'Luis Ernesto', 'Vargas', 'admin@fitogestion.co', '1098765430', 'admin', '3001234560', 'ICA-ADM-01', 'Santander', 'Bucaramanga', 'Central', true),
('e0022222-2222-2222-2222-222222222222', 'Roberto', 'Pérez', 'tecnico_santander@fitogestion.co', '1098765431', 'tecnico', '3001234561', 'ICA-TEC-SAN-01', 'Santander', 'Lebrija', 'La Renta', true),
('e0033333-3333-3333-3333-333333333333', 'Silvia', 'Gómez', 'tecnico_antioquia@fitogestion.co', '1098765432', 'tecnico', '3001234562', 'ICA-TEC-ANT-02', 'Antioquia', 'Medellín', 'Poblado', true),
('e0044444-4444-4444-4444-444444444444', 'Carlos', 'Martínez', 'tecnico_cundinamarca@fitogestion.co', '1098765433', 'tecnico', '3001234563', 'ICA-TEC-CUN-03', 'Cundinamarca', 'Fusagasugá', 'Chinauta', true),
('e0055555-5555-5555-5555-555555555555', 'Darwing', 'Jaimes', 'productor_santander@fitogestion.co', '1098765434', 'productor', '3001234564', null, 'Santander', 'Lebrija', 'La Esmeralda', true),
('e0066666-6666-6666-6666-666666666666', 'María Camila', 'Díaz', 'productor_antioquia@fitogestion.co', '1098765435', 'productor', '3001234565', null, 'Antioquia', 'Jericó', 'Quebradona', true),
-- Boyacá
('e0077777-7777-7777-7777-777777777777', 'Andrés', 'Castro', 'tecnico_boyaca@fitogestion.co', '1098765436', 'tecnico', '3111234560', 'ICA-TEC-BOY-07', 'Boyacá', 'Tunja', 'Maldonado', true),
('e0088888-8888-8888-8888-888888888888', 'Yuliana', 'Rojas', 'productor_boyaca@fitogestion.co', '1098765437', 'productor', '3211234560', null, 'Boyacá', 'Villa de Leyva', 'Sopotó', true),
-- Huila
('e0099999-9999-9999-9999-999999999999', 'Clara Inés', 'Medina', 'tecnico_huila@fitogestion.co', '1098765438', 'tecnico', '3121234560', 'ICA-TEC-HUI-08', 'Huila', 'Neiva', 'Las Mercedes', true),
('e0101010-1010-1010-1010-101010101010', 'Manuel', 'Cuellar', 'productor_huila@fitogestion.co', '1098765439', 'productor', '3221234560', null, 'Huila', 'Pitalito', 'Regueros', true),
-- Valle del Cauca
('e0202020-2020-2020-2020-202020202020', 'Diego', 'Rivera', 'tecnico_valle@fitogestion.co', '1098765440', 'tecnico', '3131234560', 'ICA-TEC-VAL-09', 'Valle del Cauca', 'Cali', 'La Morada', true),
('e0303030-3030-3030-3030-303030303030', 'Oscar', 'Giraldo', 'productor_valle@fitogestion.co', '1098765441', 'productor', '3231234560', null, 'Valle del Cauca', 'Palmira', 'Rozo', true),
-- Nariño
('e0404040-4040-4040-4040-404040404040', 'Jairo', 'Ortega', 'tecnico_narino@fitogestion.co', '1098765442', 'tecnico', '3141234560', 'ICA-TEC-NAR-10', 'Nariño', 'Pasto', 'Anganoy', true),
('e0505050-5050-5050-5050-505050505050', 'Sonia', 'Burbano', 'productor_narino@fitogestion.co', '1098765443', 'productor', '3241234560', null, 'Nariño', 'Pasto', 'Catambuco', true),
-- Tolima
('e0606060-6060-6060-6060-606060606060', 'Patricia', 'Ortiz', 'tecnico_tolima@fitogestion.co', '1098765444', 'tecnico', '3151234560', 'ICA-TEC-TOL-11', 'Tolima', 'Ibagué', 'Chucuní', true),
('e0707070-7070-7070-7070-707070707070', 'Gabriel', 'Perdomo', 'productor_tolima@fitogestion.co', '1098765445', 'productor', '3251234560', null, 'Tolima', 'Espinal', 'La Caimanera', true)
ON CONFLICT (id) DO NOTHING;

-- 9. Nutrir Predios
INSERT INTO predios (id, nombre, productor_id, departamento, municipio, vereda, numero_registro_ica, latitud, longitud, area_total, activo) VALUES
-- Originales
('d0011111-1111-1111-1111-111111111111', 'Finca La Esmeralda', 'e0055555-5555-5555-5555-555555555555', 'Santander', 'Lebrija', 'La Esmeralda', 'REG-ICA-SAN-5544', 7.1118, -73.2201, 12.50, true),
('d0022222-2222-2222-2222-222222222222', 'Hacienda El Recreo', 'e0066666-6666-6666-6666-666666666666', 'Antioquia', 'Jericó', 'Quebradona', 'REG-ICA-ANT-9988', 5.7915, -75.7820, 24.80, true),
('d0033333-3333-3333-3333-333333333333', 'Finca El Recuerdo', 'e0055555-5555-5555-5555-555555555555', 'Santander', 'Lebrija', 'Cantabria', 'REG-ICA-SAN-7766', 7.1250, -73.2315, 8.20, true),
-- Nuevos
('d0044444-4444-4444-4444-444444444444', 'Finca El Rosal (Claveles)', 'e0088888-8888-8888-8888-888888888888', 'Boyacá', 'Villa de Leyva', 'Sopotó', 'REG-ICA-BOY-0044', 5.6373, -73.5249, 5.20, true),
('d0055555-5555-5555-5555-555555555555', 'Hacienda San Isidro (Café)', 'e0101010-1010-1010-1010-101010101010', 'Huila', 'Pitalito', 'Regueros', 'REG-ICA-HUI-0055', 1.8547, -76.0507, 18.50, true),
('d0066666-6666-6666-6666-666666666666', 'Predio Cañaveral', 'e0303030-3030-3030-3030-303030303030', 'Valle del Cauca', 'Palmira', 'Rozo', 'REG-ICA-VAL-0066', 3.5168, -76.3036, 50.00, true),
('d0077777-7777-7777-7777-777777777777', 'Finca Papal Nariño', 'e0505050-5050-5050-5050-505050505050', 'Nariño', 'Pasto', 'Catambuco', 'REG-ICA-NAR-0077', 1.1714, -77.2917, 8.40, true),
('d0088888-8888-8888-8888-888888888888', 'Finca El Maizal', 'e0707070-7070-7070-7070-707070707070', 'Tolima', 'Espinal', 'La Caimanera', 'REG-ICA-TOL-0088', 4.1492, -74.8812, 14.00, true)
ON CONFLICT (id) DO NOTHING;

-- 10. Nutrir Lotes
INSERT INTO lotes (id, predio_id, nombre, cultivo_id, area, num_plantas, estado) VALUES
-- Originales
('b0011111-1111-1111-1111-111111111111', 'd0011111-1111-1111-1111-111111111111', 'Lote Limón 01', 'c0011111-1111-1111-1111-111111111111', 4.50, 1200, 'Óptimo'),
('b0011111-2222-1111-1111-111111111111', 'd0011111-1111-1111-1111-111111111111', 'Lote Naranja Valencia', 'c0011111-1111-1111-1111-111111111111', 3.00, 800, 'Alerta'),
('b0022222-1111-2222-2222-222222222222', 'd0022222-2222-2222-2222-222222222222', 'Lote Aguacate Hass 01', 'c0022222-2222-2222-2222-222222222222', 15.00, 3200, 'Óptimo'),
('b0033333-1111-3333-3333-333333333333', 'd0033333-3333-3333-3333-333333333333', 'Lote Café Castillo', 'c0033333-3333-3333-3333-333333333333', 6.00, 5000, 'Óptimo'),
-- Nuevos
('b0044444-4444-4444-4444-444444444444', 'd0044444-4444-4444-4444-444444444444', 'Invernadero Clavel 01', 'c0099999-9999-9999-9999-999999999999', 1.50, 5000, 'Óptimo'),
('b0055555-5555-5555-5555-555555555555', 'd0055555-5555-5555-5555-555555555555', 'Lote Café Bourbon 02', 'c0033333-3333-3333-3333-333333333333', 10.00, 15000, 'Óptimo'),
('b0066666-6666-6666-6666-666666666666', 'd0066666-6666-6666-6666-666666666666', 'Lote Caña Suerte 12', 'c0088888-8888-8888-8888-888888888888', 25.00, 30000, 'Óptimo'),
('b0077777-7777-7777-7777-777777777777', 'd0077777-7777-7777-7777-777777777777', 'Lote Papa Suprema 01', 'c0066666-6666-6666-6666-666666666666', 4.00, 8000, 'Óptimo'),
('b0088888-8888-8888-8888-888888888888', 'd0088888-8888-8888-8888-888888888888', 'Lote Maíz Híbrido 03', 'c0077777-7777-7777-7777-777777777777', 6.00, 12000, 'Óptimo')
ON CONFLICT (id) DO NOTHING;

-- 11. Nutrir Inspecciones Completadas
INSERT INTO inspecciones (id, tecnico_id, predio_id, lote_id, fecha_inspeccion, tipo_inspeccion, estado, observaciones, resultado_general, fecha_cierre) VALUES
-- Originales
('a0011111-1111-1111-1111-111111111111', 'e0022222-2222-2222-2222-222222222222', 'd0011111-1111-1111-1111-111111111111', 'b0011111-1111-1111-1111-111111111111', '2026-05-10', 'rutinaria', 'completada', 'Se observan plantas en buen estado general. Muestreos en hoja negativos para plagas de control oficial.', 'sin_novedad', '2026-05-10'),
('a0022222-2222-2222-2222-222222222222', 'e0033333-3333-3333-3333-333333333333', 'd0022222-2222-2222-2222-222222222222', 'b0022222-1111-2222-2222-222222222222', '2026-05-15', 'seguimiento', 'completada', 'Focos aislados de Phytophthora detectados en raíces. Se prescribe drenaje y fungicida localizado.', 'con_hallazgos', '2026-05-15'),
-- Nuevos
('a0044444-4444-4444-4444-444444444444', 'e0077777-7777-7777-7777-777777777777', 'd0044444-4444-4444-4444-444444444444', 'b0044444-4444-4444-4444-444444444444', '2026-05-20', 'rutinaria', 'completada', 'Inspección realizada en invernadero. Presencia de nudos y agallas radiculares causadas por nematodos. Se recomienda aplicación biológica de hongos nematófagos y rotación de suelos.', 'con_hallazgos', '2026-05-20'),
('a0055555-5555-5555-5555-555555555555', 'e0099999-9999-9999-9999-999999999999', 'd0055555-5555-5555-5555-555555555555', 'b0055555-5555-5555-5555-555555555555', '2026-05-22', 'seguimiento', 'completada', 'Revisión fitosanitaria del cultivo de café Bourbon. Focos de roya controlados en hojas basales. Excelente estado fisiológico general del lote.', 'sin_novedad', '2026-05-22'),
('a0066666-6666-6666-6666-666666666666', 'e0202020-2020-2020-2020-202020202020', 'd0066666-6666-6666-6666-666666666666', 'b0066666-6666-6666-6666-666666666666', '2026-05-24', 'emergencia', 'completada', 'Inspección de emergencia por sintomatología de carbón de la caña. Se detectaron 2 látigos del carbón activos en el centro del lote. Se ordenó la erradicación inmediata de los tallos afectados e incineración in situ.', 'critico', '2026-05-24'),
('a0077777-7777-7777-7777-777777777777', 'e0404040-4040-4040-4040-404040404040', 'd0077777-7777-7777-7777-777777777777', 'b0077777-7777-7777-7777-777777777777', '2026-05-25', 'rutinaria', 'completada', 'Se observan focos de Gota en tercio medio de las plantas tras lluvias prolongadas. Se recomienda iniciar aplicaciones preventivas con fungicidas registrados.', 'con_hallazgos', '2026-05-25')
ON CONFLICT (id) DO NOTHING;

-- 12. Nutrir Inspecciones Pendientes
INSERT INTO inspecciones (id, tecnico_id, predio_id, lote_id, fecha_inspeccion, tipo_inspeccion, estado, observaciones, resultado_general, fecha_cierre) VALUES
-- Originales
('a0033333-3333-3333-3333-333333333333', 'e0022222-2222-2222-2222-222222222222', 'd0011111-1111-1111-1111-111111111111', 'b0011111-2222-1111-1111-111111111111', '2026-05-20', 'emergencia', 'pendiente', 'Reporte de posible presencia de psílido Diaphorina citri en hojas terminales. Pendiente visita de campo.', null, null),
-- Nuevos
('a0088888-8888-8888-8888-888888888888', 'e0606060-6060-6060-6060-606060606060', 'd0088888-8888-8888-8888-888888888888', 'b0088888-8888-8888-8888-888888888888', '2026-05-29', 'rutinaria', 'pendiente', 'Solicitud rutinaria del productor para descartar presencia de cogollero en plántulas recién emergidas.', null, null)
ON CONFLICT (id) DO NOTHING;

-- 13. Nutrir Sub-Inspecciones
INSERT INTO sub_inspecciones (id, inspeccion_id, codigo_punto, ubicacion_referencia, observaciones, estado, plantas_evaluadas) VALUES
-- Originales
('90011111-1111-1111-1111-111111111111', 'a0011111-1111-1111-1111-111111111111', 'PUNTO-01', 'Coordenadas norte del lote 1', 'Muestreo de 5 árboles. Sin novedades.', 'completado', 5),
('90022222-2222-2222-2222-222222222222', 'a0022222-2222-2222-2222-222222222222', 'PUNTO-HASS-01', 'Cerca al canal de drenaje', 'Presencia de síntomas de marchitez en hojas.', 'completado', 5),
-- Nuevos
('90044444-4444-4444-4444-444444444444', 'a0044444-4444-4444-4444-444444444444', 'PT-CLAV-01', 'Extremo occidental del invernadero 1', 'Muestreo foliar y de raíz en 5 plantas.', 'completado', 5),
('90055555-5555-5555-5555-555555555555', 'a0055555-5555-5555-5555-555555555555', 'PT-CAFE-02', 'Cerca al lindero con río', 'Hojas con leves manchas amarillas.', 'completado', 5),
('90066666-6666-6666-6666-666666666666', 'a0066666-6666-6666-6666-666666666666', 'PT-CANA-03', 'Sector de encharcamiento central', 'Tallos jóvenes deformados con filamento negro.', 'completado', 5),
('90077777-7777-7777-7777-777777777777', 'a0077777-7777-7777-7777-777777777777', 'PT-PAPA-04', 'Loma alta del predio', 'Necrosis foliar y manchas necróticas.', 'completado', 5)
ON CONFLICT (id) DO NOTHING;

-- 14. Nutrir Registro de Plantas (Hallazgos y sanas para calcular incidencia)
INSERT INTO registro_plantas (id, sub_inspeccion_id, numero_planta, plaga_id, sintoma, severidad, incidencia, estado_planta, observaciones) VALUES
-- Originales
('80011111-1111-1111-1111-111111111111', '90011111-1111-1111-1111-111111111111', 1, null, 'Ninguno', null, 0.00, 'sana', 'Árbol sano y vigoroso.'),
('80011111-2222-1111-1111-111111111111', '90011111-1111-1111-1111-111111111111', 2, null, 'Ninguno', null, 0.00, 'sana', 'Árbol sano y vigoroso.'),
('80022222-1111-2222-2222-222222222222', '90022222-2222-2222-2222-222222222222', 1, 'f0022222-2222-2222-2222-222222222222', 'Marchitez radicular y clorosis', 'moderado', 20.00, 'enferma', 'Clorosis generalizada por encharcamiento en raíces.'),
('80022222-2222-2222-2222-222222222222', '90022222-2222-2222-2222-222222222222', 2, 'f0022222-2222-2222-2222-222222222222', 'Necrosis foliar y marchitez severa', 'severo', 40.00, 'enferma', 'Afectación severa de hongos fitopatógenos en cuello del tallo.'),
-- Clavel (Nematodos en 2 de 5 plantas)
('80044444-4444-4444-4444-444444444441', '90044444-4444-4444-4444-444444444444', 1, 'f0099999-9999-9999-9999-999999999999', 'Agallas pronunciadas en raíces y enanismo', 'moderado', 20.00, 'enferma', 'Debilitamiento general.'),
('80044444-4444-4444-4444-444444444442', '90044444-4444-4444-4444-444444444444', 2, 'f0099999-9999-9999-9999-999999999999', 'Clorosis severa y raíces deformadas', 'severo', 40.00, 'enferma', 'Pérdida de masa foliar.'),
('80044444-4444-4444-4444-444444444443', '90044444-4444-4444-4444-444444444444', 3, null, 'Ninguno', null, 0.00, 'sana', 'Planta vigorosa.'),
('80044444-4444-4444-4444-444444444444', '90044444-4444-4444-4444-444444444444', 4, null, 'Ninguno', null, 0.00, 'sana', 'Sin síntomas.'),
('80044444-4444-4444-4444-444444444445', '90044444-4444-4444-4444-444444444444', 5, null, 'Ninguno', null, 0.00, 'sana', 'Sin síntomas.'),

-- Café (Sanitariamente bien, sin plagas de control)
('80055555-5555-5555-5555-555555555551', '90055555-5555-5555-5555-555555555555', 1, null, 'Ninguno', null, 0.00, 'sana', 'Sana.'),
('80055555-5555-5555-5555-555555555552', '90055555-5555-5555-5555-555555555555', 2, null, 'Ninguno', null, 0.00, 'sana', 'Sana.'),
('80055555-5555-5555-5555-555555555553', '90055555-5555-5555-5555-555555555555', 3, null, 'Ninguno', null, 0.00, 'sana', 'Sana.'),
('80055555-5555-5555-5555-555555555554', '90055555-5555-5555-5555-555555555555', 4, null, 'Ninguno', null, 0.00, 'sana', 'Sana.'),
('80055555-5555-5555-5555-555555555555', '90055555-5555-5555-5555-555555555555', 5, null, 'Ninguno', null, 0.00, 'sana', 'Sana.'),

-- Caña (Carbón en 3 de 5 plantas — Crítico)
('80066666-6666-6666-6666-666666666661', '90066666-6666-6666-6666-666666666666', 1, 'f0088888-8888-8888-8888-888888888888', 'Látigo negro carbonoso en cogollo', 'severo', 60.00, 'enferma', 'Tallos atrofiados.'),
('80066666-6666-6666-6666-666666666662', '90066666-6666-6666-6666-666666666666', 2, 'f0088888-8888-8888-8888-888888888888', 'Látigo negro en desarrollo basal', 'moderado', 40.00, 'enferma', 'Clorosis general.'),
('80066666-6666-6666-6666-666666666663', '90066666-6666-6666-6666-666666666666', 3, 'f0088888-8888-8888-8888-888888888888', 'Estructura carbonosa y secado de tallo', 'severo', 80.00, 'enferma', 'Estructura destruida.'),
('80066666-6666-6666-6666-666666666664', '90066666-6666-6666-6666-666666666666', 4, null, 'Ninguno', null, 0.00, 'sana', 'Sana.'),
('80066666-6666-6666-6666-666666666665', '90066666-6666-6666-6666-666666666666', 5, null, 'Ninguno', null, 0.00, 'sana', 'Sana.'),

-- Papa (Gota en 1 de 5 plantas)
('80077777-7777-7777-7777-777777777771', '90077777-7777-7777-7777-777777777777', 1, 'f0066666-6666-6666-6666-666666666666', 'Manchas necróticas con vello blanco', 'moderado', 20.00, 'enferma', 'Hojas marchitas.'),
('80077777-7777-7777-7777-777777777772', '90077777-7777-7777-7777-777777777777', 2, null, 'Ninguno', null, 0.00, 'sana', 'Sana.'),
('80077777-7777-7777-7777-777777777773', '90077777-7777-7777-7777-777777777777', 3, null, 'Ninguno', null, 0.00, 'sana', 'Sana.'),
('80077777-7777-7777-7777-777777777774', '90077777-7777-7777-7777-777777777777', 4, null, 'Ninguno', null, 0.00, 'sana', 'Sin síntomas.'),
('80077777-7777-7777-7777-777777777775', '90077777-7777-7777-7777-777777777777', 5, null, 'Ninguno', null, 0.00, 'sana', 'Sin síntomas.')
ON CONFLICT (id) DO NOTHING;

-- ✅ Migración y nutrición completada con éxito
SELECT 'Datos sembrados y nutridos exitosamente para Colombia' AS resultado;
