import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv('/home/darwing/FitoGestionBE/.env')

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(supabase_url, supabase_key)

try:
    res = supabase.auth.get_user("fake_token")
    print("RES:", res)
except Exception as e:
    print("EXCEPTION:", repr(e))

