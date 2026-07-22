from __future__ import annotations

import json
import logging
import time
from typing import Any

from django.conf import settings

logger = logging.getLogger("medcare.select2")


def _safe_dict(d: Any) -> dict[str, Any]:
    if not isinstance(d, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in d.items():
        try:
            out[str(k)] = v
        except Exception:
            continue
    return out


class Select2DebugMiddleware:
    """
    Logs ultra détaillés sur les appels django-select2.

    Objectif: diagnostiquer 404 / field_id / cache / perf sur /select2/fields/auto.json.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        enabled = getattr(settings, "SELECT2_DEBUG_LOGS", False)
        path = getattr(request, "path", "") or ""
        if not enabled or not path.startswith("/select2/"):
            return self.get_response(request)

        t0 = time.perf_counter()
        user = getattr(request, "user", None)
        u = {
            "is_auth": bool(getattr(user, "is_authenticated", False)),
            "id": getattr(user, "pk", None),
            "type": getattr(user, "user_type", None),
            "is_patient": bool(getattr(user, "is_patient", False)) if user else False,
            "is_prestataire": bool(getattr(user, "is_prestataire", False)) if user else False,
            "is_superuser": bool(getattr(user, "is_superuser", False)) if user else False,
        }

        get_qs = _safe_dict(getattr(request, "GET", {}))
        # django-select2 utilise term/page/field_id (+ éventuels champs dépendants).
        req_meta = {
            "path": path,
            "method": getattr(request, "method", ""),
            "remote_addr": request.META.get("REMOTE_ADDR"),
            "xff": request.META.get("HTTP_X_FORWARDED_FOR"),
            "ua": request.META.get("HTTP_USER_AGENT"),
            "query": dict(get_qs),
            "user": u,
        }

        logger.debug("select2.request %s", json.dumps(req_meta, ensure_ascii=False, default=str))

        try:
            response = self.get_response(request)
        except Exception:
            logger.exception("select2.exception %s", json.dumps(req_meta, ensure_ascii=False, default=str))
            raise
        finally:
            pass

        dt_ms = int((time.perf_counter() - t0) * 1000)
        try:
            content_len = len(getattr(response, "content", b"") or b"")
        except Exception:
            content_len = None

        resp_meta = {
            "status": getattr(response, "status_code", None),
            "ms": dt_ms,
            "content_len": content_len,
        }
        # Pour debug "max", log un extrait du body en cas d'erreur.
        if resp_meta["status"] and int(resp_meta["status"]) >= 400:
            try:
                raw = (getattr(response, "content", b"") or b"")[:1200]
                resp_meta["body_head"] = raw.decode("utf-8", "ignore")
            except Exception:
                resp_meta["body_head"] = "<unreadable>"
        logger.debug("select2.response %s %s", json.dumps(req_meta, ensure_ascii=False, default=str), json.dumps(resp_meta, ensure_ascii=False, default=str))
        return response

