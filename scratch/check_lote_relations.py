import os
import sys
sys.path.append("/home/darwing/FitoGestionBE/ms-core-agricola")
from app.core.supabase_client import get_supabase_client

supabase = get_supabase_client()

lote1 = "134ca2ea-28ad-42f0-a135-39cd6478d7a5" # Lote C Crítico
lote2 = "7e7395d5-d14a-485c-b0ad-45a37af97ae6" # Lote C Óptimo

res1 = supabase.table("inspecciones").select("id, fecha_inspeccion, estado").eq("lote_id", lote1).execute()
res2 = supabase.table("inspecciones").select("id, fecha_inspeccion, estado").eq("lote_id", lote2).execute()

print(f"Inspecciones for Lote 1 (Crítico - {lote1}):")
for row in res1.data:
    print(row)

print(f"\nInspecciones for Lote 2 (Óptimo - {lote2}):")
for row in res2.data:
    print(row)
