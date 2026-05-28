-- ============================================================================
-- FitoGestión — Script de MIGRACIÓN 004 (ejecutar en Supabase SQL Editor)
-- Corrige: Sensibilidad a mayúsculas en correos electrónicos de usuarios
-- Expande: Flexibilidad de las restricciones de estado de planta y severidad
-- ============================================================================

-- 1. Convertir todos los correos electrónicos existentes a minúsculas para evitar fallos de inicio de sesión
UPDATE usuarios 
SET email = LOWER(email);

-- 2. Eliminar la restricción actual de estado_planta
ALTER TABLE registro_plantas 
DROP CONSTRAINT IF EXISTS registro_plantas_estado_planta_check;

-- 3. Crear una nueva restricción más flexible para estado_planta (acepta las opciones del frontend)
ALTER TABLE registro_plantas 
ADD CONSTRAINT registro_plantas_estado_planta_check 
CHECK (estado_planta IN ('sana', 'enferma', 'muerta', 'Sana', 'Afectada'));

-- 4. Eliminar la restricción actual de severidad
ALTER TABLE registro_plantas 
DROP CONSTRAINT IF EXISTS registro_plantas_severidad_check;

-- 5. Crear una nueva restricción más flexible para severidad
ALTER TABLE registro_plantas 
ADD CONSTRAINT registro_plantas_severidad_check 
CHECK (severidad IN ('leve', 'moderado', 'severo', 'Leve', 'Moderado', 'Severo'));

-- Fin del script
