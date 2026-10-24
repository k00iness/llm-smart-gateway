import secrets

from fastapi import Header, HTTPException, status

from app.core.config import settings


def _parse_clients() -> dict[str, str]:
    """'cle1:alice,cle2:bob' -> {'cle1': 'alice', 'cle2': 'bob'}"""
    clients = {}
    for i, entry in enumerate(settings.CLIENT_API_KEYS.split(","), start=1):
        entry = entry.strip()
        if not entry:
            continue
        key, _, name = entry.partition(":")
        clients[key] = name or f"client-{i}"
    return clients


async def get_current_client(authorization: str | None = Header(default=None)) -> str:
    """Renvoie le nom du client si la clé est valide, sinon erreur 401."""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        for key, name in _parse_clients().items():
            # compare_digest évite qu'on devine la clé en mesurant le temps de réponse
            if secrets.compare_digest(key.encode(), token.encode()):
                return name
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Clé API manquante ou invalide.",
        headers={"WWW-Authenticate": "Bearer"},
    )
async def require_admin(authorization: str | None = Header(default=None)) -> None:
    """Only the admin key may read metrics."""
    if authorization and authorization.lower().startswith("bearer ") and settings.ADMIN_API_KEY:
        token = authorization[7:].strip()
        if secrets.compare_digest(settings.ADMIN_API_KEY.encode(), token.encode()):
            return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Clé admin manquante ou invalide.",
        headers={"WWW-Authenticate": "Bearer"},
    )