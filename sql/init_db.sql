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
