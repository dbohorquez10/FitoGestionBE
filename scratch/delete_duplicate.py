import os
import sys
sys.path.append("/home/darwing/FitoGestionBE/ms-core-agricola")
from app.core.supabase_client import get_supabase_client

supabase = get_supabase_client()

lote_duplicado_id = "7e7395d5-d14a-485c-b0ad-45a37af97ae6"

try:
    res = supabase.table("lotes").delete().eq("id", lote_duplicado_id).execute()
    print("Delete result:", res.data)
except Exception as e:
    print("Error deleting duplicate lote:", e)
