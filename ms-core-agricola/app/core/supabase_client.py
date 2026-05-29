"""
Módulo de conexión a Supabase.
Proporciona un cliente reutilizable para todos los routers.
"""
from supabase import create_client, Client
from app.core.config import get_settings

def get_supabase_client() -> Client:
    """Retorna una nueva instancia del cliente de Supabase para evitar contaminación de estado de autenticación."""
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def get_supabase_admin_client() -> Client:
    """
    Retorna un cliente de Supabase con la Service Role Key.
    Necesario para operaciones admin como auth.admin.create_user().
    Si no se configura SUPABASE_SERVICE_ROLE_KEY, usa SUPABASE_KEY como fallback.
    """
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
    return create_client(settings.SUPABASE_URL, key)
