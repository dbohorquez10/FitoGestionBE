"""
Router de Lotes.
Gestión de lotes dentro de un predio agrícola.
Incluye filtrado por productor para garantizar aislamiento de datos.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from app.core.supabase_client import get_supabase_client
from app.core.security import get_current_user, require_role

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class LoteCreate(BaseModel):
    """Esquema para registrar un lote."""
    predio_id: str
    nombre: str
    cultivo_id: Optional[str] = None
    area: Optional[float] = Field(None, gt=0.0)  # Hectáreas
    num_plantas: Optional[int] = Field(None, gt=0)  # Total absoluto de plantas
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
def listar_lotes(predio_id: Optional[str] = None,
                 current_user: dict = Depends(get_current_user)):
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
def obtener_lote(lote_id: str,
                 current_user: dict = Depends(get_current_user)):
    """Retorna un lote específico por su ID."""
    supabase = get_supabase_client()
    response = supabase.table("lotes").select("*, cultivos(nombre), predios(nombre)").eq("id", lote_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return response.data[0]


@router.get("/predio/{predio_id}", summary="Listar lotes de un predio")
def listar_lotes_por_predio(predio_id: str,
                            current_user: dict = Depends(get_current_user)):
    """Retorna todos los lotes de un predio específico."""
    supabase = get_supabase_client()
    response = supabase.table("lotes").select("*, cultivos(nombre)").eq("predio_id", predio_id).execute()
    return response.data


@router.get("/productor/{productor_id}", summary="Listar lotes de un productor")
def listar_lotes_por_productor(productor_id: str,
                               current_user: dict = Depends(get_current_user)):
    """
    Retorna todos los lotes de todos los predios de un productor.
    El productor autenticado solo puede ver los suyos.
    """
    supabase = get_supabase_client()
    # Un productor no puede ver los lotes de otro productor
    if current_user.get("rol") == "productor" and current_user["id"] != productor_id:
        raise HTTPException(status_code=403, detail="No puedes ver los lotes de otro productor")
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
def crear_lote(lote: LoteCreate,
               current_user: dict = Depends(require_role(['productor', 'admin']))):
    """Registra un nuevo lote dentro de un predio."""
    supabase = get_supabase_client()
    # Verificar que el predio exista
    predio = supabase.table("predios").select("id").eq("id", lote.predio_id).execute()
    if not predio.data:
        raise HTTPException(status_code=404, detail="Predio no encontrado")
        
    # Verificar nombre duplicado en el mismo predio y que no esté vacío
    nombre_normalizado = lote.nombre.strip()
    if not nombre_normalizado:
        raise HTTPException(
            status_code=400,
            detail="El nombre del lote no puede estar vacío o contener solo espacios."
        )
    lote_existente = (
        supabase.table("lotes")
        .select("id")
        .eq("predio_id", lote.predio_id)
        .ilike("nombre", nombre_normalizado)
        .execute()
    )
    if lote_existente.data:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un lote con el nombre '{nombre_normalizado}' en este lugar de producción."
        )
        
    response = supabase.table("lotes").insert(lote.model_dump()).execute()
    return response.data[0]


@router.put("/{lote_id}", summary="Actualizar un lote")
def actualizar_lote(lote_id: str, lote: LoteUpdate,
                   current_user: dict = Depends(require_role(['productor', 'admin']))):
    """Actualiza los datos de un lote existente."""
    supabase = get_supabase_client()
    
    # 1. Obtener el lote para conocer su predio_id
    lote_actual_res = supabase.table("lotes").select("predio_id").eq("id", lote_id).execute()
    if not lote_actual_res.data:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    predio_id = lote_actual_res.data[0]["predio_id"]
    
    # 2. Verificar que no exista otro lote en el mismo predio con el mismo nombre (si se cambia el nombre)
    if lote.nombre is not None:
        nombre_normalizado = lote.nombre.strip()
        if not nombre_normalizado:
            raise HTTPException(
                status_code=400,
                detail="El nombre del lote no puede estar vacío o contener solo espacios."
            )
        lote_existente = (
            supabase.table("lotes")
            .select("id")
            .eq("predio_id", predio_id)
            .ilike("nombre", nombre_normalizado)
            .neq("id", lote_id)
            .execute()
        )
        if lote_existente.data:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe un lote con el nombre '{nombre_normalizado}' en este lugar de producción."
            )
            
    data = {k: v for k, v in lote.model_dump().items() if v is not None}
    response = supabase.table("lotes").update(data).eq("id", lote_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return response.data[0]


@router.delete("/{lote_id}", status_code=204, summary="Eliminar un lote")
def eliminar_lote(lote_id: str,
                 current_user: dict = Depends(require_role(['admin']))):
    """Elimina un lote del sistema."""
    supabase = get_supabase_client()
    supabase.table("lotes").delete().eq("id", lote_id).execute()
    return None
