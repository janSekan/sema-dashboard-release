from fastapi import Request
from data.config.config import PROXY_TOKEN


def get_proxy_user(request: Request):
    """
    Overí trusted proxy hlavičky z portálu.

    Ak token sedí, vráti používateľa z portálu.
    Ak nie, vráti None.
    """

    token = request.headers.get("X-SEMA-Proxy-Token")
    user = request.headers.get("X-SEMA-Proxy-User")
    role = request.headers.get("X-SEMA-Proxy-Role")

    if not PROXY_TOKEN:
        return None

    if not token or token != PROXY_TOKEN:
        return None

    if not user:
        return None

    return {
        "username": user,
        "role": role or "user",
        "source": "portal",
    }