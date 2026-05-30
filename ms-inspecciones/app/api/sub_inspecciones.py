"""
Router de Sub-Inspecciones.
Gestión de puntos de muestreo dentro de una inspección principal.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.supabase_client import get_supabase_client
from app.core.security import get_current_user, require_role

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class SubInspeccionCreate(BaseModel):
    """Esquema para crear una sub-inspección (punto de muestreo)."""
    inspeccion_id: str
    codigo_punto: str  # Identificador del punto de muestreo
    ubicacion_referencia: Optional[str] = None
    observaciones: Optional[str] = None
    plantas_evaluadas: Optional[int] = 0


class SubInspeccionUpdate(BaseModel):
    """Esquema para actualizar una sub-inspección."""
    ubicacion_referencia: Optional[str] = None
    observaciones: Optional[str] = None
    estado: Optional[str] = None  # 'pendiente', 'completado'
    plantas_evaluadas: Optional[int] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/inspeccion/{inspeccion_id}", summary="Listar sub-inspecciones de una inspección")
def listar_sub_inspecciones(inspeccion_id: str,
                            current_user: dict = Depends(get_current_user)):
    """Retorna todas las sub-inspecciones de una inspección principal."""
    supabase = get_supabase_client()
    response = (
        supabase.table("sub_inspecciones")
        .select("*, registro_plantas(*)")
        .eq("inspeccion_id", inspeccion_id)
        .execute()
    )
    return response.data


@router.get("/{sub_inspeccion_id}", summary="Obtener una sub-inspección por ID")
def obtener_sub_inspeccion(sub_inspeccion_id: str,
                           current_user: dict = Depends(get_current_user)):
    """Retorna una sub-inspección específica con sus registros de plantas."""
    supabase = get_supabase_client()
    response = (
        supabase.table("sub_inspecciones")
        .select("*, registro_plantas(*)")
        .eq("id", sub_inspeccion_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Sub-inspección no encontrada")
    return response.data[0]


@router.post("/", status_code=201, summary="Crear una sub-inspección")
def crear_sub_inspeccion(sub_inspeccion: SubInspeccionCreate,
                         current_user: dict = Depends(require_role(['tecnico', 'admin']))):
    """Crea un nuevo punto de muestreo dentro de una inspección."""
    supabase = get_supabase_client()
    data = sub_inspeccion.model_dump()
    data["estado"] = "pendiente"
    response = supabase.table("sub_inspecciones").insert(data).execute()
    return response.data[0]


@router.put("/{sub_inspeccion_id}", summary="Actualizar una sub-inspección")
def actualizar_sub_inspeccion(sub_inspeccion_id: str, sub_inspeccion: SubInspeccionUpdate,
                              current_user: dict = Depends(require_role(['tecnico', 'admin']))):
    """Actualiza los datos de una sub-inspección existente."""
    supabase = get_supabase_client()
    data = {k: v for k, v in sub_inspeccion.model_dump().items() if v is not None}
    response = (
        supabase.table("sub_inspecciones")
        .update(data)
        .eq("id", sub_inspeccion_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Sub-inspección no encontrada")
    return response.data[0]


@router.delete("/{sub_inspeccion_id}", status_code=204, summary="Eliminar una sub-inspección")
def eliminar_sub_inspeccion(sub_inspeccion_id: str,
                            current_user: dict = Depends(require_role(['admin']))):
    """Elimina una sub-inspección y sus registros de plantas asociados."""
    supabase = get_supabase_client()
    supabase.table("sub_inspecciones").delete().eq("id", sub_inspeccion_id).execute()
    return None
