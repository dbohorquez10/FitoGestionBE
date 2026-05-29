-- ============================================================================
-- FitoGestión — Script de MIGRACIÓN 010 (ejecutar en Supabase SQL Editor)
-- Objetivo: Evitar nombres duplicados de lotes en un mismo predio (case-insensitive)
-- ============================================================================

-- 1. Eliminar duplicados existentes (por seguridad, conservando el más antiguo)
DELETE FROM lotes a USING lotes b
WHERE a.id > b.id
  AND a.predio_id = b.predio_id
  AND LOWER(TRIM(a.nombre)) = LOWER(TRIM(b.nombre));

-- 2. Crear índice único case-insensitive
CREATE UNIQUE INDEX IF NOT EXISTS unique_predio_lote_nombre 
ON lotes (predio_id, LOWER(TRIM(nombre)));
