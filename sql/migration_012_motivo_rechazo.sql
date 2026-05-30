-- ============================================================================
-- FitoGestión — Script de MIGRACIÓN 012 (ejecutar en Supabase SQL Editor)
-- Objetivo: Añadir campo motivo_rechazo a la tabla inspecciones y actualizar el check constraint de estado.
-- ============================================================================

-- 1. Agregar columna 'motivo_rechazo' si no existe
ALTER TABLE public.inspecciones 
ADD COLUMN IF NOT EXISTS motivo_rechazo TEXT;

COMMENT ON COLUMN public.inspecciones.motivo_rechazo IS 'Justificación o motivo por el cual la solicitud de inspección manual (técnico de preferencia) fue rechazada por el administrador.';

-- 2. Modificar el check constraint de estado para admitir 'rechazada'
ALTER TABLE public.inspecciones DROP CONSTRAINT IF EXISTS inspecciones_estado_check;
ALTER TABLE public.inspecciones ADD CONSTRAINT inspecciones_estado_check CHECK (estado IN ('pendiente', 'en_progreso', 'completada', 'cancelada', 'rechazada'));
