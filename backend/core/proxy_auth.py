from fastapi import Request, HTTPException, status
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

def is_trusted_access(request: Request) -> bool:
    """
    Overí, či request prichádza cez portál alebo cez Tailscale.

    Povolené:
    - portál proxy s platným X-SEMA-Proxy-Token
    - Tailscale IP rozsah 100.x.x.x
    """

    proxy_user = get_proxy_user(request)

    if proxy_user:
        return True

    client_ip = request.client.host

    if client_ip and client_ip.startswith("100."):
        return True

    return False



def require_trusted_access(request: Request):
    """
    Zakáže lokálny LAN prístup mimo portálu a Tailscale.
    """

    if not is_trusted_access(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local access is disabled.",
        )

    return True