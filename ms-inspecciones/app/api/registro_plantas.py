"""
Router de Registro de Plantas.
Registro individual de plantas inspeccionadas con hallazgos fitosanitarios.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from app.core.supabase_client import get_supabase_client
from app.core.security import get_current_user, require_role

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class RegistroPlantaCreate(BaseModel):
    """Esquema para registrar una planta inspeccionada."""
    sub_inspeccion_id: str
    numero_planta: int
    plaga_id: Optional[str] = None
    sintoma: Optional[str] = None
    severidad: Optional[str] = Field(None, pattern="^(leve|moderado|severo)$")  # 'leve', 'moderado', 'severo'
    incidencia: Optional[float] = Field(None, ge=0.0, le=100.0)  # Porcentaje 0-100
    estado_planta: str = Field("sana", pattern="^(sana|enferma|muerta)$")  # 'sana', 'enferma', 'muerta'
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
def listar_registros_plantas(sub_inspeccion_id: str,
                             current_user: dict = Depends(get_current_user)):
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
def obtener_registro_planta(registro_id: str,
                            current_user: dict = Depends(get_current_user)):
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
def crear_registro_planta(registro: RegistroPlantaCreate,
                          current_user: dict = Depends(require_role(['tecnico', 'admin']))):
    """Registra una planta individual dentro de una sub-inspección."""
    supabase = get_supabase_client()
    response = supabase.table("registro_plantas").insert(registro.model_dump()).execute()
    return response.data[0]


@router.post("/bulk", status_code=201, summary="Registrar múltiples plantas")
def crear_registros_bulk(registros: List[RegistroPlantaCreate],
                         current_user: dict = Depends(require_role(['tecnico', 'admin']))):
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
def actualizar_registro_planta(registro_id: str, registro: RegistroPlantaUpdate,
                               current_user: dict = Depends(require_role(['tecnico', 'admin']))):
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
def eliminar_registro_planta(registro_id: str,
                             current_user: dict = Depends(require_role(['admin']))):
    """Elimina un registro individual de planta."""
    supabase = get_supabase_client()
    supabase.table("registro_plantas").delete().eq("id", registro_id).execute()
    return None


@router.get(
    "/resumen/sub-inspeccion/{sub_inspeccion_id}",
    summary="Resumen fitosanitario de una sub-inspección",
    response_model=ResumenFitosanitario,
)
def resumen_fitosanitario(sub_inspeccion_id: str,
                          current_user: dict = Depends(get_current_user)):
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
def obtener_alerta_fitosanitaria(cultivo_id: str, plaga_id: str,
                                  current_user: dict = Depends(get_current_user)):
    """
    Calcula el nivel de alerta fitosanitaria para un cultivo y plaga específicos.
    Llama a la función almacenada fn_alerta_fitosanitaria en Supabase para optimizar rendimiento.
    """
    supabase = get_supabase_client()
    try:
        response = supabase.rpc("fn_alerta_fitosanitaria", {
            "p_cultivo_id": cultivo_id,
            "p_plaga_id": plaga_id
        }).execute()
        
        if not response.data:
            return AlertaResponse(
                cultivo_id=cultivo_id,
                plaga_id=plaga_id,
                nivel_alerta="Bajo",
                incidencia_promedio=0.0,
                total_evaluadas=0,
                total_afectadas=0
            )
            
        # El RPC puede retornar una lista o un único objeto
        data = response.data
        if isinstance(data, list):
            if not data:
                return AlertaResponse(
                    cultivo_id=cultivo_id,
                    plaga_id=plaga_id,
                    nivel_alerta="Bajo",
                    incidencia_promedio=0.0,
                    total_evaluadas=0,
                    total_afectadas=0
                )
            record = data[0]
        else:
            record = data
            
        return AlertaResponse(
            cultivo_id=record.get("cultivo_id") or cultivo_id,
            plaga_id=record.get("plaga_id") or plaga_id,
            nivel_alerta=record.get("nivel_alerta") or "Bajo",
            incidencia_promedio=record.get("incidencia_promedio") or 0.0,
            total_evaluadas=record.get("total_evaluadas") or 0,
            total_afectadas=record.get("total_afectadas") or 0
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener alerta fitosanitaria: {str(e)}"
        )
