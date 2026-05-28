-- ============================================================================
-- Script de Limpieza de Usuarios y Dependencias
-- Conserva ÚNICAMENTE a los siguientes usuarios:
-- tecnico@fitogestion.com, admin@fitogestion.com, productor@fitogestion.com, aa@a.com, a@a.com
-- ============================================================================

BEGIN;

-- 1. Eliminar inspecciones asignadas a los técnicos que van a ser eliminados
-- (Para evitar el error del constraint ON DELETE RESTRICT en inspecciones.tecnico_id)
DELETE FROM public.inspecciones 
WHERE tecnico_id IN (
    SELECT id FROM public.usuarios 
    WHERE email NOT IN (
        'tecnico@fitogestion.com', 
        'admin@fitogestion.com', 
        'productor@fitogestion.com', 
        'aa@a.com', 
        'a@a.com'
    )
);

-- 2. Eliminar usuarios de la tabla pública
-- Gracias a ON DELETE CASCADE, esto borrará automáticamente sus lugares_produccion,
-- predios, lotes e inspecciones asociadas.
DELETE FROM public.usuarios 
WHERE email NOT IN (
    'tecnico@fitogestion.com', 
    'admin@fitogestion.com', 
    'productor@fitogestion.com', 
    'aa@a.com', 
    'a@a.com'
);

-- 3. Eliminar de la tabla del sistema de Autenticación de Supabase
DELETE FROM auth.users 
WHERE email NOT IN (
    'tecnico@fitogestion.com', 
    'admin@fitogestion.com', 
    'productor@fitogestion.com', 
    'aa@a.com', 
    'a@a.com'
);

COMMIT;
