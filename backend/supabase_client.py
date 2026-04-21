import os

from dotenv import load_dotenv
from supabase import create_client


load_dotenv("bdd.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE") or os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_ERROR = ""


class _UnavailableTableQuery:
    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def maybe_single(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def delete(self, *args, **kwargs):
        return self

    def execute(self):
        raise RuntimeError(SUPABASE_ERROR or "Supabase indisponible")


class _UnavailableAdminApi:
    def delete_user(self, *args, **kwargs):
        raise RuntimeError(SUPABASE_ERROR or "Supabase indisponible")


class _UnavailableAuth:
    admin = _UnavailableAdminApi()
    api = _UnavailableAdminApi()

    def sign_up(self, *args, **kwargs):
        raise RuntimeError(SUPABASE_ERROR or "Supabase indisponible")

    def sign_in_with_password(self, *args, **kwargs):
        raise RuntimeError(SUPABASE_ERROR or "Supabase indisponible")

    def reset_password_for_email(self, *args, **kwargs):
        raise RuntimeError(SUPABASE_ERROR or "Supabase indisponible")

    def get_user(self, *args, **kwargs):
        raise RuntimeError(SUPABASE_ERROR or "Supabase indisponible")


class _UnavailableClient:
    auth = _UnavailableAuth()

    def table(self, *args, **kwargs):
        return _UnavailableTableQuery()


def _build_client(key_value: str | None, label: str):
    global SUPABASE_ERROR

    if not SUPABASE_URL or not key_value:
        SUPABASE_ERROR = (
            "Variables Supabase manquantes. Renseignez SUPABASE_URL et "
            f"{label} avant de deployer l'authentification."
        )
        print(f"Supabase: unavailable ({SUPABASE_ERROR})")
        return _UnavailableClient()

    try:
        client = create_client(SUPABASE_URL, key_value)
        print(f"Supabase: connected ({label})")
        return client
    except Exception as exc:
        SUPABASE_ERROR = f"Erreur initialisation Supabase ({label}): {exc}"
        print(f"Supabase: unavailable ({SUPABASE_ERROR})")
        return _UnavailableClient()


supabase = _build_client(SUPABASE_KEY, "SUPABASE_KEY")
supabase_admin = _build_client(SUPABASE_SERVICE_ROLE, "SUPABASE_SERVICE_ROLE") if SUPABASE_SERVICE_ROLE else supabase


def signup_user(email, password):
    return supabase.auth.sign_up({"email": email, "password": password})


def login_user(email, password):
    return supabase.auth.sign_in_with_password({"email": email, "password": password})


def reset_password_email(email, redirect_to=None):
    options = {"redirect_to": redirect_to} if redirect_to else None
    return supabase.auth.reset_password_for_email(email, options)


def delete_user_admin(user_id: str) -> tuple[bool, str | None]:
    """Try to delete a Supabase auth user using the admin client."""
    try:
        client = supabase_admin
        admin_api = getattr(client.auth, "admin", None) or getattr(client.auth, "api", None)
        if admin_api and hasattr(admin_api, "delete_user"):
            try:
                admin_api.delete_user(user_id)
            except TypeError:
                admin_api.delete_user(user_id, False)
            return True, None
        return False, "Admin API unavailable (missing service role key)"
    except Exception as exc:
        return False, str(exc)
