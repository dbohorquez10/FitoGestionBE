"""
Router de Usuarios.
CRUD completo para la gestión de usuarios del sistema FitoGestión.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.core.supabase_client import get_supabase_client

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class UsuarioCreate(BaseModel):
    """Esquema para la creación de un usuario."""
    nombre: str
    apellido: str
    email: EmailStr
    cedula: str
    rol: str  # 'admin', 'tecnico', 'productor'
    telefono: Optional[str] = None
    registro_ica: Optional[str] = None  # Solo para técnicos
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    vereda: Optional[str] = None


class UsuarioUpdate(BaseModel):
    """Esquema para la actualización parcial de un usuario."""
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    rol: Optional[str] = None
    registro_ica: Optional[str] = None
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    vereda: Optional[str] = None


class UsuarioResponse(BaseModel):
    """Esquema de respuesta de un usuario."""
    id: str
    nombre: str
    apellido: str
    email: str
    cedula: str
    rol: str
    telefono: Optional[str] = None
    registro_ica: Optional[str] = None
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    vereda: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", summary="Listar todos los usuarios")
def listar_usuarios():
    """Retorna la lista completa de usuarios registrados."""
    supabase = get_supabase_client()
    response = supabase.table("usuarios").select("*").execute()
    return response.data


# ── Rutas estáticas ANTES de las dinámicas (evitar conflicto con /{usuario_id}) ──

@router.get("/tecnicos/activos", summary="Listar técnicos activos")
def listar_tecnicos_activos():
    """
    Retorna todos los usuarios con rol 'tecnico' y estado 'Activo'.
    Usado por el frontend en la solicitud de inspección (asignación de técnico).
    NOTA: Esta ruta debe estar ANTES de /{usuario_id} para evitar conflictos.
    """
    supabase = get_supabase_client()
    response = (
        supabase.table("usuarios")
        .select("*")
        .eq("rol", "tecnico")
        .eq("activo", True)
        .execute()
    )
    return response.data


@router.get("/{usuario_id}", summary="Obtener un usuario por ID")
def obtener_usuario(usuario_id: str):
    """Retorna un usuario específico por su ID."""
    supabase = get_supabase_client()
    response = supabase.table("usuarios").select("*").eq("id", usuario_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return response.data[0]


@router.post("/", status_code=201, summary="Crear un nuevo usuario")
def crear_usuario(usuario: UsuarioCreate):
    """Crea un nuevo usuario en el sistema."""
    supabase = get_supabase_client()
    response = supabase.table("usuarios").insert(usuario.model_dump()).execute()
    return response.data[0]


@router.put("/{usuario_id}", summary="Actualizar un usuario")
def actualizar_usuario(usuario_id: str, usuario: UsuarioUpdate):
    """Actualiza los datos de un usuario existente."""
    supabase = get_supabase_client()
    data = {k: v for k, v in usuario.model_dump().items() if v is not None}
    response = supabase.table("usuarios").update(data).eq("id", usuario_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return response.data[0]


@router.delete("/{usuario_id}", status_code=204, summary="Eliminar un usuario")
def eliminar_usuario(usuario_id: str):
    """Elimina un usuario del sistema por su ID."""
    supabase = get_supabase_client()
    supabase.table("usuarios").delete().eq("id", usuario_id).execute()
    return None



@router.patch("/{usuario_id}/toggle-estado", summary="Suspender o activar un usuario")
def toggle_estado_usuario(usuario_id: str):
    """
    Alterna el estado de un usuario entre activo e inactivo.
    Equivale a suspender o rehabilitar una cuenta (acción de Admin).
    """
    supabase = get_supabase_client()
    # Obtener estado actual
    response = supabase.table("usuarios").select("activo").eq("id", usuario_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    activo_actual = response.data[0]["activo"]
    nuevo_estado = not activo_actual
    updated = (
        supabase.table("usuarios")
        .update({"activo": nuevo_estado})
        .eq("id", usuario_id)
        .execute()
    )
    return {"id": usuario_id, "activo": nuevo_estado}
