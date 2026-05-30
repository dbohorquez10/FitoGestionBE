import os
import sys
sys.path.append("/home/darwing/FitoGestionBE/ms-core-agricola")
from app.core.supabase_client import get_supabase_client

supabase = get_supabase_client()
try:
    res = supabase.table("inspecciones").select("*").limit(1).execute()
    if res.data:
        print("Columns in inspecciones:", list(res.data[0].keys()))
        print("First row data:", res.data[0])
    else:
        print("No data in table, but we can query metadata or try inserting/testing.")
except Exception as e:
    print("Error querying database:", e)
