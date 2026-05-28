"""
Router de Catálogos.
Gestión de Plagas y Cultivos registrados ante el ICA.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.core.supabase_client import get_supabase_client

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class PlagaCreate(BaseModel):
    """Esquema para registrar una plaga."""
    nombre_comun: str
    nombre_cientifico: Optional[str] = None
    tipo: str  # 'insecto', 'hongo', 'bacteria', 'virus', 'nematodo', 'maleza'
    descripcion: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    cultivos_afectados: Optional[List[str]] = []  # Lista de IDs de cultivos (se insertan en plaga_cultivo)


class CultivoCreate(BaseModel):
    """Esquema para registrar un cultivo."""
    nombre: str
    nombre_cientifico: Optional[str] = None
    variedad: Optional[str] = None
    descripcion: Optional[str] = None


# ── Plagas ────────────────────────────────────────────────────────────────────

@router.get("/plagas", summary="Listar plagas")
def listar_plagas():
    """Retorna todas las plagas del catálogo con sus cultivos asociados."""
    supabase = get_supabase_client()
    response = supabase.table("plagas").select("*").execute()

    # Cargar TODAS las relaciones plaga-cultivo en UNA sola query (elimina N+1)
    relaciones_map: dict[str, list[str]] = {}
    try:
        rel = supabase.table("plaga_cultivo").select("plaga_id, cultivo_id").execute()
        for r in rel.data:
            relaciones_map.setdefault(r["plaga_id"], []).append(r["cultivo_id"])
    except Exception:
        pass  # tabla plaga_cultivo aún no existe

    for plaga in response.data:
        plaga["cultivos_afectados"] = relaciones_map.get(plaga["id"], [])

    return response.data


@router.post("/plagas", status_code=201, summary="Crear una plaga")
def crear_plaga(plaga: PlagaCreate):
    """
    Registra una nueva plaga en el catálogo.
    Si se proporcionan cultivos_afectados, se insertan en la tabla plaga_cultivo.
    """
    supabase = get_supabase_client()
    # Separar cultivos_afectados del payload principal (no es columna de la tabla plagas)
    cultivos_ids = plaga.cultivos_afectados or []
    plaga_data = plaga.model_dump(exclude={"cultivos_afectados"})
    response = supabase.table("plagas").insert(plaga_data).execute()
    nueva_plaga = response.data[0]

    # Insertar relaciones many-to-many en plaga_cultivo
    if cultivos_ids:
        try:
            relaciones = [{"plaga_id": nueva_plaga["id"], "cultivo_id": cid} for cid in cultivos_ids]
            supabase.table("plaga_cultivo").insert(relaciones).execute()
            nueva_plaga["cultivos_afectados"] = cultivos_ids
        except Exception:
            pass  # tabla plaga_cultivo aún no existe

    return nueva_plaga


@router.get("/plagas/por-cultivo/{cultivo_id}", summary="Plagas asociadas a un cultivo")
def listar_plagas_por_cultivo(cultivo_id: str):
    """
    Retorna todas las plagas que afectan a un cultivo específico.
    Equivale a getPlagasByPrediosCultivos(cultivoId) del frontend.
    Usa la tabla de relación 'plaga_cultivo' (many-to-many).
    """
    supabase = get_supabase_client()
    # Obtener IDs de plagas que afectan el cultivo
    rel = (
        supabase.table("plaga_cultivo")
        .select("plaga_id")
        .eq("cultivo_id", cultivo_id)
        .execute()
    )
    plaga_ids = [r["plaga_id"] for r in rel.data]
    if not plaga_ids:
        return []
    # Obtener el detalle de cada plaga
    response = (
        supabase.table("plagas")
        .select("*")
        .in_("id", plaga_ids)
        .execute()
    )
    return response.data


@router.get("/plagas/{plaga_id}", summary="Obtener plaga por ID")
def obtener_plaga(plaga_id: str):
    """Retorna una plaga específica por su ID con sus cultivos asociados."""
    supabase = get_supabase_client()
    response = supabase.table("plagas").select("*").eq("id", plaga_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Plaga no encontrada")
    plaga = response.data[0]
    try:
        rel = supabase.table("plaga_cultivo").select("cultivo_id").eq("plaga_id", plaga_id).execute()
        plaga["cultivos_afectados"] = [r["cultivo_id"] for r in rel.data]
    except Exception:
        plaga["cultivos_afectados"] = []
    return plaga


@router.put("/plagas/{plaga_id}", summary="Actualizar plaga")
def actualizar_plaga(plaga_id: str, plaga: PlagaCreate):
    """
    Actualiza una plaga existente.
    Si se proporcionan cultivos_afectados, se reemplazan las relaciones en plaga_cultivo.
    """
    supabase = get_supabase_client()
    cultivos_ids = plaga.cultivos_afectados or []
    plaga_data = plaga.model_dump(exclude={"cultivos_afectados"})
    response = supabase.table("plagas").update(plaga_data).eq("id", plaga_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Plaga no encontrada")
    plaga_actualizada = response.data[0]

    # Reemplazar relaciones: borrar las existentes e insertar las nuevas
    try:
        supabase.table("plaga_cultivo").delete().eq("plaga_id", plaga_id).execute()
        if cultivos_ids:
            relaciones = [{"plaga_id": plaga_id, "cultivo_id": cid} for cid in cultivos_ids]
            supabase.table("plaga_cultivo").insert(relaciones).execute()
        plaga_actualizada["cultivos_afectados"] = cultivos_ids
    except Exception:
        pass  # tabla plaga_cultivo aún no existe

    return plaga_actualizada


@router.delete("/plagas/{plaga_id}", status_code=204, summary="Eliminar plaga")
def eliminar_plaga(plaga_id: str):
    """Elimina una plaga del catálogo."""
    supabase = get_supabase_client()
    supabase.table("plagas").delete().eq("id", plaga_id).execute()
    return None


# ── Cultivos ──────────────────────────────────────────────────────────────────

@router.get("/cultivos", summary="Listar cultivos")
def listar_cultivos():
    """Retorna todos los cultivos del catálogo."""
    supabase = get_supabase_client()
    response = supabase.table("cultivos").select("*").execute()
    return response.data


@router.post("/cultivos", status_code=201, summary="Crear un cultivo")
def crear_cultivo(cultivo: CultivoCreate):
    """Registra un nuevo cultivo en el catálogo."""
    supabase = get_supabase_client()
    response = supabase.table("cultivos").insert(cultivo.model_dump()).execute()
    return response.data[0]


@router.get("/cultivos/{cultivo_id}", summary="Obtener cultivo por ID")
def obtener_cultivo(cultivo_id: str):
    """Retorna un cultivo específico por su ID."""
    supabase = get_supabase_client()
    response = supabase.table("cultivos").select("*").eq("id", cultivo_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Cultivo no encontrado")
    return response.data[0]


@router.put("/cultivos/{cultivo_id}", summary="Actualizar cultivo")
def actualizar_cultivo(cultivo_id: str, cultivo: CultivoCreate):
    """Actualiza un cultivo existente."""
    supabase = get_supabase_client()
    response = supabase.table("cultivos").update(cultivo.model_dump()).eq("id", cultivo_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Cultivo no encontrado")
    return response.data[0]


@router.delete("/cultivos/{cultivo_id}", status_code=204, summary="Eliminar cultivo")
def eliminar_cultivo(cultivo_id: str):
    """Elimina un cultivo del catálogo."""
    supabase = get_supabase_client()
    supabase.table("cultivos").delete().eq("id", cultivo_id).execute()
    return None


