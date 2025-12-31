import os
from typing import Optional
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


class SupabaseConfigError(Exception):
    pass


_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise SupabaseConfigError(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not set in the environment"
        )
    _supabase_client = create_client(url, key)
    return _supabase_client
