"""
Router de Catálogos.
Gestión de Plagas y Cultivos registrados ante el ICA.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.supabase_client import get_supabase_client

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class PlagaCreate(BaseModel):
    """Esquema para registrar una plaga."""
    nombre_comun: str
    nombre_cientifico: Optional[str] = None
    tipo: str  # 'insecto', 'hongo', 'bacteria', 'virus', 'nematodo', 'maleza'
    descripcion: Optional[str] = None


class CultivoCreate(BaseModel):
    """Esquema para registrar un cultivo."""
    nombre: str
    nombre_cientifico: Optional[str] = None
    variedad: Optional[str] = None
    descripcion: Optional[str] = None


# ── Plagas ────────────────────────────────────────────────────────────────────

@router.get("/plagas", summary="Listar plagas")
async def listar_plagas():
    """Retorna todas las plagas del catálogo."""
    supabase = get_supabase_client()
    response = supabase.table("plagas").select("*").execute()
    return response.data


@router.post("/plagas", status_code=201, summary="Crear una plaga")
async def crear_plaga(plaga: PlagaCreate):
    """Registra una nueva plaga en el catálogo."""
    supabase = get_supabase_client()
    response = supabase.table("plagas").insert(plaga.model_dump()).execute()
    return response.data[0]


@router.get("/plagas/{plaga_id}", summary="Obtener plaga por ID")
async def obtener_plaga(plaga_id: str):
    """Retorna una plaga específica por su ID."""
    supabase = get_supabase_client()
    response = supabase.table("plagas").select("*").eq("id", plaga_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Plaga no encontrada")
    return response.data[0]


@router.put("/plagas/{plaga_id}", summary="Actualizar plaga")
async def actualizar_plaga(plaga_id: str, plaga: PlagaCreate):
    """Actualiza una plaga existente."""
    supabase = get_supabase_client()
    response = supabase.table("plagas").update(plaga.model_dump()).eq("id", plaga_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Plaga no encontrada")
    return response.data[0]


@router.delete("/plagas/{plaga_id}", status_code=204, summary="Eliminar plaga")
async def eliminar_plaga(plaga_id: str):
    """Elimina una plaga del catálogo."""
    supabase = get_supabase_client()
    supabase.table("plagas").delete().eq("id", plaga_id).execute()
    return None


# ── Cultivos ──────────────────────────────────────────────────────────────────

@router.get("/cultivos", summary="Listar cultivos")
async def listar_cultivos():
    """Retorna todos los cultivos del catálogo."""
    supabase = get_supabase_client()
    response = supabase.table("cultivos").select("*").execute()
    return response.data


@router.post("/cultivos", status_code=201, summary="Crear un cultivo")
async def crear_cultivo(cultivo: CultivoCreate):
    """Registra un nuevo cultivo en el catálogo."""
    supabase = get_supabase_client()
    response = supabase.table("cultivos").insert(cultivo.model_dump()).execute()
    return response.data[0]


@router.get("/cultivos/{cultivo_id}", summary="Obtener cultivo por ID")
async def obtener_cultivo(cultivo_id: str):
    """Retorna un cultivo específico por su ID."""
    supabase = get_supabase_client()
    response = supabase.table("cultivos").select("*").eq("id", cultivo_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Cultivo no encontrado")
    return response.data[0]


@router.put("/cultivos/{cultivo_id}", summary="Actualizar cultivo")
async def actualizar_cultivo(cultivo_id: str, cultivo: CultivoCreate):
    """Actualiza un cultivo existente."""
    supabase = get_supabase_client()
    response = supabase.table("cultivos").update(cultivo.model_dump()).eq("id", cultivo_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Cultivo no encontrado")
    return response.data[0]


@router.delete("/cultivos/{cultivo_id}", status_code=204, summary="Eliminar cultivo")
async def eliminar_cultivo(cultivo_id: str):
    """Elimina un cultivo del catálogo."""
    supabase = get_supabase_client()
    supabase.table("cultivos").delete().eq("id", cultivo_id).execute()
    return None
