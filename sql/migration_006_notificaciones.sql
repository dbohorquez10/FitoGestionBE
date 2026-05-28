-- ========================================================
-- Migración 006: Sistema de Notificaciones
-- ========================================================

-- Crear tabla notificaciones
CREATE TABLE IF NOT EXISTS public.notificaciones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    titulo VARCHAR(150) NOT NULL,
    mensaje TEXT NOT NULL,
    tipo VARCHAR(50) DEFAULT 'info',
    leido BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Políticas RLS
ALTER TABLE public.notificaciones ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Usuarios pueden ver sus propias notificaciones" 
ON public.notificaciones FOR SELECT 
USING (auth.uid() = usuario_id);

CREATE POLICY "Usuarios pueden actualizar sus propias notificaciones" 
ON public.notificaciones FOR UPDATE 
USING (auth.uid() = usuario_id);

CREATE POLICY "Sistema puede insertar notificaciones" 
ON public.notificaciones FOR INSERT 
WITH CHECK (true);
