"""
Router de Predios.
Gestión de predios agrícolas vinculados a productores.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from app.core.supabase_client import get_supabase_client
from app.core.security import get_current_user, require_role

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class PredioCreate(BaseModel):
    """Esquema para registrar un predio."""
    nombre: str
    productor_id: str
    lugar_id: Optional[str] = None
    departamento: str
    municipio: str
    vereda: Optional[str] = None
    numero_registro_ica: Optional[str] = None  # Número de registro ante el ICA
    latitud: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitud: Optional[float] = Field(None, ge=-180.0, le=180.0)
    area_total: Optional[float] = Field(None, gt=0.0)


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
def obtener_predios_batch(request: PredioBatchRequest,
                          current_user: dict = Depends(get_current_user)):
    """Retorna múltiples predios en una sola petición. Elimina el problema N+1 del frontend."""
    if not request.ids:
        return []
    supabase = get_supabase_client()
    response = supabase.table("predios").select("*").in_("id", request.ids).execute()
    return response.data

@router.get("/", summary="Listar predios")
def listar_predios(skip: int = 0, limit: int = 100,
                   current_user: dict = Depends(get_current_user)):
    """Retorna predios. El productor solo ve los suyos; admin ve todos."""
    supabase = get_supabase_client()
    if current_user.get("rol") == "productor":
        response = supabase.table("predios").select("*") \
            .eq("productor_id", current_user["id"]).execute()
    else:
        response = supabase.table("predios").select("*").range(skip, skip + limit - 1).execute()
    return response.data


@router.get("/productor/{productor_id}", summary="Listar predios de un productor")
def listar_predios_por_productor(productor_id: str,
                                 current_user: dict = Depends(get_current_user)):
    """Retorna los predios de un productor. El productor solo puede ver los suyos."""
    supabase = get_supabase_client()
    # Un productor no puede consultar los predios de otro productor
    if current_user.get("rol") == "productor" and current_user["id"] != productor_id:
        raise HTTPException(status_code=403, detail="No puedes ver los predios de otro productor")
    response = supabase.table("predios").select("*").eq("productor_id", productor_id).execute()
    return response.data


@router.get("/{predio_id}", summary="Obtener un predio por ID")
def obtener_predio(predio_id: str,
                   current_user: dict = Depends(get_current_user)):
    """Retorna un predio específico con sus lotes asociados."""
    supabase = get_supabase_client()
    response = supabase.table("predios").select("*, lotes(*)").eq("id", predio_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Predio no encontrado")
    return response.data[0]



@router.post("/", status_code=201, summary="Crear un predio")
def crear_predio(predio: PredioCreate,
                current_user: dict = Depends(require_role(['productor', 'admin']))):
    """Registra un nuevo predio agrícola. Fuerza productor_id desde el token JWT."""
    supabase = get_supabase_client()
    data = predio.model_dump()
    # Ignorar el productor_id del payload: siempre usar el del usuario autenticado
    if current_user.get("rol") == "productor":
        data["productor_id"] = current_user["id"]
    response = supabase.table("predios").insert(data).execute()
    return response.data[0]


@router.put("/{predio_id}", summary="Actualizar un predio")
def actualizar_predio(predio_id: str, predio: PredioUpdate,
                     current_user: dict = Depends(require_role(['productor', 'admin']))):
    """Actualiza un predio. El productor solo puede editar el suyo."""
    supabase = get_supabase_client()
    # Verificar propiedad para productores
    if current_user.get("rol") == "productor":
        existing = supabase.table("predios").select("productor_id").eq("id", predio_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Predio no encontrado")
        if existing.data[0]["productor_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="No puedes modificar un predio que no te pertenece")
    data = {k: v for k, v in predio.model_dump().items() if v is not None}
    response = supabase.table("predios").update(data).eq("id", predio_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Predio no encontrado")
    return response.data[0]


@router.delete("/{predio_id}", status_code=204, summary="Eliminar un predio")
def eliminar_predio(predio_id: str,
                   current_user: dict = Depends(require_role(['productor', 'admin']))):
    """Elimina un predio. El productor solo puede eliminar el suyo."""
    supabase = get_supabase_client()
    if current_user.get("rol") == "productor":
        existing = supabase.table("predios").select("productor_id").eq("id", predio_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Predio no encontrado")
        if existing.data[0]["productor_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="No puedes eliminar un predio que no te pertenece")
    supabase.table("predios").delete().eq("id", predio_id).execute()
    return None
