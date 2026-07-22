"""Redirections « next » sécurisées (anti open redirect)."""
from __future__ import annotations

from django.utils.http import url_has_allowed_host_and_scheme


def safe_next_redirect(request, candidate: str | None) -> str | None:
    """
    Retourne une URL de redirection sûre (chemins relatifs ou absolus same-host).
    """
    if not candidate:
        return None
    candidate = str(candidate).strip()
    if not candidate:
        return None
    allowed = {request.get_host()}
    if url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts=allowed,
        require_https=request.is_secure(),
    ):
        return candidate
    return None
