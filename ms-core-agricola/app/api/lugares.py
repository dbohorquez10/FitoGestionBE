"""
Router de Lugares de Producción.
Gestión de lugares de producción agrícola vinculados a productores.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.supabase_client import get_supabase_client
from app.core.security import get_current_user, require_role

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
def obtener_lugares_batch(request: LugarBatchRequest,
                          current_user: dict = Depends(get_current_user)):
    """Retorna múltiples lugares en una sola petición."""
    if not request.ids:
        return []
    supabase = get_supabase_client()
    response = supabase.table("lugares_produccion").select("*").in_("id", request.ids).execute()
    return response.data

@router.get("/", summary="Listar lugares de producción")
def listar_lugares(skip: int = 0, limit: int = 100,
                   current_user: dict = Depends(get_current_user)):
    """Retorna lugares. El productor solo ve los suyos; admin ve todos."""
    supabase = get_supabase_client()
    if current_user.get("rol") == "productor":
        response = supabase.table("lugares_produccion").select("*") \
            .eq("productor_id", current_user["id"]).execute()
    else:
        response = supabase.table("lugares_produccion").select("*") \
            .range(skip, skip + limit - 1).execute()
    return response.data


@router.get("/productor/{productor_id}", summary="Listar lugares de un productor")
def listar_lugares_por_productor(productor_id: str,
                                 current_user: dict = Depends(get_current_user)):
    """Retorna los lugares de un productor con sus predios y lotes. El productor solo ve los suyos."""
    supabase = get_supabase_client()
    if current_user.get("rol") == "productor" and current_user["id"] != productor_id:
        raise HTTPException(status_code=403, detail="No puedes ver los lugares de otro productor")
    response = supabase.table("lugares_produccion").select("*, predios(*, lotes(*))").eq("productor_id", productor_id).execute()
    return response.data


@router.get("/{lugar_id}", summary="Obtener un lugar por ID")
def obtener_lugar(lugar_id: str,
                  current_user: dict = Depends(get_current_user)):
    """Retorna un lugar específico con sus predios anidados."""
    supabase = get_supabase_client()
    response = supabase.table("lugares_produccion").select("*, predios(*, lotes(*))").eq("id", lugar_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Lugar de producción no encontrado")
    return response.data[0]


@router.post("/", status_code=201, summary="Crear un lugar de producción")
def crear_lugar(lugar: LugarCreate,
               current_user: dict = Depends(require_role(['productor', 'admin']))):
    """Registra un nuevo lugar. Fuerza productor_id desde el token JWT."""
    supabase = get_supabase_client()
    data = lugar.model_dump()
    # Ignorar el productor_id del payload: siempre usar el del usuario autenticado
    if current_user.get("rol") == "productor":
        data["productor_id"] = current_user["id"]
    response = supabase.table("lugares_produccion").insert(data).execute()
    return response.data[0]


@router.put("/{lugar_id}", summary="Actualizar un lugar")
def actualizar_lugar(lugar_id: str, lugar: LugarUpdate,
                    current_user: dict = Depends(require_role(['productor', 'admin']))):
    """Actualiza un lugar. El productor solo puede editar el suyo."""
    supabase = get_supabase_client()
    if current_user.get("rol") == "productor":
        existing = supabase.table("lugares_produccion").select("productor_id").eq("id", lugar_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Lugar no encontrado")
        if existing.data[0]["productor_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="No puedes modificar un lugar que no te pertenece")
    data = {k: v for k, v in lugar.model_dump().items() if v is not None}
    response = supabase.table("lugares_produccion").update(data).eq("id", lugar_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Lugar no encontrado")
    return response.data[0]


@router.delete("/{lugar_id}", status_code=204, summary="Eliminar un lugar")
def eliminar_lugar(lugar_id: str,
                  current_user: dict = Depends(require_role(['productor', 'admin']))):
    """Elimina un lugar. El productor solo puede eliminar el suyo."""
    supabase = get_supabase_client()
    if current_user.get("rol") == "productor":
        existing = supabase.table("lugares_produccion").select("productor_id").eq("id", lugar_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Lugar no encontrado")
        if existing.data[0]["productor_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="No puedes eliminar un lugar que no te pertenece")
    supabase.table("lugares_produccion").delete().eq("id", lugar_id).execute()
    return None
