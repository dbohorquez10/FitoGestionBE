import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv('/home/darwing/FitoGestionBE/.env')

supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

try:
    res = supabase.auth.admin.create_user({"email": "test@test.com", "password": "password123", "email_confirm": True})
    print("RES with email_confirm:", res)
except Exception as e:
    print("EXCEPTION email_confirm:", repr(e))

try:
    res = supabase.auth.admin.create_user({"email": "test2@test.com", "password": "password123"})
    print("RES without email_confirm:", res)
except Exception as e:
    print("EXCEPTION without email_confirm:", repr(e))

try:
    res = supabase.auth.sign_up({"email": "test3@test.com", "password": "password123"})
    print("RES signup:", res)
except Exception as e:
    print("EXCEPTION signup:", repr(e))
