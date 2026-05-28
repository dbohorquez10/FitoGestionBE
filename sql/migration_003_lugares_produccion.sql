-- ============================================================================
-- FitoGestión — Script de MIGRACIÓN 003
-- Crea la estructura de "Lugares de Producción" agrupando Predios
-- ============================================================================

-- 1. Crear tabla lugares_produccion
CREATE TABLE IF NOT EXISTS lugares_produccion (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    productor_id        UUID          NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    nombre              VARCHAR(150)  NOT NULL,
    numero_registro_ica VARCHAR(50)   UNIQUE,
    departamento        VARCHAR(100)  NOT NULL,
    municipio           VARCHAR(100)  NOT NULL,
    vereda              VARCHAR(150),
    latitud             DECIMAL(10, 7),
    longitud            DECIMAL(10, 7),
    activo              BOOLEAN       DEFAULT TRUE,
    created_at          TIMESTAMPTZ   DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   DEFAULT NOW()
);

COMMENT ON TABLE lugares_produccion IS 'Lugar de producción que agrupa predios y tiene registro ICA.';
CREATE INDEX IF NOT EXISTS idx_lugares_produccion_productor ON lugares_produccion(productor_id);
CREATE INDEX IF NOT EXISTS idx_lugares_produccion_region ON lugares_produccion(departamento, municipio);

-- 2. Añadir lugar_id a predios
ALTER TABLE predios ADD COLUMN IF NOT EXISTS lugar_id UUID REFERENCES lugares_produccion(id) ON DELETE CASCADE;

-- 3. Trigger para updated_at
DROP TRIGGER IF EXISTS trg_lugares_produccion_updated_at ON lugares_produccion;
CREATE TRIGGER trg_lugares_produccion_updated_at BEFORE UPDATE ON lugares_produccion FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 4. RLS
ALTER TABLE lugares_produccion ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access" ON lugares_produccion;
CREATE POLICY "Service role full access" ON lugares_produccion FOR ALL USING (true) WITH CHECK (true);

-- 5. Migrar datos existentes (crear un lugar por cada predio actual y asociarlos)
-- Lugar 1: La Esmeralda (e0055555, Santander, Lebrija)
INSERT INTO lugares_produccion (id, productor_id, nombre, numero_registro_ica, departamento, municipio, vereda, latitud, longitud)
VALUES ('f1011111-1111-1111-1111-111111111111', 'e0055555-5555-5555-5555-555555555555', 'Lugar La Esmeralda', 'REG-ICA-SAN-5544', 'Santander', 'Lebrija', 'La Esmeralda', 7.1118, -73.2201)
ON CONFLICT (id) DO NOTHING;

-- Lugar 2: El Recreo (e0066666, Antioquia, Jericó)
INSERT INTO lugares_produccion (id, productor_id, nombre, numero_registro_ica, departamento, municipio, vereda, latitud, longitud)
VALUES ('f1022222-2222-2222-2222-222222222222', 'e0066666-6666-6666-6666-666666666666', 'Lugar El Recreo', 'REG-ICA-ANT-9988', 'Antioquia', 'Jericó', 'Quebradona', 5.7915, -75.7820)
ON CONFLICT (id) DO NOTHING;

-- Asociar predios a los lugares (La Esmeralda y El Recuerdo van al Lugar 1, El Recreo al Lugar 2)
UPDATE predios SET lugar_id = 'f1011111-1111-1111-1111-111111111111' WHERE id IN ('d0011111-1111-1111-1111-111111111111', 'd0033333-3333-3333-3333-333333333333');
UPDATE predios SET lugar_id = 'f1022222-2222-2222-2222-222222222222' WHERE id = 'd0022222-2222-2222-2222-222222222222';
