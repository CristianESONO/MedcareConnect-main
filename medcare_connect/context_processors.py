from urllib.parse import urlencode

from django.urls import reverse

from messaging.models import Notification, Message
from cart.models import Cart
from medcare_connect.visitor_chrome import get_footer_pillars, use_visitor_chrome

GUEST_CART_SESSION_KEY = "medcare_guest_cart_session_v1"


def global_context(request):
    chrome = use_visitor_chrome(request)
    ctx = {
        "use_visitor_chrome": chrome,
        "guest_cart_preview_url": reverse("cart:guest_cart_preview"),
        "guest_cart_merge_url": reverse("cart:cart_merge_guest"),
        "medcare_user_is_patient": bool(
            request.user.is_authenticated and getattr(request.user, "is_patient", False)
        ),
    }
    ctx["footer_pillars"] = get_footer_pillars()
    if request.user.is_authenticated:
        inbox = Notification.queryset_inbox(request.user)
        rappels = Notification.queryset_rappels(request.user)
        ctx["unread_notifications"] = inbox.filter(is_read=False).count()
        ctx["unread_rappels"] = rappels.filter(is_read=False).count()
        recent = list(inbox.order_by("-created_at")[:10])
        ctx["recent_notifications"] = recent
        ctx["recent_unread_count"] = sum(1 for n in recent if not n.is_read)
        ctx["unread_messages"] = Message.objects.filter(
            receiver=request.user, is_read=False
        ).count()
        if getattr(request.user, "is_prestataire", False):
            from healthcare.models import OrganismeDeSante
            from cart.models import DevisPart
            from appointments.models import RendezVous

            prestataire_org = OrganismeDeSante.objects.filter(user=request.user).first()
            ctx["prestataire_org"] = prestataire_org
            if prestataire_org:
                ctx["new_devis_count"] = DevisPart.objects.filter(
                    organisme=prestataire_org,
                    status="sent",
                ).exclude(devis__status="draft").count()
                ctx["new_rdv_count"] = RendezVous.objects.filter(
                    organisme=prestataire_org,
                    status=RendezVous.STATUS_REQUESTED,
                ).count()
            else:
                ctx["new_devis_count"] = 0
                ctx["new_rdv_count"] = 0
        if request.user.is_patient:
            cart = Cart.objects.filter(patient=request.user, status="active").first()
            ctx["cart_count"] = cart.item_count if cart else 0
        else:
            ctx["cart_count"] = 0
    else:
        ctx["is_visitor"] = True
        ctx["visitor_return_query"] = urlencode({"next": request.get_full_path()})
        ctx["unread_notifications"] = 0
        ctx["unread_rappels"] = 0
        ctx["recent_notifications"] = []
        ctx["recent_unread_count"] = 0
        ctx["unread_messages"] = 0
        raw = request.session.get(GUEST_CART_SESSION_KEY) or {}
        if isinstance(raw, dict):
            # Affiche le total des quantités (plus intuitif qu'un simple nombre de lignes).
            total_qty = 0
            for v in raw.values():
                try:
                    total_qty += max(0, int(v))
                except (TypeError, ValueError):
                    continue
            ctx["cart_count"] = total_qty
        else:
            ctx["cart_count"] = 0
    return ctx