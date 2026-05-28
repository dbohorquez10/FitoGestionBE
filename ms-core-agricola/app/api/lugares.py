"""
Router de Lugares de Producción.
Gestión de lugares de producción agrícola vinculados a productores.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.supabase_client import get_supabase_client

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class LugarCreate(BaseModel):
    """Esquema para registrar un lugar de producción."""
    nombre: str
    productor_id: str
    numero_registro_ica: Optional[str] = None
    departamento: str
    municipio: str
    vereda: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None


class LugarUpdate(BaseModel):
    """Esquema para actualizar un lugar de producción."""
    nombre: Optional[str] = None
    numero_registro_ica: Optional[str] = None
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    vereda: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None


class LugarBatchRequest(BaseModel):
    """Esquema para solicitar múltiples lugares por sus IDs."""
    ids: list[str]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/batch", summary="Obtener múltiples lugares por IDs")
def obtener_lugares_batch(request: LugarBatchRequest):
    """Retorna múltiples lugares en una sola petición."""
    if not request.ids:
        return []
    supabase = get_supabase_client()
    response = supabase.table("lugares_produccion").select("*").in_("id", request.ids).execute()
    return response.data

@router.get("/", summary="Listar lugares de producción")
def listar_lugares(skip: int = 0, limit: int = 100):
    """Retorna todos los lugares registrados."""
    supabase = get_supabase_client()
    response = supabase.table("lugares_produccion").select("*").range(skip, skip + limit - 1).execute()
    return response.data


@router.get("/productor/{productor_id}", summary="Listar lugares de un productor")
def listar_lugares_por_productor(productor_id: str):
    """Retorna todos los lugares de un productor específico con sus predios y lotes."""
    supabase = get_supabase_client()
    response = supabase.table("lugares_produccion").select("*, predios(*, lotes(*))").eq("productor_id", productor_id).execute()
    return response.data


@router.get("/{lugar_id}", summary="Obtener un lugar por ID")
def obtener_lugar(lugar_id: str):
    """Retorna un lugar específico con sus predios anidados."""
    supabase = get_supabase_client()
    response = supabase.table("lugares_produccion").select("*, predios(*, lotes(*))").eq("id", lugar_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Lugar de producción no encontrado")
    return response.data[0]


@router.post("/", status_code=201, summary="Crear un lugar de producción")
def crear_lugar(lugar: LugarCreate):
    """Registra un nuevo lugar de producción."""
    supabase = get_supabase_client()
    response = supabase.table("lugares_produccion").insert(lugar.model_dump()).execute()
    return response.data[0]


@router.put("/{lugar_id}", summary="Actualizar un lugar")
def actualizar_lugar(lugar_id: str, lugar: LugarUpdate):
    """Actualiza los datos de un lugar existente."""
    supabase = get_supabase_client()
    data = {k: v for k, v in lugar.model_dump().items() if v is not None}
    response = supabase.table("lugares_produccion").update(data).eq("id", lugar_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Lugar no encontrado")
    return response.data[0]


@router.delete("/{lugar_id}", status_code=204, summary="Eliminar un lugar")
def eliminar_lugar(lugar_id: str):
    """Elimina un lugar del sistema."""
    supabase = get_supabase_client()
    supabase.table("lugares_produccion").delete().eq("id", lugar_id).execute()
    return None
