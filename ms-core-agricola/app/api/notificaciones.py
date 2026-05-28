from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.supabase_client import get_supabase_client
from app.core.security import get_current_user

router = APIRouter()

class NotificacionCreate(BaseModel):
    usuario_id: str
    titulo: str
    mensaje: str
    tipo: Optional[str] = "info"

@router.get("/usuario/{usuario_id}", summary="Obtener notificaciones del usuario")
def listar_notificaciones(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Retorna las últimas notificaciones de un usuario ordenadas por fecha."""
    supabase = get_supabase_client()
    try:
        response = (
            supabase.table("notificaciones")
            .select("*")
            .eq("usuario_id", usuario_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        return response.data
    except Exception as e:
        # Si la tabla no existe o hay error, fallar graciosamente devolviendo lista vacía
        return []

@router.put("/{notificacion_id}/leer", summary="Marcar notificación como leída")
def marcar_como_leida(notificacion_id: str, current_user: dict = Depends(get_current_user)):
    """Marca una notificación como leída."""
    supabase = get_supabase_client()
    try:
        response = (
            supabase.table("notificaciones")
            .update({"leido": True})
            .eq("id", notificacion_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Notificación no encontrada")
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Error interno al actualizar la notificación")

@router.post("/", status_code=201, summary="Crear una notificación")
def crear_notificacion(notificacion: NotificacionCreate, current_user: dict = Depends(get_current_user)):
    """Crea una nueva notificación (uso interno/sistema)."""
    supabase = get_supabase_client()
    try:
        response = supabase.table("notificaciones").insert(notificacion.model_dump()).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al crear la notificación")
