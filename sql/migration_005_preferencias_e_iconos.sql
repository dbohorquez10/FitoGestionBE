-- Agregar columnas icon y color a plagas
ALTER TABLE public.plagas
ADD COLUMN IF NOT EXISTS icon VARCHAR(50),
ADD COLUMN IF NOT EXISTS color VARCHAR(20);

-- Actualizar plagas existentes con los iconos que teníamos quemados
UPDATE public.plagas SET icon = 'pest_control', color = '#ef4444' WHERE tipo = 'insecto';
UPDATE public.plagas SET icon = 'spa', color = '#8b5cf6' WHERE tipo = 'hongo';
UPDATE public.plagas SET icon = 'coronavirus', color = '#f59e0b' WHERE tipo = 'bacteria';
UPDATE public.plagas SET icon = 'biotech', color = '#06b6d4' WHERE tipo = 'virus';
UPDATE public.plagas SET icon = 'bug_report', color = '#ec4899' WHERE tipo = 'nematodo';
UPDATE public.plagas SET icon = 'grass', color = '#22c55e' WHERE tipo = 'maleza';

-- Set defaults if icon or color is null later
ALTER TABLE public.plagas
ALTER COLUMN icon SET DEFAULT 'bug_report',
ALTER COLUMN color SET DEFAULT '#64748b';

-- Tabla de preferencias de usuario
CREATE TABLE IF NOT EXISTS public.usuario_preferencias (
    usuario_id UUID PRIMARY KEY REFERENCES public.usuarios(id) ON DELETE CASCADE,
    alertas_plaga_grave BOOLEAN DEFAULT true,
    nuevas_solicitudes BOOLEAN DEFAULT true,
    inspecciones_vencidas BOOLEAN DEFAULT true,
    resumen_semanal BOOLEAN DEFAULT false,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Políticas de RLS para usuario_preferencias (se permite todo temporalmente como el resto de tablas dev)
ALTER TABLE public.usuario_preferencias ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Permitir todo a todos en usuario_preferencias"
    ON public.usuario_preferencias FOR ALL
    USING (true) WITH CHECK (true);
