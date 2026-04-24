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
-- ║ TABLA: PREDIOS                                                           ║
-- ╚════════════════════════════════════════════════════════════════════════════╝
CREATE TABLE IF NOT EXISTS predios (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre          VARCHAR(150)  NOT NULL,
    productor_id    UUID          NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    departamento    VARCHAR(100)  NOT NULL,
    municipio       VARCHAR(100)  NOT NULL,
    vereda          VARCHAR(150),
    latitud         DECIMAL(10, 7),
    longitud        DECIMAL(10, 7),
    area_total      DECIMAL(10, 2),  -- Hectáreas
    activo          BOOLEAN       DEFAULT TRUE,
    created_at      TIMESTAMPTZ   DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   DEFAULT NOW()
);

COMMENT ON TABLE predios IS 'Predios agrícolas vinculados a un productor.';
CREATE INDEX idx_predios_productor ON predios(productor_id);

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
    estado        VARCHAR(30)   DEFAULT 'activo' CHECK (estado IN ('activo', 'inactivo', 'en_cuarentena')),
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

-- Política permisiva para service_role (el backend usa la service key)
CREATE POLICY "Service role full access" ON usuarios          FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON cultivos          FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON plagas            FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON predios           FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON lotes             FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON inspecciones      FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON sub_inspecciones  FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON registro_plantas  FOR ALL USING (true) WITH CHECK (true);
