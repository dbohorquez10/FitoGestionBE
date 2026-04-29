"""
Router de Lotes.
Gestión de lotes dentro de un predio agrícola.
Incluye filtrado por productor para garantizar aislamiento de datos.
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
    num_plantas: Optional[int] = None  # Total absoluto de plantas
    estado: str = "Óptimo"  # 'Óptimo', 'Alerta', 'Crítico', 'En Cuarentena'


class LoteUpdate(BaseModel):
    """Esquema para actualizar un lote."""
    nombre: Optional[str] = None
    cultivo_id: Optional[str] = None
    area: Optional[float] = None
    num_plantas: Optional[int] = None
    estado: Optional[str] = None  # 'Óptimo', 'Alerta', 'Crítico', 'En Cuarentena'


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", summary="Listar lotes")
def listar_lotes(predio_id: Optional[str] = None):
    """
    Retorna lotes. Si se pasa predio_id como query param, filtra solo los
    de ese predio. Sin filtro retorna todos (uso admin).
    """
    supabase = get_supabase_client()
    query = supabase.table("lotes").select("*, cultivos(nombre)")
    if predio_id:
        query = query.eq("predio_id", predio_id)
    response = query.execute()
    return response.data


@router.get("/{lote_id}", summary="Obtener un lote por ID")
def obtener_lote(lote_id: str):
    """Retorna un lote específico por su ID."""
    supabase = get_supabase_client()
    response = supabase.table("lotes").select("*, cultivos(nombre), predios(nombre)").eq("id", lote_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return response.data[0]


@router.get("/predio/{predio_id}", summary="Listar lotes de un predio")
def listar_lotes_por_predio(predio_id: str):
    """Retorna todos los lotes de un predio específico."""
    supabase = get_supabase_client()
    response = supabase.table("lotes").select("*, cultivos(nombre)").eq("predio_id", predio_id).execute()
    return response.data


@router.get("/productor/{productor_id}", summary="Listar lotes de un productor")
def listar_lotes_por_productor(productor_id: str):
    """
    Retorna todos los lotes de todos los predios de un productor.
    Realiza join: lotes → predios (filtrado por productor_id).
    """
    supabase = get_supabase_client()
    # 1. Obtener los predios del productor
    predios_res = supabase.table("predios").select("id").eq("productor_id", productor_id).execute()
    predio_ids = [p["id"] for p in predios_res.data]
    if not predio_ids:
        return []
    # 2. Obtener lotes de esos predios
    response = (
        supabase.table("lotes")
        .select("*, cultivos(nombre), predios(nombre)")
        .in_("predio_id", predio_ids)
        .execute()
    )
    return response.data


@router.post("/", status_code=201, summary="Crear un lote")
def crear_lote(lote: LoteCreate):
    """Registra un nuevo lote dentro de un predio."""
    supabase = get_supabase_client()
    # Verificar que el predio exista
    predio = supabase.table("predios").select("id").eq("id", lote.predio_id).execute()
    if not predio.data:
        raise HTTPException(status_code=404, detail="Predio no encontrado")
    response = supabase.table("lotes").insert(lote.model_dump()).execute()
    return response.data[0]


@router.put("/{lote_id}", summary="Actualizar un lote")
def actualizar_lote(lote_id: str, lote: LoteUpdate):
    """Actualiza los datos de un lote existente."""
    supabase = get_supabase_client()
    data = {k: v for k, v in lote.model_dump().items() if v is not None}
    response = supabase.table("lotes").update(data).eq("id", lote_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return response.data[0]


@router.delete("/{lote_id}", status_code=204, summary="Eliminar un lote")
def eliminar_lote(lote_id: str):
    """Elimina un lote del sistema."""
    supabase = get_supabase_client()
    supabase.table("lotes").delete().eq("id", lote_id).execute()
    return None
