"""
Router de Lotes.
Gestión de lotes dentro de un predio agrícola.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.supabase_client import get_supabase_client

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class LoteCreate(BaseModel):
    """Esquema para registrar un lote."""
    predio_id: str
    nombre: str
    cultivo_id: Optional[str] = None
    area: Optional[float] = None  # Hectáreas
    num_plantas: Optional[int] = None
    estado: str = "activo"  # 'activo', 'inactivo', 'en_cuarentena'


class LoteUpdate(BaseModel):
    """Esquema para actualizar un lote."""
    nombre: Optional[str] = None
    cultivo_id: Optional[str] = None
    area: Optional[float] = None
    num_plantas: Optional[int] = None
    estado: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", summary="Listar lotes")
async def listar_lotes():
    """Retorna todos los lotes registrados."""
    supabase = get_supabase_client()
    response = supabase.table("lotes").select("*, cultivos(nombre)").execute()
    return response.data


@router.get("/{lote_id}", summary="Obtener un lote por ID")
async def obtener_lote(lote_id: str):
    """Retorna un lote específico por su ID."""
    supabase = get_supabase_client()
    response = supabase.table("lotes").select("*, cultivos(nombre), predios(nombre)").eq("id", lote_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return response.data[0]


@router.get("/predio/{predio_id}", summary="Listar lotes de un predio")
async def listar_lotes_por_predio(predio_id: str):
    """Retorna todos los lotes de un predio específico."""
    supabase = get_supabase_client()
    response = supabase.table("lotes").select("*, cultivos(nombre)").eq("predio_id", predio_id).execute()
    return response.data


@router.post("/", status_code=201, summary="Crear un lote")
async def crear_lote(lote: LoteCreate):
    """Registra un nuevo lote dentro de un predio."""
    supabase = get_supabase_client()
    response = supabase.table("lotes").insert(lote.model_dump()).execute()
    return response.data[0]


@router.put("/{lote_id}", summary="Actualizar un lote")
async def actualizar_lote(lote_id: str, lote: LoteUpdate):
    """Actualiza los datos de un lote existente."""
    supabase = get_supabase_client()
    data = {k: v for k, v in lote.model_dump().items() if v is not None}
    response = supabase.table("lotes").update(data).eq("id", lote_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return response.data[0]


@router.delete("/{lote_id}", status_code=204, summary="Eliminar un lote")
async def eliminar_lote(lote_id: str):
    """Elimina un lote del sistema."""
    supabase = get_supabase_client()
    supabase.table("lotes").delete().eq("id", lote_id).execute()
    return None
