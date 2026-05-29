-- ============================================================================
-- Script de MIGRACIÓN 009 (ejecutar en Supabase SQL Editor)
-- Añade: columna modo_asignacion a la tabla inspecciones.
-- ============================================================================

ALTER TABLE public.inspecciones 
ADD COLUMN IF NOT EXISTS modo_asignacion VARCHAR(30) DEFAULT 'automatica' CHECK (modo_asignacion IN ('automatica', 'preferencia'));

COMMENT ON COLUMN public.inspecciones.modo_asignacion IS 'Modo de asignación: automatica (asignada por el sistema/admin) o preferencia (sugerida por el productor)';
