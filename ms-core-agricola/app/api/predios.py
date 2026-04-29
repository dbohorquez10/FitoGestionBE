"""
Router de Predios.
Gestión de predios agrícolas vinculados a productores.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.supabase_client import get_supabase_client

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class PredioCreate(BaseModel):
    """Esquema para registrar un predio."""
    nombre: str
    productor_id: str
    departamento: str
    municipio: str
    vereda: Optional[str] = None
    numero_registro_ica: Optional[str] = None  # Número de registro ante el ICA
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    area_total: Optional[float] = None  # Hectáreas


class PredioUpdate(BaseModel):
    """Esquema para actualizar un predio."""
    nombre: Optional[str] = None
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    vereda: Optional[str] = None
    numero_registro_ica: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    area_total: Optional[float] = None


class PredioBatchRequest(BaseModel):
    """Esquema para solicitar múltiples predios por sus IDs."""
    ids: list[str]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/batch", summary="Obtener múltiples predios por IDs")
def obtener_predios_batch(request: PredioBatchRequest):
    """Retorna múltiples predios en una sola petición. Elimina el problema N+1 del frontend."""
    if not request.ids:
        return []
    supabase = get_supabase_client()
    response = supabase.table("predios").select("*").in_("id", request.ids).execute()
    return response.data

@router.get("/", summary="Listar predios")
def listar_predios():
    """Retorna todos los predios registrados."""
    supabase = get_supabase_client()
    response = supabase.table("predios").select("*").execute()
    return response.data


@router.get("/{predio_id}", summary="Obtener un predio por ID")
def obtener_predio(predio_id: str):
    """Retorna un predio específico con sus lotes asociados."""
    supabase = get_supabase_client()
    response = supabase.table("predios").select("*, lotes(*)").eq("id", predio_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Predio no encontrado")
    return response.data[0]


@router.get("/productor/{productor_id}", summary="Listar predios de un productor")
def listar_predios_por_productor(productor_id: str):
    """Retorna todos los predios de un productor específico."""
    supabase = get_supabase_client()
    response = supabase.table("predios").select("*").eq("productor_id", productor_id).execute()
    return response.data


@router.post("/", status_code=201, summary="Crear un predio")
def crear_predio(predio: PredioCreate):
    """Registra un nuevo predio agrícola."""
    supabase = get_supabase_client()
    response = supabase.table("predios").insert(predio.model_dump()).execute()
    return response.data[0]


@router.put("/{predio_id}", summary="Actualizar un predio")
def actualizar_predio(predio_id: str, predio: PredioUpdate):
    """Actualiza los datos de un predio existente."""
    supabase = get_supabase_client()
    data = {k: v for k, v in predio.model_dump().items() if v is not None}
    response = supabase.table("predios").update(data).eq("id", predio_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Predio no encontrado")
    return response.data[0]


@router.delete("/{predio_id}", status_code=204, summary="Eliminar un predio")
def eliminar_predio(predio_id: str):
    """Elimina un predio del sistema."""
    supabase = get_supabase_client()
    supabase.table("predios").delete().eq("id", predio_id).execute()
    return None
