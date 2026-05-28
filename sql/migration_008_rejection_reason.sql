-- ============================================================================
-- UmbraCode — Script de MIGRACIÓN 008 (ejecutar en Supabase SQL Editor)
-- Añade: campo razon_rechazo a la tabla inspecciones.
-- ============================================================================

ALTER TABLE inspecciones ADD COLUMN IF NOT EXISTS razon_rechazo TEXT;

COMMENT ON COLUMN inspecciones.razon_rechazo IS 'Justificación o razón por la cual la inspección fue rechazada/anulada.';
