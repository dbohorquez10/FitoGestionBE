-- ============================================================================
-- FitoGestión — Script de MIGRACIÓN 011 (ejecutar en Supabase SQL Editor)
-- Objetivo: Añadir campo de estado (aprobación) a la tabla plagas
-- ============================================================================

-- 1. Agregar columna 'estado' a la tabla plagas con valor por defecto 'aprobado'
ALTER TABLE plagas 
ADD COLUMN IF NOT EXISTS estado VARCHAR(30) DEFAULT 'aprobado' CHECK (estado IN ('aprobado', 'pendiente'));

-- 2. Asegurar que las plagas existentes estén marcadas como aprobadas
UPDATE plagas 
SET estado = 'aprobado' 
WHERE estado IS NULL;
