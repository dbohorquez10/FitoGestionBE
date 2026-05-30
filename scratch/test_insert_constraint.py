import os
import sys
from datetime import date
sys.path.append("/home/darwing/FitoGestionBE/ms-core-agricola")
from app.core.supabase_client import get_supabase_client

supabase = get_supabase_client()

# Try to insert a mock pending inspection with null tecnico_id
test_data = {
    "predio_id": "b0af1bea-909d-4472-9544-2c54095a75fb", # Finca Lau
    "lote_id": "134ca2ea-28ad-42f0-a135-39cd6478d7a5",
    "fecha_inspeccion": str(date.today()),
    "tipo_inspeccion": "rutinaria",
    "estado": "pendiente",
    "modo_asignacion": "automatica"
}

try:
    res = supabase.table("inspecciones").insert(test_data).execute()
    print("Insert success! Inserted row:", res.data)
    # Clean up
    inserted_id = res.data[0]["id"]
    supabase.table("inspecciones").delete().eq("id", inserted_id).execute()
except Exception as e:
    print("Insert failed with error:", e)
