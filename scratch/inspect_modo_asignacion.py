import os
import sys
sys.path.append("/home/darwing/FitoGestionBE/ms-core-agricola")
from app.core.supabase_client import get_supabase_client

supabase = get_supabase_client()
res = supabase.table("inspecciones").select("id, modo_asignacion, tecnico_id").execute()
print("All inspections with modo_asignacion:")
for row in res.data:
    print(row)
