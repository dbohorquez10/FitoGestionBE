-- ============================================================================
-- FitoGestión — Script de MIGRACIÓN (ejecutar en Supabase SQL Editor)
-- Agrega: tabla plaga_cultivo + columna numero_registro_ica en predios
-- ============================================================================

-- 1. Tabla intermedia plaga_cultivo (many-to-many)
CREATE TABLE IF NOT EXISTS plaga_cultivo (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plaga_id    UUID NOT NULL REFERENCES plagas(id) ON DELETE CASCADE,
    cultivo_id  UUID NOT NULL REFERENCES cultivos(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(plaga_id, cultivo_id)
);

COMMENT ON TABLE plaga_cultivo IS 'Relación muchos-a-muchos entre plagas y los cultivos que afectan.';
CREATE INDEX IF NOT EXISTS idx_plaga_cultivo_plaga ON plaga_cultivo(plaga_id);
CREATE INDEX IF NOT EXISTS idx_plaga_cultivo_cultivo ON plaga_cultivo(cultivo_id);

-- 2. Columna numero_registro_ica en predios (si no existe)
ALTER TABLE predios ADD COLUMN IF NOT EXISTS numero_registro_ica VARCHAR(50);

-- 3. RLS + política para plaga_cultivo
ALTER TABLE plaga_cultivo ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON plaga_cultivo FOR ALL USING (true) WITH CHECK (true);

-- ✅ Migración completada
SELECT 'Migración exitosa: plaga_cultivo + numero_registro_ica' AS resultado;
