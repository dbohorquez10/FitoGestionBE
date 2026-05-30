import os
import sys
sys.path.append("/home/darwing/FitoGestionBE/ms-core-agricola")
from app.core.supabase_client import get_supabase_client

supabase = get_supabase_client()
res = supabase.table("lotes").select("id, predio_id, nombre, created_at").execute()
print("All lotes with created_at:")
for row in res.data:
    print(row)
