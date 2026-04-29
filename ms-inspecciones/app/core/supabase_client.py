"""
Módulo de conexión a Supabase.
Proporciona un cliente reutilizable para todos los routers.
"""
from supabase import create_client, Client
from app.core.config import get_settings

_supabase_client = None

def get_supabase_client() -> Client:
    """Retorna el cliente de Supabase instanciado como un Singleton."""
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client
