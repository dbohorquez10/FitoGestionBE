"""
Router de Autenticación.
Login con email/contraseña usando Supabase Auth, retorna JWT.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.core.supabase_client import get_supabase_client

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Credenciales para iniciar sesión."""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Datos para registrar un nuevo usuario."""
    email: EmailStr
    password: str
    nombre: str
    apellido: str
    cedula: str
    rol: str = "productor"  # 'productor', 'tecnico'
    telefono: str | None = None
    registro_ica: str | None = None


class TokenResponse(BaseModel):
    """Respuesta con el token de sesión."""
    access_token: str
    token_type: str = "bearer"
    user: dict


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión")
async def login(credentials: LoginRequest):
    """
    Autentica al usuario con email y contraseña.
    Retorna el access_token JWT de Supabase.
    """
    supabase = get_supabase_client()
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": credentials.email, "password": credentials.password}
        )
        session = response.session
        user = response.user
        if not session:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        # Obtener perfil adicional del usuario desde la tabla usuarios
        perfil = supabase.table("usuarios").select("*").eq("email", credentials.email).execute()
        perfil_data = perfil.data[0] if perfil.data else {}

        return TokenResponse(
            access_token=session.access_token,
            user={
                "id": user.id,
                "email": user.email,
                **perfil_data,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Error de autenticación: {str(e)}")


@router.post("/register", status_code=201, summary="Registrar usuario")
async def register(data: RegisterRequest):
    """
    Registra un nuevo usuario en Supabase Auth y crea su perfil
    en la tabla 'usuarios'.
    """
    supabase = get_supabase_client()
    try:
        # 1. Crear en Supabase Auth
        auth_response = supabase.auth.admin.create_user(
            {
                "email": data.email,
                "password": data.password,
                "email_confirm": True,
            }
        )
        user_id = auth_response.user.id

        # 2. Insertar perfil en tabla usuarios
        perfil = {
            "id": user_id,
            "nombre": data.nombre,
            "apellido": data.apellido,
            "email": data.email,
            "cedula": data.cedula,
            "rol": data.rol,
            "telefono": data.telefono,
            "registro_ica": data.registro_ica,
        }
        supabase.table("usuarios").insert(perfil).execute()

        return {"message": "Usuario registrado exitosamente", "id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al registrar usuario: {str(e)}")


@router.post("/logout", status_code=204, summary="Cerrar sesión")
async def logout():
    """
    Invalida la sesión actual del usuario.
    El cliente debe eliminar el token localmente.
    """
    supabase = get_supabase_client()
    supabase.auth.sign_out()
    return None


@router.get("/me", summary="Obtener perfil del usuario autenticado")
async def me(authorization: str = ""):
    """
    Retorna el perfil del usuario actual a partir del token JWT.
    El token debe enviarse en el header Authorization: Bearer <token>
    """
    supabase = get_supabase_client()
    try:
        user = supabase.auth.get_user(authorization.replace("Bearer ", ""))
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")
        perfil = supabase.table("usuarios").select("*").eq("email", user.user.email).execute()
        return perfil.data[0] if perfil.data else {"email": user.user.email}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"No autorizado: {str(e)}")
