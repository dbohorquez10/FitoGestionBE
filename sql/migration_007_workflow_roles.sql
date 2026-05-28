-- ============================================================================
-- UmbraCode — Script de MIGRACIÓN 007 (ejecutar en Supabase SQL Editor)
-- Añade: campos de aprobación y campos calculados a inspecciones.
-- Redefine: trigger de cálculo de incidencias a nivel global.
-- Migra: datos iniciales para coherencia con el nuevo flujo de trabajo.
-- ============================================================================

-- 1. Añadir columnas a la tabla de inspecciones
ALTER TABLE inspecciones ADD COLUMN IF NOT EXISTS estado_aprobacion VARCHAR(30) DEFAULT 'pendiente' CHECK (estado_aprobacion IN ('pendiente', 'aprobado', 'rechazado'));
ALTER TABLE inspecciones ADD COLUMN IF NOT EXISTS incidencia_global_pct DECIMAL(5, 2) DEFAULT 0.0;
ALTER TABLE inspecciones ADD COLUMN IF NOT EXISTS nivel_alerta VARCHAR(50) DEFAULT 'Normal (Monitoreo)';

-- 2. Redefinir la función disparadora para calcular métricas locales y globales
CREATE OR REPLACE FUNCTION fn_calcular_incidencia()
RETURNS TRIGGER AS $$
DECLARE
    v_sub_id UUID;
    v_inspeccion_id UUID;
    v_lote_id UUID;
    v_total INT;
    v_afectadas INT;
    v_incidencia DECIMAL;
    v_total_evaluadas INT;
    v_total_enfermas INT;
    v_incidencia_global DECIMAL;
    v_nivel_alerta VARCHAR(50);
BEGIN
    -- Identificar la sub_inspección afectada
    IF TG_OP = 'DELETE' THEN
        v_sub_id := OLD.sub_inspeccion_id;
    ELSE
        v_sub_id := NEW.sub_inspeccion_id;
    END IF;

    -- Calcular métricas para esta sub_inspección
    SELECT COUNT(*), COUNT(*) FILTER (WHERE estado_planta IN ('enferma', 'muerta'))
    INTO v_total, v_afectadas
    FROM registro_plantas
    WHERE sub_inspeccion_id = v_sub_id;

    -- Actualizar el contador de plantas_evaluadas en la sub_inspección
    UPDATE sub_inspecciones
    SET plantas_evaluadas = v_total
    WHERE id = v_sub_id;

    -- Obtener ID de la inspección principal
    SELECT inspeccion_id INTO v_inspeccion_id FROM sub_inspecciones WHERE id = v_sub_id;

    -- Calcular métricas a nivel global de la inspección
    SELECT COALESCE(SUM(plantas_evaluadas), 0)
    INTO v_total_evaluadas
    FROM sub_inspecciones
    WHERE inspeccion_id = v_inspeccion_id;

    SELECT COUNT(*)
    INTO v_total_enfermas
    FROM registro_plantas rp
    JOIN sub_inspecciones si ON rp.sub_inspeccion_id = si.id
    WHERE si.inspeccion_id = v_inspeccion_id AND rp.estado_planta IN ('enferma', 'muerta');

    IF v_total_evaluadas > 0 THEN
        v_incidencia_global := (v_total_enfermas::DECIMAL / v_total_evaluadas) * 100;
    ELSE
        v_incidencia_global := 0.0;
    END IF;

    IF v_incidencia_global >= 15.0 THEN
        v_nivel_alerta := 'Crítico (Cuarentena Recomendada)';
    ELSIF v_incidencia_global >= 5.0 THEN
        v_nivel_alerta := 'Alerta (Tratamiento Requerido)';
    ELSE
        v_nivel_alerta := 'Normal (Monitoreo)';
    END IF;

    -- Actualizar la inspección principal con la incidencia y alerta globales
    UPDATE inspecciones
    SET incidencia_global_pct = ROUND(v_incidencia_global, 2),
        nivel_alerta = v_nivel_alerta
    WHERE id = v_inspeccion_id;

    -- Si hay plantas evaluadas, calcular incidencia y verificar estado del lote
    IF v_total > 0 THEN
        v_incidencia := (v_afectadas::DECIMAL / v_total) * 100;
        
        IF v_incidencia > 10.0 THEN
            SELECT lote_id INTO v_lote_id FROM inspecciones WHERE id = v_inspeccion_id;
            
            -- Actualizar estado del lote a Crítico
            UPDATE lotes
            SET estado = 'Crítico'
            WHERE id = v_lote_id AND estado != 'Crítico';
        END IF;
    END IF;

    RETURN NULL; -- AFTER trigger
END;
$$ LANGUAGE plpgsql;

-- 3. Calcular e inicializar campos para los registros históricos existentes
UPDATE inspecciones i
SET
  incidencia_global_pct = (
    SELECT 
      CASE 
        WHEN total_eval > 0 THEN ROUND((total_enf::DECIMAL / total_eval) * 100, 2)
        ELSE 0.0
      END
    FROM (
      SELECT 
        (SELECT COALESCE(SUM(plantas_evaluadas), 0) FROM sub_inspecciones WHERE inspeccion_id = i.id) as total_eval,
        (SELECT COUNT(*) FROM registro_plantas rp JOIN sub_inspecciones si ON rp.sub_inspeccion_id = si.id WHERE si.inspeccion_id = i.id AND rp.estado_planta IN ('enferma', 'muerta')) as total_enf
    ) sub
  ),
  nivel_alerta = (
    SELECT 
      CASE 
        WHEN total_eval > 0 AND (total_enf::DECIMAL / total_eval) * 100 >= 15.0 THEN 'Crítico (Cuarentena Recomendada)'
        WHEN total_eval > 0 AND (total_enf::DECIMAL / total_eval) * 100 >= 5.0 THEN 'Alerta (Tratamiento Requerido)'
        ELSE 'Normal (Monitoreo)'
      END
    FROM (
      SELECT 
        (SELECT COALESCE(SUM(plantas_evaluadas), 0) FROM sub_inspecciones WHERE inspeccion_id = i.id) as total_eval,
        (SELECT COUNT(*) FROM registro_plantas rp JOIN sub_inspecciones si ON rp.sub_inspeccion_id = si.id WHERE si.inspeccion_id = i.id AND rp.estado_planta IN ('enferma', 'muerta')) as total_enf
    ) sub
  ),
  estado_aprobacion = (
    CASE
      WHEN estado = 'completada' THEN 'aprobado'
      ELSE 'pendiente'
    END
  );
