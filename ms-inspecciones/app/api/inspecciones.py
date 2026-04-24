"""
Router de Inspecciones.
Flujo transaccional completo para inspecciones fitosanitarias ICA.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.core.supabase_client import get_supabase_client

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class InspeccionCreate(BaseModel):
    """Esquema para crear una inspección fitosanitaria."""
    tecnico_id: str
    predio_id: str
    lote_id: str
    fecha_inspeccion: date
    tipo_inspeccion: str  # 'rutinaria', 'seguimiento', 'emergencia'
    observaciones: Optional[str] = None


class InspeccionUpdate(BaseModel):
    """Esquema para actualizar una inspección."""
    estado: Optional[str] = None  # 'pendiente', 'en_progreso', 'completada', 'cancelada'
    observaciones: Optional[str] = None
    resultado_general: Optional[str] = None  # 'sin_novedad', 'con_hallazgos', 'critico'
    fecha_cierre: Optional[date] = None


class InspeccionResponse(BaseModel):
    """Esquema de respuesta de una inspección."""
    id: str
    tecnico_id: str
    predio_id: str
    lote_id: str
    fecha_inspeccion: date
    tipo_inspeccion: str
    estado: str
    observaciones: Optional[str] = None
    resultado_general: Optional[str] = None
    created_at: Optional[datetime] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", summary="Listar inspecciones")
async def listar_inspecciones():
    """Retorna todas las inspecciones registradas."""
    supabase = get_supabase_client()
    response = supabase.table("inspecciones").select("*").order("fecha_inspeccion", desc=True).execute()
    return response.data


@router.get("/{inspeccion_id}", summary="Obtener una inspección por ID")
async def obtener_inspeccion(inspeccion_id: str):
    """Retorna una inspección con sus sub-inspecciones y registros de plantas."""
    supabase = get_supabase_client()
    response = (
        supabase.table("inspecciones")
        .select("*, sub_inspecciones(*, registro_plantas(*))")
        .eq("id", inspeccion_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Inspección no encontrada")
    return response.data[0]


@router.get("/tecnico/{tecnico_id}", summary="Inspecciones por técnico")
async def listar_inspecciones_por_tecnico(tecnico_id: str):
    """Retorna todas las inspecciones asignadas a un técnico."""
    supabase = get_supabase_client()
    response = (
        supabase.table("inspecciones")
        .select("*")
        .eq("tecnico_id", tecnico_id)
        .order("fecha_inspeccion", desc=True)
        .execute()
    )
    return response.data


@router.get("/predio/{predio_id}", summary="Inspecciones por predio")
async def listar_inspecciones_por_predio(predio_id: str):
    """Retorna todas las inspecciones realizadas en un predio."""
    supabase = get_supabase_client()
    response = (
        supabase.table("inspecciones")
        .select("*")
        .eq("predio_id", predio_id)
        .order("fecha_inspeccion", desc=True)
        .execute()
    )
    return response.data


@router.post("/", status_code=201, summary="Crear una inspección")
async def crear_inspeccion(inspeccion: InspeccionCreate):
    """
    Crea una nueva inspección fitosanitaria.
    Se inicializa con estado 'pendiente'.
    """
    supabase = get_supabase_client()
    data = inspeccion.model_dump()
    data["estado"] = "pendiente"
    data["fecha_inspeccion"] = str(data["fecha_inspeccion"])
    response = supabase.table("inspecciones").insert(data).execute()
    return response.data[0]


@router.put("/{inspeccion_id}", summary="Actualizar una inspección")
async def actualizar_inspeccion(inspeccion_id: str, inspeccion: InspeccionUpdate):
    """Actualiza el estado o datos de una inspección existente."""
    supabase = get_supabase_client()
    data = {k: v for k, v in inspeccion.model_dump().items() if v is not None}
    if "fecha_cierre" in data:
        data["fecha_cierre"] = str(data["fecha_cierre"])
    response = supabase.table("inspecciones").update(data).eq("id", inspeccion_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Inspección no encontrada")
    return response.data[0]


@router.delete("/{inspeccion_id}", status_code=204, summary="Eliminar una inspección")
async def eliminar_inspeccion(inspeccion_id: str):
    """Elimina una inspección y sus registros asociados (cascade)."""
    supabase = get_supabase_client()
    supabase.table("inspecciones").delete().eq("id", inspeccion_id).execute()
    return None
