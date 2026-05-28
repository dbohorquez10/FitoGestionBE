-- ============================================================================
-- FitoGestión — Script DDL de inicialización
-- Base de datos: Supabase (PostgreSQL)
-- Ejecutar en el SQL Editor de Supabase
-- ============================================================================

-- Habilitar extensión UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ TABLA: USUARIOS                                                          ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
CREATE TABLE IF NOT EXISTS usuarios (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre        VARCHAR(100)  NOT NULL,
    apellido      VARCHAR(100)  NOT NULL,
    email         VARCHAR(255)  NOT NULL UNIQUE,
    cedula        VARCHAR(20)   NOT NULL UNIQUE,
    rol           VARCHAR(20)   NOT NULL CHECK (rol IN ('admin', 'tecnico', 'productor')),
    telefono      VARCHAR(20),
    registro_ica  VARCHAR(50),  -- Solo para técnicos
    departamento  VARCHAR(100),
    municipio     VARCHAR(100),
    vereda        VARCHAR(150),
    activo        BOOLEAN       DEFAULT TRUE,
    created_at    TIMESTAMPTZ   DEFAULT NOW(),
    updated_at    TIMESTAMPTZ   DEFAULT NOW()
);

COMMENT ON TABLE usuarios IS 'Usuarios del sistema: administradores, técnicos ICA y productores.';

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ TABLA: CULTIVOS (Catálogo)                                               ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
CREATE TABLE IF NOT EXISTS cultivos (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre              VARCHAR(100)  NOT NULL,
    nombre_cientifico   VARCHAR(200),
    variedad            VARCHAR(100),
    descripcion         TEXT,
    activo              BOOLEAN       DEFAULT TRUE,
    created_at          TIMESTAMPTZ   DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   DEFAULT NOW()
);

COMMENT ON TABLE cultivos IS 'Catálogo de cultivos agrícolas registrados.';

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ TABLA: PLAGAS (Catálogo)                                                 ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
CREATE TABLE IF NOT EXISTS plagas (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre_comun        VARCHAR(150)  NOT NULL,
    nombre_cientifico   VARCHAR(200),
    tipo                VARCHAR(50)   NOT NULL CHECK (tipo IN ('insecto', 'hongo', 'bacteria', 'virus', 'nematodo', 'maleza')),
    descripcion         TEXT,
    activo              BOOLEAN       DEFAULT TRUE,
    created_at          TIMESTAMPTZ   DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   DEFAULT NOW()
);

COMMENT ON TABLE plagas IS 'Catálogo de plagas y enfermedades fitosanitarias.';

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ TABLA: PLAGA_CULTIVO (Relación Many-to-Many)                            ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
CREATE TABLE IF NOT EXISTS plaga_cultivo (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plaga_id    UUID NOT NULL REFERENCES plagas(id) ON DELETE CASCADE,
    cultivo_id  UUID NOT NULL REFERENCES cultivos(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(plaga_id, cultivo_id)
);

COMMENT ON TABLE plaga_cultivo IS 'Relación muchos-a-muchos entre plagas y los cultivos que afectan.';
CREATE INDEX idx_plaga_cultivo_plaga ON plaga_cultivo(plaga_id);
CREATE INDEX idx_plaga_cultivo_cultivo ON plaga_cultivo(cultivo_id);

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ TABLA: PREDIOS                                                           ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
CREATE TABLE IF NOT EXISTS predios (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre              VARCHAR(150)  NOT NULL,
    productor_id        UUID          NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    departamento        VARCHAR(100)  NOT NULL,
    municipio           VARCHAR(100)  NOT NULL,
    vereda              VARCHAR(150),
    numero_registro_ica VARCHAR(50),  -- Código de registro ante el ICA
    latitud             DECIMAL(10, 7),
    longitud            DECIMAL(10, 7),
    area_total          DECIMAL(10, 2),  -- Hectáreas
    activo              BOOLEAN       DEFAULT TRUE,
    created_at          TIMESTAMPTZ   DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   DEFAULT NOW()
);

COMMENT ON TABLE predios IS 'Predios agrícolas vinculados a un productor.';
CREATE INDEX idx_predios_productor ON predios(productor_id);
CREATE INDEX idx_predios_region ON predios(departamento, municipio);
CREATE INDEX idx_usuarios_region ON usuarios(departamento, municipio);

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ TABLA: LOTES                                                             ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
CREATE TABLE IF NOT EXISTS lotes (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    predio_id     UUID          NOT NULL REFERENCES predios(id) ON DELETE CASCADE,
    nombre        VARCHAR(100)  NOT NULL,
    cultivo_id    UUID          REFERENCES cultivos(id) ON DELETE SET NULL,
    area          DECIMAL(10, 2),  -- Hectáreas
    num_plantas   INTEGER,
    estado        VARCHAR(30)   DEFAULT 'Óptimo' CHECK (estado IN ('Óptimo', 'Alerta', 'Crítico', 'En Cuarentena')),
    created_at    TIMESTAMPTZ   DEFAULT NOW(),
    updated_at    TIMESTAMPTZ   DEFAULT NOW()
);

COMMENT ON TABLE lotes IS 'Lotes de cultivo dentro de un predio agrícola.';
CREATE INDEX idx_lotes_predio ON lotes(predio_id);
CREATE INDEX idx_lotes_cultivo ON lotes(cultivo_id);

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ TABLA: INSPECCIONES                                                      ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
CREATE TABLE IF NOT EXISTS inspecciones (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tecnico_id          UUID          NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    predio_id           UUID          NOT NULL REFERENCES predios(id) ON DELETE CASCADE,
    lote_id             UUID          NOT NULL REFERENCES lotes(id) ON DELETE CASCADE,
    fecha_inspeccion    DATE          NOT NULL,
    tipo_inspeccion     VARCHAR(30)   NOT NULL CHECK (tipo_inspeccion IN ('rutinaria', 'seguimiento', 'emergencia')),
    estado              VARCHAR(30)   DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'en_progreso', 'completada', 'cancelada')),
    observaciones       TEXT,
    resultado_general   VARCHAR(30)   CHECK (resultado_general IN ('sin_novedad', 'con_hallazgos', 'critico')),
    fecha_cierre        DATE,
    created_at          TIMESTAMPTZ   DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   DEFAULT NOW()
);

COMMENT ON TABLE inspecciones IS 'Inspecciones fitosanitarias realizadas por técnicos ICA.';
CREATE INDEX idx_inspecciones_tecnico ON inspecciones(tecnico_id);
CREATE INDEX idx_inspecciones_predio ON inspecciones(predio_id);
CREATE INDEX idx_inspecciones_lote ON inspecciones(lote_id);
CREATE INDEX idx_inspecciones_fecha ON inspecciones(fecha_inspeccion);

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ TABLA: SUB-INSPECCIONES                                                  ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
CREATE TABLE IF NOT EXISTS sub_inspecciones (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    inspeccion_id           UUID          NOT NULL REFERENCES inspecciones(id) ON DELETE CASCADE,
    codigo_punto            VARCHAR(50)   NOT NULL,
    ubicacion_referencia    VARCHAR(255),
    observaciones           TEXT,
    estado                  VARCHAR(30)   DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'completado')),
    plantas_evaluadas       INTEGER       DEFAULT 0,
    created_at              TIMESTAMPTZ   DEFAULT NOW(),
    updated_at              TIMESTAMPTZ   DEFAULT NOW()
);

COMMENT ON TABLE sub_inspecciones IS 'Puntos de muestreo dentro de una inspección principal.';
CREATE INDEX idx_sub_inspecciones_inspeccion ON sub_inspecciones(inspeccion_id);

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ TABLA: REGISTRO DE PLANTAS                                               ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
CREATE TABLE IF NOT EXISTS registro_plantas (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sub_inspeccion_id   UUID          NOT NULL REFERENCES sub_inspecciones(id) ON DELETE CASCADE,
    numero_planta       INTEGER       NOT NULL,
    plaga_id            UUID          REFERENCES plagas(id) ON DELETE SET NULL,
    sintoma             VARCHAR(255),
    severidad           VARCHAR(20)   CHECK (severidad IN ('leve', 'moderado', 'severo')),
    incidencia          DECIMAL(5, 2) CHECK (incidencia >= 0 AND incidencia <= 100),
    estado_planta       VARCHAR(20)   DEFAULT 'sana' CHECK (estado_planta IN ('sana', 'enferma', 'muerta')),
    observaciones       TEXT,
    created_at          TIMESTAMPTZ   DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   DEFAULT NOW()
);

COMMENT ON TABLE registro_plantas IS 'Registro individual de plantas inspeccionadas con hallazgos fitosanitarios.';
CREATE INDEX idx_registro_plantas_sub ON registro_plantas(sub_inspeccion_id);
CREATE INDEX idx_registro_plantas_plaga ON registro_plantas(plaga_id);

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ FUNCIÓN: Trigger para actualizar updated_at automáticamente              ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger a todas las tablas
CREATE TRIGGER trg_usuarios_updated_at       BEFORE UPDATE ON usuarios         FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_cultivos_updated_at       BEFORE UPDATE ON cultivos         FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_plagas_updated_at         BEFORE UPDATE ON plagas           FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_predios_updated_at        BEFORE UPDATE ON predios          FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_lotes_updated_at          BEFORE UPDATE ON lotes            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_inspecciones_updated_at   BEFORE UPDATE ON inspecciones     FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_sub_inspecciones_updated_at BEFORE UPDATE ON sub_inspecciones FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_registro_plantas_updated_at BEFORE UPDATE ON registro_plantas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ FUNCIÓN Y TRIGGER: Calcular Incidencia Fitosanitaria                       ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
CREATE OR REPLACE FUNCTION fn_calcular_incidencia()
RETURNS TRIGGER AS $$
DECLARE
    v_sub_id UUID;
    v_inspeccion_id UUID;
    v_lote_id UUID;
    v_total INT;
    v_afectadas INT;
    v_incidencia DECIMAL;
BEGIN
    -- Identificar la sub_inspección afectada
    IF TG_OP = 'DELETE' THEN
        v_sub_id := OLD.sub_inspeccion_id;
    ELSE
        v_sub_id := NEW.sub_inspeccion_id;
    END IF;

    -- Calcular métricas para esta sub_inspección
    SELECT COUNT(*), COUNT(*) FILTER (WHERE estado_planta IN ('enferma', 'muerta'))
    INTO v_total, v_afectadas
    FROM registro_plantas
    WHERE sub_inspeccion_id = v_sub_id;

    -- Actualizar el contador de plantas_evaluadas en la sub_inspección
    UPDATE sub_inspecciones
    SET plantas_evaluadas = v_total
    WHERE id = v_sub_id;

    -- Si hay plantas evaluadas, calcular incidencia y verificar estado del lote
    IF v_total > 0 THEN
        v_incidencia := (v_afectadas::DECIMAL / v_total) * 100;
        
        IF v_incidencia > 10.0 THEN
            -- Obtener IDs relacionados
            SELECT inspeccion_id INTO v_inspeccion_id FROM sub_inspecciones WHERE id = v_sub_id;
            SELECT lote_id INTO v_lote_id FROM inspecciones WHERE id = v_inspeccion_id;
            
            -- Actualizar estado del lote a Crítico
            UPDATE lotes
            SET estado = 'Crítico'
            WHERE id = v_lote_id AND estado != 'Crítico';
        END IF;
    END IF;

    RETURN NULL; -- AFTER trigger
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_calcular_incidencia_lote
AFTER INSERT OR UPDATE OR DELETE ON registro_plantas
FOR EACH ROW EXECUTE FUNCTION fn_calcular_incidencia();

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ ROW LEVEL SECURITY (RLS) — Habilitar para uso con Supabase               ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
ALTER TABLE usuarios          ENABLE ROW LEVEL SECURITY;
ALTER TABLE cultivos          ENABLE ROW LEVEL SECURITY;
ALTER TABLE plagas            ENABLE ROW LEVEL SECURITY;
ALTER TABLE predios           ENABLE ROW LEVEL SECURITY;
ALTER TABLE lotes             ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspecciones      ENABLE ROW LEVEL SECURITY;
ALTER TABLE sub_inspecciones  ENABLE ROW LEVEL SECURITY;
ALTER TABLE registro_plantas  ENABLE ROW LEVEL SECURITY;
ALTER TABLE plaga_cultivo     ENABLE ROW LEVEL SECURITY;

-- Política permisiva para service_role (el backend usa la service key)
CREATE POLICY "Service role full access" ON usuarios          FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON cultivos          FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON plagas            FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON plaga_cultivo     FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON predios           FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON lotes             FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON inspecciones      FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON sub_inspecciones  FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON registro_plantas  FOR ALL USING (true) WITH CHECK (true);

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ FUNCIÓN: Generar Informe Fitosanitario                                     ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
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


-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║ DATOS SEMILLA (SEED DATA)                                                ║
-- ╚════════════════════════════════════════════════════════════════════════════╝

-- 1. Insertar Cultivos
INSERT INTO cultivos (id, nombre, nombre_cientifico, variedad, descripcion, activo) VALUES
('c0011111-1111-1111-1111-111111111111', 'Cítricos', 'Citrus spp.', 'Limón Tahití', 'Cultivo de cítricos para exportación de limón y naranja dulce.', true),
('c0022222-2222-2222-2222-222222222222', 'Aguacate', 'Persea americana', 'Hass', 'Aguacate tipo Hass cultivado para mercados nacionales e internacionales.', true),
('c0033333-3333-3333-3333-333333333333', 'Café', 'Coffea arabica', 'Castillo', 'Café especial Castillo de alta resistencia a la roya.', true),
('c0044444-4444-4444-4444-444444444444', 'Cacao', 'Theobroma cacao', 'CCN51', 'Cacao de alta productividad y fermentación controlada.', true),
('c0055555-5555-5555-5555-555555555555', 'Plátano', 'Musa paradisiaca', 'Hartón', 'Plátano clon Hartón utilizado como sombrío temporal y producción.', true)
ON CONFLICT (id) DO NOTHING;

-- 2. Insertar Plagas
INSERT INTO plagas (id, nombre_comun, nombre_cientifico, tipo, descripcion, activo) VALUES
('f0011111-1111-1111-1111-111111111111', 'Diaphorina citri (Psílido asiático)', 'Diaphorina citri', 'insecto', 'Vector de la bacteria Candidatus Liberibacter que causa el HLB de los cítricos.', true),
('f0022222-2222-2222-2222-222222222222', 'Pudrición del cogollo / Raíz', 'Phytophthora cinnamomi', 'hongo', 'Hongo patógeno que causa pudrición radicular en aguacate y cítricos.', true),
('f0033333-3333-3333-3333-333333333333', 'Broca del Café', 'Hypothenemus hampei', 'insecto', 'Plaga principal que perfora el grano de café afectando calidad y rendimiento.', true),
('f0044444-4444-4444-4444-444444444444', 'Moniliasis del Cacao', 'Moniliophthora roreri', 'hongo', 'Enfermedad limitante que pudre la mazorca de cacao internamente.', true),
('f0055555-5555-5555-5555-555555555555', 'Moko del Plátano', 'Ralstonia solanacearum', 'bacteria', 'Marchitez bacteriana sistémica que destruye plantas de musáceas.', true)
ON CONFLICT (id) DO NOTHING;

-- 3. Insertar Relaciones Plaga-Cultivo
INSERT INTO plaga_cultivo (plaga_id, cultivo_id) VALUES
('f0011111-1111-1111-1111-111111111111', 'c0011111-1111-1111-1111-111111111111'), -- Diaphorina en Cítricos
('f0022222-2222-2222-2222-222222222222', 'c0022222-2222-2222-2222-222222222222'), -- Phytophthora en Aguacate
('f0022222-2222-2222-2222-222222222222', 'c0011111-1111-1111-1111-111111111111'), -- Phytophthora en Cítricos
('f0033333-3333-3333-3333-333333333333', 'c0033333-3333-3333-3333-333333333333'), -- Broca en Café
('f0044444-4444-4444-4444-444444444444', 'c0044444-4444-4444-4444-444444444444'), -- Monilia en Cacao
('f0055555-5555-5555-5555-555555555555', 'c0055555-5555-5555-5555-555555555555')  -- Moko en Plátano
ON CONFLICT DO NOTHING;

-- 4. Insertar Usuarios
INSERT INTO usuarios (id, nombre, apellido, email, cedula, rol, telefono, registro_ica, departamento, municipio, vereda, activo) VALUES
('e0011111-1111-1111-1111-111111111111', 'Luis Ernesto', 'Vargas', 'admin@fitogestion.co', '1098765430', 'admin', '3001234560', 'ICA-ADM-01', 'Santander', 'Bucaramanga', 'Central', true),
('e0022222-2222-2222-2222-222222222222', 'Roberto', 'Pérez', 'tecnico_santander@fitogestion.co', '1098765431', 'tecnico', '3001234561', 'ICA-TEC-SAN-01', 'Santander', 'Lebrija', 'La Renta', true),
('e0033333-3333-3333-3333-333333333333', 'Silvia', 'Gómez', 'tecnico_antioquia@fitogestion.co', '1098765432', 'tecnico', '3001234562', 'ICA-TEC-ANT-02', 'Antioquia', 'Medellín', 'Poblado', true),
('e0044444-4444-4444-4444-444444444444', 'Carlos', 'Martínez', 'tecnico_cundinamarca@fitogestion.co', '1098765433', 'tecnico', '3001234563', 'ICA-TEC-CUN-03', 'Cundinamarca', 'Fusagasugá', 'Chinauta', true),
('e0055555-5555-5555-5555-555555555555', 'Darwing', 'Jaimes', 'productor_santander@fitogestion.co', '1098765434', 'productor', '3001234564', null, 'Santander', 'Lebrija', 'La Esmeralda', true),
('e0066666-6666-6666-6666-666666666666', 'María Camila', 'Díaz', 'productor_antioquia@fitogestion.co', '1098765435', 'productor', '3001234565', null, 'Antioquia', 'Jericó', 'Quebradona', true)
ON CONFLICT (id) DO NOTHING;

-- 5. Insertar Predios
INSERT INTO predios (id, nombre, productor_id, departamento, municipio, vereda, numero_registro_ica, latitud, longitud, area_total, activo) VALUES
('d0011111-1111-1111-1111-111111111111', 'Finca La Esmeralda', 'e0055555-5555-5555-5555-555555555555', 'Santander', 'Lebrija', 'La Esmeralda', 'REG-ICA-SAN-5544', 7.1118, -73.2201, 12.50, true),
('d0022222-2222-2222-2222-222222222222', 'Hacienda El Recreo', 'e0066666-6666-6666-6666-666666666666', 'Antioquia', 'Jericó', 'Quebradona', 'REG-ICA-ANT-9988', 5.7915, -75.7820, 24.80, true),
('d0033333-3333-3333-3333-333333333333', 'Finca El Recuerdo', 'e0055555-5555-5555-5555-555555555555', 'Santander', 'Lebrija', 'Cantabria', 'REG-ICA-SAN-7766', 7.1250, -73.2315, 8.20, true)
ON CONFLICT (id) DO NOTHING;

-- 6. Insertar Lotes
INSERT INTO lotes (id, predio_id, nombre, cultivo_id, area, num_plantas, estado) VALUES
('b0011111-1111-1111-1111-111111111111', 'd0011111-1111-1111-1111-111111111111', 'Lote Limón 01', 'c0011111-1111-1111-1111-111111111111', 4.50, 1200, 'Óptimo'),
('b0011111-2222-1111-1111-111111111111', 'd0011111-1111-1111-1111-111111111111', 'Lote Naranja Valencia', 'c0011111-1111-1111-1111-111111111111', 3.00, 800, 'Alerta'),
('b0022222-1111-2222-2222-222222222222', 'd0022222-2222-2222-2222-222222222222', 'Lote Aguacate Hass 01', 'c0022222-2222-2222-2222-222222222222', 15.00, 3200, 'Óptimo'),
('b0033333-1111-3333-3333-333333333333', 'd0033333-3333-3333-3333-333333333333', 'Lote Café Castillo', 'c0033333-3333-3333-3333-333333333333', 6.00, 5000, 'Óptimo')
ON CONFLICT (id) DO NOTHING;

-- 7. Insertar Inspecciones
INSERT INTO inspecciones (id, tecnico_id, predio_id, lote_id, fecha_inspeccion, tipo_inspeccion, estado, observaciones, resultado_general, fecha_cierre) VALUES
('a0011111-1111-1111-1111-111111111111', 'e0022222-2222-2222-2222-222222222222', 'd0011111-1111-1111-1111-111111111111', 'b0011111-1111-1111-1111-111111111111', '2026-05-10', 'rutinaria', 'completada', 'Se observan plantas en buen estado general. Muestreos en hoja negativos para plagas de control oficial.', 'sin_novedad', '2026-05-10'),
('a0022222-2222-2222-2222-222222222222', 'e0033333-3333-3333-3333-333333333333', 'd0022222-2222-2222-2222-222222222222', 'b0022222-1111-2222-2222-222222222222', '2026-05-15', 'seguimiento', 'completada', 'Focos aislados de Phytophthora detectados en raíces. Se prescribe drenaje y fungicida localizado.', 'con_hallazgos', '2026-05-15'),
('a0033333-3333-3333-3333-333333333333', 'e0022222-2222-2222-2222-222222222222', 'd0011111-1111-1111-1111-111111111111', 'b0011111-2222-1111-1111-111111111111', '2026-05-20', 'emergencia', 'pendiente', 'Reporte de posible presencia de psílido Diaphorina citri en hojas terminales. Pendiente visita de campo.', null, null)
ON CONFLICT (id) DO NOTHING;

-- 8. Insertar Sub-Inspecciones
INSERT INTO sub_inspecciones (id, inspeccion_id, codigo_punto, ubicacion_referencia, observaciones, estado, plantas_evaluadas) VALUES
('90011111-1111-1111-1111-111111111111', 'a0011111-1111-1111-1111-111111111111', 'PUNTO-01', 'Coordenadas norte del lote 1', 'Muestreo de 5 árboles. Sin novedades.', 'completado', 5),
('90022222-2222-2222-2222-222222222222', 'a0022222-2222-2222-2222-222222222222', 'PUNTO-HASS-01', 'Cerca al canal de drenaje', 'Presencia de síntomas de marchitez en hojas.', 'completado', 5)
ON CONFLICT (id) DO NOTHING;

-- 9. Insertar Registro de Plantas
INSERT INTO registro_plantas (id, sub_inspeccion_id, numero_planta, plaga_id, sintoma, severidad, incidencia, estado_planta, observaciones) VALUES
('80011111-1111-1111-1111-111111111111', '90011111-1111-1111-1111-111111111111', 1, null, 'Ninguno', null, 0.00, 'sana', 'Árbol sano y vigoroso.'),
('80011111-2222-1111-1111-111111111111', '90011111-1111-1111-1111-111111111111', 2, null, 'Ninguno', null, 0.00, 'sana', 'Árbol sano y vigoroso.'),
('80022222-1111-2222-2222-222222222222', '90022222-2222-2222-2222-222222222222', 1, 'f0022222-2222-2222-2222-222222222222', 'Marchitez radicular y clorosis', 'moderado', 20.00, 'enferma', 'Clorosis generalizada por encharcamiento en raíces.'),
('80022222-2222-2222-2222-222222222222', '90022222-2222-2222-2222-222222222222', 2, 'f0022222-2222-2222-2222-222222222222', 'Necrosis foliar y marchitez severa', 'severo', 40.00, 'enferma', 'Afectación severa de hongos fitopatógenos en cuello del tallo.')
ON CONFLICT (id) DO NOTHING;

