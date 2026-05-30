"""
Router de Registro de Plantas.
Registro individual de plantas inspeccionadas con hallazgos fitosanitarios.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.core.supabase_client import get_supabase_client

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class RegistroPlantaCreate(BaseModel):
    """Esquema para registrar una planta inspeccionada."""
    sub_inspeccion_id: str
    numero_planta: int
    plaga_id: Optional[str] = None
    sintoma: Optional[str] = None
    severidad: Optional[str] = None  # 'leve', 'moderado', 'severo'
    incidencia: Optional[float] = None  # Porcentaje 0-100
    estado_planta: str = "sana"  # 'sana', 'enferma', 'muerta'
    observaciones: Optional[str] = None


class RegistroPlantaUpdate(BaseModel):
    """Esquema para actualizar el registro de una planta."""
    plaga_id: Optional[str] = None
    sintoma: Optional[str] = None
    severidad: Optional[str] = None
    incidencia: Optional[float] = None
    estado_planta: Optional[str] = None
    observaciones: Optional[str] = None


class ResumenFitosanitario(BaseModel):
    """Resumen calculado de una sub-inspección."""
    total_plantas: int
    plantas_sanas: int
    plantas_enfermas: int
    plantas_muertas: int
    porcentaje_incidencia: float
    plagas_detectadas: List[str]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/sub-inspeccion/{sub_inspeccion_id}", summary="Listar registros de una sub-inspección")
def listar_registros_plantas(sub_inspeccion_id: str):
    """Retorna todos los registros de plantas de una sub-inspección."""
    supabase = get_supabase_client()
    response = (
        supabase.table("registro_plantas")
        .select("*, plagas(nombre_comun)")
        .eq("sub_inspeccion_id", sub_inspeccion_id)
        .order("numero_planta")
        .execute()
    )
    return response.data


@router.get("/{registro_id}", summary="Obtener registro de planta por ID")
def obtener_registro_planta(registro_id: str):
    """Retorna un registro específico de planta inspeccionada."""
    supabase = get_supabase_client()
    response = (
        supabase.table("registro_plantas")
        .select("*, plagas(nombre_comun, nombre_cientifico)")
        .eq("id", registro_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Registro de planta no encontrado")
    return response.data[0]


@router.post("/", status_code=201, summary="Registrar una planta inspeccionada")
def crear_registro_planta(registro: RegistroPlantaCreate):
    """Registra una planta individual dentro de una sub-inspección."""
    supabase = get_supabase_client()
    response = supabase.table("registro_plantas").insert(registro.model_dump()).execute()
    return response.data[0]


@router.post("/bulk", status_code=201, summary="Registrar múltiples plantas")
def crear_registros_bulk(registros: List[RegistroPlantaCreate]):
    """
    Registra múltiples plantas de una sola vez (bulk insert).
    Útil para registro masivo durante el muestreo en campo.
    """
    try:
        supabase = get_supabase_client()
        data = [r.model_dump() for r in registros]
        if not data:
            return {"inserted": 0, "records": []}
        response = supabase.table("registro_plantas").insert(data).execute()
        return {"inserted": len(response.data), "records": response.data}
    except Exception as e:
        error_msg = str(e)
        if "foreign key" in error_msg.lower() or "violates foreign key constraint" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Error de integridad referencial: Asegúrese de que todos los IDs (como sub_inspeccion_id o plaga_id) sean válidos. Detalles: {error_msg}"
            )
        elif "check constraint" in error_msg.lower() or "violates check constraint" in error_msg.lower():
            raise HTTPException(
                status_code=422,
                detail=f"Error de validación de datos: Algunos registros no cumplen con las restricciones de la base de datos (ej. severidad o incidencia inválidas). Detalles: {error_msg}"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Error al procesar el guardado masivo de plantas: {error_msg}"
            )



@router.put("/{registro_id}", summary="Actualizar registro de planta")
def actualizar_registro_planta(registro_id: str, registro: RegistroPlantaUpdate):
    """Actualiza los datos de un registro de planta existente."""
    supabase = get_supabase_client()
    data = {k: v for k, v in registro.model_dump().items() if v is not None}
    response = (
        supabase.table("registro_plantas")
        .update(data)
        .eq("id", registro_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Registro de planta no encontrado")
    return response.data[0]


@router.delete("/{registro_id}", status_code=204, summary="Eliminar registro de planta")
def eliminar_registro_planta(registro_id: str):
    """Elimina un registro individual de planta."""
    supabase = get_supabase_client()
    supabase.table("registro_plantas").delete().eq("id", registro_id).execute()
    return None


@router.get(
    "/resumen/sub-inspeccion/{sub_inspeccion_id}",
    summary="Resumen fitosanitario de una sub-inspección",
    response_model=ResumenFitosanitario,
)
def resumen_fitosanitario(sub_inspeccion_id: str):
    """
    Calcula y retorna el resumen fitosanitario de una sub-inspección.
    Incluye conteos de plantas por estado y porcentaje de incidencia.
    """
    supabase = get_supabase_client()
    response = (
        supabase.table("registro_plantas")
        .select("*, plagas(nombre_comun)")
        .eq("sub_inspeccion_id", sub_inspeccion_id)
        .execute()
    )
    registros = response.data
    total = len(registros)
    if total == 0:
        return ResumenFitosanitario(
            total_plantas=0,
            plantas_sanas=0,
            plantas_enfermas=0,
            plantas_muertas=0,
            porcentaje_incidencia=0.0,
            plagas_detectadas=[],
        )

    sanas = sum(1 for r in registros if r.get("estado_planta") == "sana")
    enfermas = sum(1 for r in registros if r.get("estado_planta") == "enferma")
    muertas = sum(1 for r in registros if r.get("estado_planta") == "muerta")

    plagas = list(set(
        r["plagas"]["nombre_comun"]
        for r in registros
        if r.get("plagas") and r["plagas"].get("nombre_comun")
    ))

    return ResumenFitosanitario(
        total_plantas=total,
        plantas_sanas=sanas,
        plantas_enfermas=enfermas,
        plantas_muertas=muertas,
        porcentaje_incidencia=round(((enfermas + muertas) / total) * 100, 2),
        plagas_detectadas=plagas,
    )


class AlertaResponse(BaseModel):
    cultivo_id: str
    plaga_id: str
    nivel_alerta: str  # 'Bajo', 'Medio', 'Crítico'
    incidencia_promedio: float
    total_evaluadas: int
    total_afectadas: int


@router.get(
    "/alerta/{cultivo_id}/{plaga_id}",
    summary="Obtener nivel de alerta por cultivo y plaga",
    response_model=AlertaResponse,
)
def obtener_alerta_fitosanitaria(cultivo_id: str, plaga_id: str):
    """
    Calcula el nivel de alerta fitosanitaria para un cultivo y plaga específicos.
    Basado en el promedio de incidencia de las inspecciones.
    """
    supabase = get_supabase_client()
    
    # 1. Obtener lotes del cultivo
    lotes_res = supabase.table("lotes").select("id").eq("cultivo_id", cultivo_id).execute()
    lote_ids = [l["id"] for l in lotes_res.data]
    if not lote_ids:
        return AlertaResponse(cultivo_id=cultivo_id, plaga_id=plaga_id, nivel_alerta="Bajo", incidencia_promedio=0.0, total_evaluadas=0, total_afectadas=0)
    
    # 2. Obtener inspecciones de esos lotes
    inspecciones_res = supabase.table("inspecciones").select("id").in_("lote_id", lote_ids).execute()
    inspeccion_ids = [i["id"] for i in inspecciones_res.data]
    if not inspeccion_ids:
        return AlertaResponse(cultivo_id=cultivo_id, plaga_id=plaga_id, nivel_alerta="Bajo", incidencia_promedio=0.0, total_evaluadas=0, total_afectadas=0)
        
    # 3. Obtener sub-inspecciones
    subs_res = supabase.table("sub_inspecciones").select("id").in_("inspeccion_id", inspeccion_ids).execute()
    sub_ids = [s["id"] for s in subs_res.data]
    if not sub_ids:
        return AlertaResponse(cultivo_id=cultivo_id, plaga_id=plaga_id, nivel_alerta="Bajo", incidencia_promedio=0.0, total_evaluadas=0, total_afectadas=0)

    # 4. Obtener registros de plantas afectadas por la plaga en esas sub-inspecciones
    # Consultamos TODOS los registros de esas sub-inspecciones para saber el total evaluado
    registros_res = supabase.table("registro_plantas").select("plaga_id, estado_planta").in_("sub_inspeccion_id", sub_ids).execute()
    registros = registros_res.data
    
    total_evaluadas = len(registros)
    if total_evaluadas == 0:
        return AlertaResponse(cultivo_id=cultivo_id, plaga_id=plaga_id, nivel_alerta="Bajo", incidencia_promedio=0.0, total_evaluadas=0, total_afectadas=0)

    # Contamos las afectadas específicamente por esta plaga
    afectadas = [r for r in registros if r.get("plaga_id") == plaga_id and r.get("estado_planta") in ["enferma", "muerta"]]
    total_afectadas = len(afectadas)
    
    incidencia = (total_afectadas / total_evaluadas) * 100
    
    # Lógica de negocio normativa para el nivel de alerta
    if incidencia > 10.0:
        nivel = "Crítico"
    elif incidencia >= 5.0:
        nivel = "Medio"
    else:
        nivel = "Bajo"
        
    return AlertaResponse(
        cultivo_id=cultivo_id,
        plaga_id=plaga_id,
        nivel_alerta=nivel,
        incidencia_promedio=round(incidencia, 2),
        total_evaluadas=total_evaluadas,
        total_afectadas=total_afectadas
    )
