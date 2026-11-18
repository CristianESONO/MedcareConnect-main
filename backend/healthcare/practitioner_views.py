from decimal import Decimal, InvalidOperation
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.db.models import F
from django.views.decorators.http import require_GET

from healthcare.models import (
    OrganismeDeSante,
    ActeMedical,
    ServiceMedical,
    PrestationTicket,
    PractitionerAffiliation,
    PrestataireActe,
    ExamenPanel,
)
from cart.models import Cart, CartItem
from messaging.models import Conversation, Message


def _get_user_org(request):
    if not request.user.is_authenticated:
        return None
    try:
        return request.user.healthcare_provider_profile
    except Exception:
        return None


def _wants_json(request):
    return (
        "application/json" in request.headers.get("Accept", "")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


# ==============================================================================
# ÉTAPE 2 : TYPE D'ÉTABLISSEMENT & DÉCOUPLAGE DES PILIERS (STRUCTURE)
# ==============================================================================

@login_required
def prestataire_type_etablissement(request):
    org = _get_user_org(request)
    if not org:
        messages.error(request, "Veuillez d'abord créer votre établissement.")
        return redirect("healthcare:organisme_create")

    if not org.is_active:
        messages.warning(request, "Votre structure est en attente d'activation. L'accès aux panels d'examens sera disponible dès validation de votre compte.")
        return redirect("healthcare:prestataire_dashboard")

    from healthcare.prestataire_catalogue import official_pilier_services
    from healthcare.data.structure_types_demo import DEMO_STRUCTURE_TYPES, PILIER_KEY_TO_SLUG

    canonical_piliers = official_pilier_services()
    active_pilier_ids = set(org.piliers_actifs.values_list("id", flat=True))

    # Carte label → set de slugs suggérés (pour le JS de suggestion — non contraignant)
    # Construit depuis DEMO_STRUCTURE_TYPES pour rester en synchro avec la source de vérité
    slug_to_id = {p.slug: p.id for p in canonical_piliers}
    type_piliers_map: dict[str, list[int]] = {}
    for row in DEMO_STRUCTURE_TYPES:
        suggested_ids = [
            slug_to_id[PILIER_KEY_TO_SLUG[k]]
            for k in row["pilier_keys"]
            if PILIER_KEY_TO_SLUG.get(k) in slug_to_id
        ]
        type_piliers_map[row["label"]] = suggested_ids
    # Types indicatifs consolidés (union démo + suppléments V1)
    indicatif_types = [
        {"name": row["label"], "icon": row["icon"], "proposed": False}
        for row in DEMO_STRUCTURE_TYPES
    ] + [
        {"name": "Centre de vaccination", "icon": "💉", "proposed": True},
        {"name": "Cabinet de médecine générale", "icon": "🧑‍⚕️", "proposed": True},
        {"name": "Polyclinique", "icon": "🏬", "proposed": True},
        {"name": "Centre de santé", "icon": "🏘️", "proposed": True},
        {"name": "Maternité", "icon": "👶", "proposed": True},
    ]

    if request.method == "POST":
        org.name = request.POST.get("name", org.name).strip()
        org.topology_type = request.POST.get("topology_type", org.topology_type)
        org.address = request.POST.get("address", org.address).strip()
        org.city = request.POST.get("city", org.city).strip()
        org.ninea = request.POST.get("ninea", org.ninea or "").strip() or None
        org.type_libre = request.POST.get("type_libre", org.type_libre or "").strip()

        # Piliers choisis librement — aucune contrainte liée au type
        pilier_ids = request.POST.getlist("piliers")
        selected_piliers = ServiceMedical.objects.filter(id__in=pilier_ids)
        org.piliers_actifs.set(selected_piliers)

        org.save()
        messages.success(request, "Type d'établissement et piliers d'activité enregistrés avec succès.")
        if "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"ok": True, "message": "Configuration enregistrée."})
        return redirect("healthcare:prestataire_type_etablissement")

    # Groupement par domaine pour l'affichage
    domain_piliers = {
        "paraclinique": {
            "name": "Paraclinique",
            "color": "#14b87a",
            "piliers": canonical_piliers,
        }
    }

    import json
    context = {
        "org": org,
        "dash_active": "typeetab",
        "canonical_piliers": canonical_piliers,
        "active_pilier_ids": active_pilier_ids,
        "indicatif_types": indicatif_types,
        "domain_piliers": domain_piliers,
        "type_piliers_map_json": json.dumps(type_piliers_map),
    }
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse({
            "organization": org.name,
            "address": org.address or "",
            "city": org.city or "",
            "ninea": org.ninea or "",
            "topology_type": org.topology_type or "simple",
            "type_libre": org.type_libre or "",
            "types": indicatif_types,
            "pillars": [
                {
                    "id": pillar.pk,
                    "name": pillar.display_name,
                    "slug": pillar.slug,
                    "icon": str(pillar.display_icon or ""),
                    "active": pillar.pk in active_pilier_ids,
                }
                for pillar in canonical_piliers
            ],
            "type_pillars_map": type_piliers_map,
        })
    from medcare_connect.views import react_app

    return react_app(request)



# ==============================================================================
# ÉTAPE 4 : TICKETS DE PRESTATION (ESPACE PRATICIEN INDÉPENDANT)
# ==============================================================================

@login_required
def prestataire_tickets(request):
    org = _get_user_org(request)
    if not org:
        return redirect("healthcare:organisme_create")
    if "application/json" in request.headers.get("Accept", "") and not org.is_praticien:
        return JsonResponse({"error": "Cette fonction est réservée aux praticiens."}, status=403)

    tickets = PrestationTicket.objects.filter(organisme=org).order_by("-created_at")
    my_actes = PrestataireActe.objects.filter(organisme=org, is_available=True).select_related("acte")
    from messaging.models import Conversation
    conversations = (
        Conversation.objects.filter(prestataire=org.user)
        .select_related("patient")
        .order_by("-updated_at")[:50]
    )
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse({
            "organization": org.name,
            "tickets": [
                {
                    "id": ticket.pk,
                    "title": ticket.title,
                    "description": ticket.description or "",
                    "price": str(ticket.price),
                    "mode": ticket.mode,
                    "mode_label": ticket.get_mode_display(),
                    "zone": ticket.zone,
                    "disponibilite": ticket.disponibilite,
                    "is_active": ticket.is_active,
                    "views_count": ticket.views_count,
                    "identifiant": ticket.identifiant,
                    "public_path": ticket.get_public_path(),
                    "search_url": ticket.get_search_url(),
                    "acte": {
                        "id": ticket.acte_id,
                        "name": ticket.acte.name,
                    } if ticket.acte_id else None,
                    "created_at": ticket.created_at.isoformat(),
                }
                for ticket in tickets.select_related("acte")
            ],
            "actes": [
                {
                    "id": pa.acte_id,
                    "name": pa.acte.name,
                    "price": str(pa.price),
                }
                for pa in my_actes
            ],
            "conversations": [
                {
                    "id": conversation.pk,
                    "patient": conversation.patient.get_full_name() or conversation.patient.username,
                    "subject": conversation.subject or "",
                }
                for conversation in conversations
            ],
        })

    context = {
        "org": org,
        "dash_active": "tickets",
        "tickets": tickets,
        "my_actes": my_actes,
        "conversations": conversations,
        "base_url": request.build_absolute_uri("/").rstrip("/"),
    }
    from medcare_connect.views import react_app

    return react_app(request)


@login_required
def prestataire_ticket_create(request):
    org = _get_user_org(request)
    if not org:
        return redirect("healthcare:organisme_create")
    if not org.is_praticien:
        if _wants_json(request):
            return JsonResponse({"error": "Cette fonction est réservée aux praticiens."}, status=403)
        raise Http404("Réservé aux praticiens")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        wants_json = _wants_json(request)
        description = request.POST.get("description", "").strip()
        price_raw = request.POST.get("price", "0").replace(" ", "").replace("F", "").replace("CFA", "")
        try:
            price = Decimal(price_raw)
        except (InvalidOperation, ValueError):
            if wants_json:
                return JsonResponse({"error": "Saisissez un tarif valide."}, status=400)
            price = Decimal("10000")
        if wants_json and not title:
            return JsonResponse({"error": "Le titre de la prestation est obligatoire."}, status=400)
        if wants_json and (not price.is_finite() or price < 0):
            return JsonResponse({"error": "Le tarif ne peut pas être négatif."}, status=400)

        mode = request.POST.get("mode", "domicile")
        if wants_json and mode not in ("domicile", "cabinet"):
            return JsonResponse({"error": "Modalité de prestation invalide."}, status=400)
        zone = request.POST.get("zone", "Dakar").strip()
        disponibilite = request.POST.get("disponibilite", "Créneaux sur demande").strip()
        acte_id = request.POST.get("acte_id")

        acte = None
        if acte_id:
            acte = ActeMedical.objects.filter(id=acte_id, is_active=True, level=3).first()
            if wants_json and acte is None:
                return JsonResponse({"error": "Sélectionnez un acte valide."}, status=400)

        # Générer un slug identifiant unique pour le lien privé (ex: cheikh-ndiaye-kine-3a7b)
        base_slug = slugify(f"{org.name}-{title}"[:30]) or "prestation"
        identifiant = f"{base_slug}-{get_random_string(6).lower()}"
        while PrestationTicket.objects.filter(identifiant=identifiant).exists():
            identifiant = f"{base_slug}-{get_random_string(7).lower()}"

        ticket = PrestationTicket.objects.create(
            organisme=org,
            identifiant=identifiant,
            title=title or "Séance de soins",
            description=description,
            acte=acte,
            price=price,
            mode=mode,
            zone=zone,
            disponibilite=disponibilite,
            is_active=True,
        )

        if wants_json:
            return JsonResponse({
                "ok": True,
                "id": ticket.pk,
                "title": ticket.title,
                "public_path": ticket.get_public_path(),
                "message": "Ticket créé.",
            }, status=201)
        messages.success(request, f"Ticket « {ticket.title} » créé avec succès ! Votre lien privé est prêt.")
        return redirect("healthcare:prestataire_tickets")

    return redirect("healthcare:prestataire_tickets")


@login_required
def prestataire_ticket_toggle(request, pk):
    org = _get_user_org(request)
    ticket = get_object_or_404(PrestationTicket, pk=pk, organisme=org)
    ticket.is_active = not ticket.is_active
    ticket.save(update_fields=["is_active", "updated_at"])

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
        return JsonResponse({"status": "ok", "is_active": ticket.is_active})

    state = "activé" if ticket.is_active else "désactivé"
    messages.info(request, f"Le ticket « {ticket.title} » a été {state}.")
    return redirect("healthcare:prestataire_tickets")


@login_required
def prestataire_ticket_delete(request, pk):
    org = _get_user_org(request)
    ticket = get_object_or_404(PrestationTicket, pk=pk, organisme=org)
    title = ticket.title
    ticket.delete()
    if _wants_json(request):
        return JsonResponse({"ok": True, "message": f"Le ticket « {title} » a été supprimé."})
    messages.success(request, f"Le ticket « {title} » a été supprimé.")
    return redirect("healthcare:prestataire_tickets")


@login_required
def ticket_send(request):
    """Envoyer le lien d'un ticket de prestation dans la messagerie vers des patients sélectionnés."""
    if request.method != "POST":
        return redirect("healthcare:prestataire_tickets")

    org = _get_user_org(request)
    if not org:
        return redirect("healthcare:organisme_create")

    ticket_url = request.POST.get("ticket_url", "").strip()
    ticket_nom = request.POST.get("ticket_nom", "Ticket de prestation").strip()
    conv_ids = request.POST.getlist("conv_ids")

    if not conv_ids:
        if _wants_json(request):
            return JsonResponse({"error": "Sélectionnez au moins un patient."}, status=400)
        messages.error(request, "Sélectionnez au moins un patient.")
        return redirect("healthcare:prestataire_tickets")

    from messaging.models import Conversation, Message
    sent = 0
    for conv_id in conv_ids:
        try:
            conv = Conversation.objects.get(pk=int(conv_id), prestataire=org.user)
        except (Conversation.DoesNotExist, ValueError):
            continue
        Message.objects.create(
            conversation=conv,
            sender=org.user,
            receiver=conv.patient,
            content=(
                f"🎫 **{ticket_nom}**\n"
                f"Voici votre ticket de prestation direct :\n"
                f"{ticket_url}\n\n"
                f"Cliquez sur le lien pour finaliser votre réservation et fixer votre rendez-vous."
            ),
            message_type="internal",
            payload={"type": "ticket_link", "ticket_url": ticket_url, "ticket_nom": ticket_nom},
        )
        conv.save(update_fields=["updated_at"])
        sent += 1

    if _wants_json(request):
        if not sent:
            return JsonResponse({"error": "Aucun message envoyé. Vérifiez les conversations sélectionnées."}, status=400)
        return JsonResponse({"ok": True, "sent": sent, "message": f"Ticket envoyé à {sent} patient(s)."})
    messages.success(request, f"Ticket envoyé avec succès à {sent} patient(s).")
    return redirect("healthcare:prestataire_tickets")


# ==============================================================================
# ÉTAPE 6 : SECTION ACCÈS PRATICIEN & AFFILIATIONS MULTI
# ==============================================================================

@login_required
def prestataire_acces(request):
    org = _get_user_org(request)
    if not org:
        return redirect("healthcare:organisme_create")

    if org.is_praticien:
        affiliations = PractitionerAffiliation.objects.filter(
            praticien=org, status__in=["pending", "approved"]
        ).select_related("structure")
        # Invitations reçues de structures (initiated_by=structure, statut=invited)
        invitations_recues = PractitionerAffiliation.objects.filter(
            praticien=org, status="invited", initiated_by="structure"
        ).select_related("structure")
        structures_dispo = (
            OrganismeDeSante.objects.filter(account_nature="structure", is_active=True)
            .exclude(id__in=PractitionerAffiliation.objects.filter(praticien=org).values_list("structure_id", flat=True))
            .order_by("name")
        )
        praticiens_dispo = []
    else:
        # Côté structure hôte
        affiliations = PractitionerAffiliation.objects.filter(
            structure=org, status__in=["pending", "approved", "invited"]
        ).select_related("praticien")
        invitations_recues = []
        structures_dispo = []
        # Praticiens disponibles à inviter (pas encore affiliés)
        praticiens_dispo = (
            OrganismeDeSante.objects.filter(account_nature="praticien", is_active=True)
            .exclude(id__in=PractitionerAffiliation.objects.filter(structure=org).values_list("praticien_id", flat=True))
            .order_by("name")
        )

    context = {
        "org": org,
        "dash_active": "acces",
        "affiliations": affiliations,
        "invitations_recues": invitations_recues,
        "structures_dispo": structures_dispo,
        "praticiens_dispo": praticiens_dispo,
        "day_choices": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
    }
    if "application/json" in request.headers.get("Accept", ""):
        def serialize_affiliation(affiliation, peer):
            return {
                "id": affiliation.pk,
                "name": peer.name,
                "city": peer.city or "",
                "role_title": affiliation.role_title,
                "days_schedule": affiliation.days_schedule or [],
                "status": affiliation.status,
                "status_label": affiliation.get_status_display(),
                "initiated_by": affiliation.initiated_by,
                "agenda_url": (
                    f"/sante/prestataire/acces/agenda/{affiliation.pk}/"
                    if org.is_praticien and affiliation.status == "approved"
                    else None
                ),
            }

        return JsonResponse({
            "organization": org.name,
            "is_practitioner": org.is_praticien,
            "affiliations": [
                serialize_affiliation(affiliation, affiliation.structure if org.is_praticien else affiliation.praticien)
                for affiliation in affiliations
            ],
            "received_invitations": [
                serialize_affiliation(affiliation, affiliation.structure)
                for affiliation in invitations_recues
            ],
            "available_structures": [
                {"id": item.pk, "name": item.name, "city": item.city or "", "address": item.address or ""}
                for item in structures_dispo
            ],
            "available_practitioners": [
                {"id": item.pk, "name": item.name, "city": item.city or "", "profession": item.get_profession_display() or ""}
                for item in praticiens_dispo
            ],
            "days": DAYS_FR,
        })
    from medcare_connect.views import react_app

    return react_app(request)


@login_required
def prestataire_affiliation_create(request):
    """Praticien → demande d'accès à une structure."""
    org = _get_user_org(request)
    if not org:
        return redirect("healthcare:organisme_create")
    if not org.is_praticien:
        raise Http404("Réservé aux praticiens")

    if request.method == "POST":
        structure_id = request.POST.get("structure_id")
        structure = get_object_or_404(
            OrganismeDeSante,
            id=structure_id,
            account_nature="structure",
            is_active=True,
        )

        role_title = request.POST.get("role_title", "").strip() or "Praticien consultant"
        days_raw = request.POST.getlist("days")

        affiliation, created = PractitionerAffiliation.objects.get_or_create(
            praticien=org,
            structure=structure,
            defaults={
                "role_title": role_title,
                "days_schedule": days_raw,
                "status": "pending",
                "initiated_by": "praticien",
            },
        )
        if _wants_json(request):
            if not created:
                return JsonResponse({"error": "Une demande ou affiliation existe déjà pour cette structure."}, status=400)
            return JsonResponse({"ok": True, "id": affiliation.pk, "message": f"Demande envoyée à {structure.name}."}, status=201)
        messages.success(request, f"Demande d'accès envoyée à {structure.name}. En attente de validation.")
    return redirect("healthcare:prestataire_acces")


@login_required
def prestataire_affiliation_invite(request):
    """Structure → invitation d'un praticien."""
    org = _get_user_org(request)
    if not org or org.is_praticien:
        raise Http404("Réservé aux structures")

    if request.method == "POST":
        praticien_id = request.POST.get("praticien_id")
        praticien = get_object_or_404(OrganismeDeSante, id=praticien_id, is_active=True)
        if not praticien.is_praticien:
            if _wants_json(request):
                return JsonResponse({"error": "Cet organisme n'est pas un praticien."}, status=400)
            messages.error(request, "Cet organisme n'est pas un praticien.")
            return redirect("healthcare:prestataire_acces")

        role_title = request.POST.get("role_title", "").strip() or "Intervenant"
        days_raw = request.POST.getlist("days")

        aff, created = PractitionerAffiliation.objects.get_or_create(
            praticien=praticien,
            structure=org,
            defaults={
                "role_title": role_title,
                "days_schedule": days_raw,
                "status": "invited",
                "initiated_by": "structure",
            },
        )
        if created:
            messages.success(request, f"Invitation envoyée à {praticien.name}. En attente de son acceptation.")
        else:
            if _wants_json(request):
                return JsonResponse({"error": f"{praticien.name} est déjà rattaché ou a déjà une demande en cours."}, status=400)
            messages.warning(request, f"{praticien.name} est déjà rattaché ou a déjà une demande en cours.")
        if _wants_json(request):
            return JsonResponse({"ok": True, "id": aff.pk, "message": f"Invitation envoyée à {praticien.name}."}, status=201)
    return redirect("healthcare:prestataire_acces")


@login_required
def prestataire_affiliation_accept(request, pk):
    """Praticien accepte une invitation de structure."""
    org = _get_user_org(request)
    aff = get_object_or_404(
        PractitionerAffiliation, pk=pk, praticien=org, status="invited", initiated_by="structure"
    )
    aff.status = "approved"
    aff.save(update_fields=["status", "updated_at"])
    if _wants_json(request):
        return JsonResponse({"ok": True, "message": f"Vous avez rejoint {aff.structure.name}."})
    messages.success(request, f"Vous avez rejoint {aff.structure.name} avec succès !")
    return redirect("healthcare:prestataire_acces")


@login_required
def prestataire_affiliation_approve(request, pk):
    """Structure valide une demande d'un praticien."""
    org = _get_user_org(request)
    aff = get_object_or_404(PractitionerAffiliation, pk=pk, structure=org)
    aff.status = "approved"
    aff.save(update_fields=["status", "updated_at"])
    if _wants_json(request):
        return JsonResponse({"ok": True, "message": f"L'accès de {aff.praticien.name} a été validé."})
    messages.success(request, f"L'accès pour le praticien {aff.praticien.name} a été validé avec succès.")
    return redirect("healthcare:prestataire_acces")


@login_required
def prestataire_affiliation_delete(request, pk):
    org = _get_user_org(request)
    aff = get_object_or_404(PractitionerAffiliation, pk=pk)
    if aff.praticien != org and aff.structure != org:
        raise Http404("Non autorisé")
    aff.delete()
    if _wants_json(request):
        return JsonResponse({"ok": True, "message": "Rattachement supprimé."})
    messages.info(request, "Rattachement supprimé.")
    return redirect("healthcare:prestataire_acces")


# ==============================================================================
# ÉTAPE 5 : VUE PATIENT DU TICKET DIRECT (/t/<identifiant>)
# Résout à la fois les PrestationTicket (praticiens) et les ExamenPanel (structures)
# ==============================================================================

def patient_ticket_view(request, token):
    wants_json = "application/json" in request.headers.get("Accept", "")
    # Essayer d'abord un ExamenPanel (structure multi-actes)
    panel = ExamenPanel.objects.filter(token=token).first()
    if panel:
        return _panel_patient_view(request, panel)

    ticket = get_object_or_404(PrestationTicket, identifiant=token)
    if not wants_json:
        PrestationTicket.objects.filter(pk=ticket.pk).update(views_count=F("views_count") + 1)
        ticket.refresh_from_db()

    praticien = ticket.organisme
    prestataire_user = praticien.user

    if request.method == "GET" and wants_json:
        return JsonResponse(
            {
                "kind": "ticket",
                "token": token,
                "title": ticket.title,
                "description": ticket.description or "",
                "price": str(ticket.price) if ticket.price is not None else "",
                "mode": ticket.get_mode_display(),
                "zone": ticket.zone or "",
                "availability": ticket.disponibilite or "",
                "act": ticket.acte.name if ticket.acte else "",
                "provider": {
                    "name": praticien.name,
                    "slug": praticien.slug,
                    "city": praticien.city or "",
                },
                "login_url": f"/connexion/?next=/t/{token}/",
                "signup_url": f"/inscription/?next=/t/{token}/",
                "cart_url": f"/t/{token}/",
                "contact_url": f"/messaging/demarrer/{praticien.slug}/",
            }
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Flux réel : patient authentifié qui clique sur un lien partagé (LinkedIn…)
    # → On ouvre/reprend la conversation immédiatement, sans page intermédiaire.
    # ──────────────────────────────────────────────────────────────────────────
    if request.method == "GET" and request.user.is_authenticated and getattr(request.user, "is_patient", False):
        if prestataire_user:
            conv = Conversation.objects.filter(
                patient=request.user,
                prestataire=prestataire_user,
            ).first()

            if not conv:
                price_str = f"{int(ticket.price)} FCFA" if ticket.price else "Tarif sur demande"
                conv = Conversation.objects.create(
                    patient=request.user,
                    prestataire=prestataire_user,
                    subject=f"Prestation : {ticket.title}",
                    kind=Conversation.KIND_GENERAL,
                )
                Message.objects.create(
                    conversation=conv,
                    sender=request.user,
                    receiver=prestataire_user,
                    content=(
                        f"Bonjour, j'ai découvert votre prestation « {ticket.title} » "
                        f"({price_str} · {ticket.get_mode_display()}) et je souhaite "
                        f"en savoir plus ou convenir d'un rendez-vous."
                    ),
                )
            return redirect("messaging:conversation_detail", pk=conv.pk)

    # Actions POST depuis la page info (visiteur non connecté)
    if request.method == "POST" and request.POST.get("action") == "add_cart":
        # S'assurer qu'un PrestataireActe existe pour cet acte et ce praticien
        if ticket.acte:
            pa, _ = PrestataireActe.objects.get_or_create(
                organisme=praticien,
                acte=ticket.acte,
                defaults={"price": ticket.price, "is_available": True},
            )
        else:
            first_acte = ActeMedical.objects.filter(is_active=True).first()
            pa, _ = PrestataireActe.objects.get_or_create(
                organisme=praticien,
                acte=first_acte,
                defaults={"price": ticket.price, "is_available": True},
            )

        if request.user.is_authenticated and request.user.is_patient:
            cart = Cart.get_active_cart(request.user)
            item, created = CartItem.objects.get_or_create(cart=cart, prestataire_acte=pa)
            if not created:
                item.quantity += 1
                item.save(update_fields=["quantity"])
        else:
            session_cart = request.session.get("guest_cart", [])
            session_cart.append(pa.id)
            request.session["guest_cart"] = session_cart
            request.session.modified = True

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "status": "ok",
                "message": "Prestation ajoutée au panier !",
                "cart_url": "/cart/",
            })

        messages.success(request, f"« {ticket.title} » a été ajouté à votre panier.")
        return redirect(request.path)

    # Demande de devis / connexion depuis la page info visiteur
    if request.method == "POST" and request.POST.get("action") == "request_devis":
        if not request.user.is_authenticated:
            if wants_json:
                return JsonResponse(
                    {
                        "error": "Connectez-vous pour contacter cette structure.",
                        "login_url": f"/connexion/?next=/t/{token}/",
                    },
                    status=401,
                )
            return redirect(f"/connexion/?next=/t/{token}/")
        if prestataire_user:
            conv = Conversation.objects.filter(
                patient=request.user,
                prestataire=prestataire_user,
            ).first()
            if not conv:
                price_str = f"{int(ticket.price)} FCFA" if ticket.price else "Tarif sur demande"
                conv = Conversation.objects.create(
                    patient=request.user,
                    prestataire=prestataire_user,
                    subject=f"Prestation : {ticket.title}",
                    kind=Conversation.KIND_GENERAL,
                )
                Message.objects.create(
                    conversation=conv,
                    sender=request.user,
                    receiver=prestataire_user,
                    content=(
                        f"Bonjour, je souhaite obtenir un devis / convenir d'un RDV "
                        f"pour votre prestation : {ticket.title} "
                        f"({'%d FCFA' % ticket.price if ticket.price else 'Tarif sur demande'} "
                        f"· {ticket.get_mode_display()})."
                    ),
                )
            if wants_json:
                return JsonResponse(
                    {
                        "ok": True,
                        "redirect_url": reverse(
                            "messaging:conversation_detail", args=[conv.pk]
                        ),
                    }
                )
            return redirect("messaging:conversation_detail", pk=conv.pk)

    # ──────────────────────────────────────────────────────────────────────────
    # Page d'information — visiteur non connecté (ou praticien sans compte user)
    # ──────────────────────────────────────────────────────────────────────────
    from medcare_connect.views import react_app

    return react_app(request)


def patient_mobile_view(request):
    """Interface React mobile patient MedCare."""
    from medcare_connect.views import react_app

    return react_app(request)


@require_GET
def patient_mobile_data_api(request):
    latest_ticket = (
        PrestationTicket.objects.filter(is_active=True)
        .select_related("organisme", "acte")
        .order_by("-created_at")
        .first()
    )
    if not latest_ticket:
        return JsonResponse({"ticket": None})

    organization = latest_ticket.organisme
    return JsonResponse(
        {
            "ticket": {
                "token": latest_ticket.identifiant,
                "title": latest_ticket.title,
                "description": latest_ticket.description,
                "price": str(latest_ticket.price),
                "mode": latest_ticket.get_mode_display(),
                "zone": latest_ticket.zone,
                "availability": latest_ticket.disponibilite,
                "act": latest_ticket.acte.name if latest_ticket.acte_id else "",
                "public_url": latest_ticket.get_public_path(),
                "provider": {
                    "name": organization.name,
                    "profession": organization.profession or "",
                    "city": organization.city or "",
                    "quartier": organization.quartier or "",
                    "slug": organization.slug,
                    "logo": organization.logo.url if organization.logo else None,
                },
            }
        }
    )


# ==============================================================================
# AGENDA PRATICIEN PAR STRUCTURE (Étape 6 avancée)
# ==============================================================================

HOURS = [f"{h:02d}:00" for h in range(7, 21)]
DAYS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


@login_required
def agenda_praticien_edit(request, aff_pk):
    """
    Calendrier hebdomadaire interactif : le praticien définit ses créneaux
    heure par heure pour chaque structure d'affiliation (status=approved).
    """
    org = _get_user_org(request)
    if not org or not org.is_praticien:
        raise Http404("Réservé aux praticiens")

    aff = get_object_or_404(PractitionerAffiliation, pk=aff_pk, praticien=org, status="approved")

    if request.method == "POST":
        # Grille envoyée sous forme de checkboxes "day_hour" ex: "Lundi_09:00"
        raw_slots = request.POST.getlist("slots")
        invalid_slots = [
            slot for slot in raw_slots
            if "_" not in slot
            or slot.split("_", 1)[0] not in DAYS_FR
            or slot.split("_", 1)[1] not in HOURS
        ]
        if _wants_json(request) and invalid_slots:
            return JsonResponse({"error": "Un ou plusieurs créneaux sont invalides."}, status=400)
        # Structure en dict {jour: [heures]}
        schedule: dict[str, list[str]] = {}
        for slot in raw_slots:
            if "_" in slot:
                day, hour = slot.split("_", 1)
                if day in DAYS_FR and hour in HOURS:
                    schedule.setdefault(day, []).append(hour)

        aff.days_schedule = [
            f"{day} : {', '.join(sorted(hours))}"
            for day, hours in sorted(
                schedule.items(),
                key=lambda x: DAYS_FR.index(x[0]) if x[0] in DAYS_FR else 99,
            )
        ]
        aff.save(update_fields=["days_schedule", "updated_at"])
        if _wants_json(request):
            return JsonResponse({"ok": True, "message": f"Agenda mis à jour pour {aff.structure.name}."})
        messages.success(request, f"Agenda mis à jour pour {aff.structure.name}.")
        return redirect("healthcare:prestataire_acces")

    # Reconstruire la grille depuis days_schedule
    active_slots: set[str] = set()
    for line in (aff.days_schedule or []):
        # Format: "Lundi : 09:00, 10:00"
        if ":" in line:
            parts = line.split(":", 1)
            day = parts[0].strip()
            for h in parts[1].split(","):
                h = h.strip()
                if h:
                    active_slots.add(f"{day}_{h}")

    grid_rows = []
    for hour in HOURS:
        row_slots = []
        for day in DAYS_FR:
            slot_key = f"{day}_{hour}"
            row_slots.append({
                "key": slot_key,
                "day": day,
                "hour": hour,
                "is_active": slot_key in active_slots,
            })
        grid_rows.append({"hour": hour, "slots": row_slots})

    context = {
        "org": org,
        "aff": aff,
        "dash_active": "acces",
        "account_page_title": f"Agenda · {aff.structure.name}",
        "days": DAYS_FR,
        "hours": HOURS,
        "grid_rows": grid_rows,
        "active_slots_count": len(active_slots),
    }
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse({
            "organization": org.name,
            "structure": aff.structure.name,
            "affiliation_id": aff.pk,
            "days": DAYS_FR,
            "hours": HOURS,
            "active_slots": sorted(active_slots),
            "active_slots_count": len(active_slots),
        })
    from medcare_connect.views import react_app

    return react_app(request)


# ==============================================================================
# FICHE PUBLIQUE PRATICIEN (Étape 6 — visibilité via acte proposé)
# ==============================================================================

def praticien_public_detail(request, slug):
    """
    Fiche publique d'un praticien indépendant.
    Accessible via /sante/praticien/<slug>/ et apparaît dans les résultats
    de recherche si un acte correspondant est proposé.
    """
    wants_json = _wants_json(request)
    if not wants_json:
        from medcare_connect.views import react_app

        return react_app(request)

    from django.utils.text import slugify as dj_slugify

    # Recherche directe par slug
    praticien = OrganismeDeSante.objects.filter(slug=slug, is_active=True, account_nature="praticien").first()
    if not praticien and slug.isdigit():
        praticien = OrganismeDeSante.objects.filter(pk=int(slug), is_active=True, account_nature="praticien").first()

    # Recherche de secours par slugification du nom (sans charger tous les objets)
    if not praticien:
        # Chercher par slugification sur les praticiens uniquement (filtré en DB)
        for p in OrganismeDeSante.objects.filter(is_active=True, account_nature="praticien").only("id", "name", "slug", "account_nature"):
            if dj_slugify(p.name) == slug or p.slug == slug:
                praticien = OrganismeDeSante.objects.filter(pk=p.pk).first()
                break

    if not praticien or not praticien.is_praticien:
        raise Http404("Praticien introuvable")

    actes = PrestataireActe.objects.filter(
        organisme=praticien, is_available=True
    ).select_related("acte", "acte__service_medical_category")

    affiliations = PractitionerAffiliation.objects.filter(
        praticien=praticien, status="approved"
    ).select_related("structure")

    tickets = PrestationTicket.objects.filter(
        organisme=praticien, is_active=True
    ).exclude(identifiant="").exclude(identifiant__isnull=True).order_by("-created_at")

    context = {
        "praticien": praticien,
        "actes": actes,
        "affiliations": affiliations,
        "tickets": tickets,
        "page_title": f"{praticien.name} · Praticien MedCare Connect",
    }
    return JsonResponse(
        {
            "id": praticien.pk,
            "name": praticien.name,
            "slug": praticien.slug,
            "profession": praticien.profession or "",
            "specialty": getattr(praticien, "specialite", "") or "",
            "city": praticien.city or "",
            "quartier": praticien.quartier or "",
            "address": praticien.address or "",
            "phone": praticien.contact_phone or "",
            "description": praticien.description or "",
            "logo": (
                request.build_absolute_uri(praticien.logo.url)
                if praticien.logo
                else ""
            ),
            "acts": [
                {
                    "id": pa.pk,
                    "name": pa.acte.name,
                    "category": (
                        pa.acte.service_medical_category.name
                        if pa.acte.service_medical_category
                        else ""
                    ),
                    "price": str(pa.price),
                    "delay": pa.get_delai_display() if pa.delai else "",
                    "add_url": reverse("cart:cart_add", kwargs={"pk": pa.pk}),
                }
                for pa in actes
            ],
            "affiliations": [
                {
                    "structure": affiliation.structure.name,
                    "city": affiliation.structure.city or "",
                    "role": affiliation.role_title or "",
                    "days": affiliation.days_schedule or [],
                    "profile_url": reverse(
                        "healthcare:organisme_detail",
                        kwargs={"slug": affiliation.structure.slug},
                    ),
                }
                for affiliation in affiliations
            ],
            "tickets": [
                {
                    "title": ticket.title,
                    "description": ticket.description,
                    "price": str(ticket.price),
                    "mode": ticket.get_mode_display(),
                    "zone": ticket.zone,
                    "availability": ticket.disponibilite,
                    "url": ticket.get_public_path(),
                    "search_url": ticket.get_search_url(),
                }
                for ticket in tickets
            ],
        }
    )


# ==============================================================================
# PANELS D'EXAMENS (structures)
# ==============================================================================

@login_required
def prestataire_panels(request):
    """Liste des panels d'examens de la structure."""
    org = _get_user_org(request)
    if not org:
        if "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"error": "Veuillez d'abord créer votre établissement."}, status=401)
        messages.error(request, "Veuillez d'abord créer votre établissement.")
        return redirect("healthcare:organisme_create")

    if not org.is_active:
        if "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"error": "Votre structure est en attente d'activation."}, status=403)
        messages.warning(request, "Votre structure est en attente d'activation. L'accès aux panels d'examens sera disponible dès validation de votre compte.")
        return redirect("healthcare:prestataire_dashboard")

    if "application/json" not in request.headers.get("Accept", ""):
        from medcare_connect.views import react_app

        return react_app(request)

    panels = ExamenPanel.objects.filter(organisme=org).prefetch_related("actes", "actes__acte")

    # Actes disponibles pour la recherche JS et le constructeur
    # Inclut l'ensemble des actes médicaux de référence MedCare (5 piliers, hors ambulance),
    # enrichis avec le statut et le tarif configuré par l'organisme s'il existe.
    from healthcare.models import ActeMedical
    pa_by_acte_id = {
        pa.acte_id: pa
        for pa in PrestataireActe.objects.filter(organisme=org).select_related("acte")
    }
    all_actes = (
        ActeMedical.objects.filter(is_active=True, level=3)
        .exclude(service_medical_category__slug="ambulance-medicalisee")
        .filter(service_medical_category__order__lte=10)
        .select_related("service_medical_category", "parent_service")
        .order_by("service_medical_category__order", "name")
    )
    actes_data = []
    for am in all_actes:
        pa = pa_by_acte_id.get(am.id)
        if pa:
            actes_data.append({
                "id": pa.pk,
                "acte_id": am.id,
                "nom": am.name,
                "cat": (
                    am.service_medical_category.name
                    if am.service_medical_category
                    else "Général"
                ),
                "sous_cat": am.parent_service.name if am.parent_service else "",
                "prix": float(pa.price) if pa.price else (float(am.reference_price) if am.reference_price else 0),
                "actif": bool(pa.is_available),
                "configured": True,
            })
        else:
            actes_data.append({
                "id": f"am_{am.id}",
                "acte_id": am.id,
                "nom": am.name,
                "cat": (
                    am.service_medical_category.name
                    if am.service_medical_category
                    else "Général"
                ),
                "sous_cat": am.parent_service.name if am.parent_service else "",
                "prix": float(am.reference_price) if am.reference_price else 0,
                "actif": False,
                "configured": False,
            })
    # Conversations actives (pour le modal "Envoyer à")
    from messaging.models import Conversation
    conversations = Conversation.objects.filter(
        prestataire=org.user,
        is_active=True,
    ).select_related("patient").order_by("-updated_at")[:50]

    if "application/json" in request.headers.get("Accept", ""):
        panel_items = [
            {
                "id": panel.pk,
                "kind": panel.kind,
                "nom": panel.nom,
                "description": panel.description or "",
                "actes": [
                    {"id": pa.pk, "nom": pa.acte.name, "price": float(pa.price or 0)}
                    for pa in panel.actes.select_related("acte").all()
                ],
                "is_active": panel.is_active,
                "token": panel.token,
                "public_path": panel.get_public_path(),
                "search_url": panel.get_search_url(),
                "total_price": float(panel.total_price),
                "views_count": panel.views_count,
                "is_prestation_ticket": False,
            }
            for panel in panels
        ]
        from healthcare.models import PrestationTicket
        panel_items.extend([
            {
                "id": f"pt_{ticket.pk}",
                "kind": "ticket",
                "nom": ticket.title,
                "description": ticket.description or "",
                "actes": [
                    {"id": ticket.acte_id, "nom": ticket.acte.name, "price": float(ticket.price or 0)}
                ] if ticket.acte_id else [],
                "is_active": ticket.is_active,
                "token": ticket.identifiant,
                "public_path": ticket.get_public_path(),
                "search_url": ticket.get_search_url(),
                "total_price": float(ticket.price or 0),
                "views_count": ticket.views_count,
                "is_prestation_ticket": True,
            }
            for ticket in PrestationTicket.objects.filter(organisme=org).select_related("acte")
        ])
        return JsonResponse({
            "organization": org.name,
            "panels": panel_items,
            "acts": actes_data,
            "conversations": [
                {
                    "id": conversation.pk,
                    "patient": conversation.patient.get_full_name() or conversation.patient.username,
                    "subject": conversation.subject or "",
                }
                for conversation in conversations
            ],
        })

@login_required
def panel_create(request):
    """Créer ou modifier un panel d'examens ou un ticket (supporte formulaire classique et AJAX)."""
    if request.method != "POST":
        return redirect("healthcare:prestataire_panels")

    org = _get_user_org(request)
    if not org:
        return redirect("healthcare:organisme_create")

    is_ajax = _wants_json(request)
    panel_id = request.POST.get("panel_id")
    nom = request.POST.get("nom", "").strip()
    kind = request.POST.get("kind", "panel")
    description = request.POST.get("description", "").strip()
    acte_ids_raw = request.POST.get("acte_ids", "")
    acte_noms_raw = request.POST.get("acte_noms", "")

    if not nom:
        if is_ajax:
            return JsonResponse({"ok": False, "error": "Le nom du panel ou du ticket est obligatoire."}, status=400)
        messages.error(request, "Le nom du panel ou du ticket est obligatoire.")
        return redirect("healthcare:prestataire_panels")

    if kind not in (ExamenPanel.KIND_PANEL, ExamenPanel.KIND_TICKET):
        kind = ExamenPanel.KIND_PANEL

    if panel_id:
        try:
            panel = ExamenPanel.objects.get(pk=int(panel_id), organisme=org)
            panel.nom = nom
            panel.kind = kind
            panel.description = description
            panel.save()
        except (ExamenPanel.DoesNotExist, ValueError):
            if is_ajax:
                return JsonResponse({"ok": False, "error": "Panel introuvable."}, status=404)
            panel = ExamenPanel.objects.create(
                organisme=org,
                kind=kind,
                nom=nom,
                description=description,
            )
    else:
        panel = ExamenPanel.objects.create(
            organisme=org,
            kind=kind,
            nom=nom,
            description=description,
        )

    # Attacher les actes sélectionnés
    selected_pas = []
    if acte_ids_raw:
        for x in acte_ids_raw.split(","):
            x = x.strip()
            if not x:
                continue
            if x.isdigit():
                pa = PrestataireActe.objects.filter(pk=int(x), organisme=org).first()
                if pa and pa not in selected_pas:
                    selected_pas.append(pa)
            elif x.startswith("am_") and x[3:].isdigit():
                am_id = int(x[3:])
                am = ActeMedical.objects.filter(pk=am_id, level=3).first()
                if am:
                    pa, _ = PrestataireActe.objects.get_or_create(
                        organisme=org,
                        acte=am,
                        defaults={"price": am.reference_price or 0, "is_available": True}
                    )
                    if pa and pa not in selected_pas:
                        selected_pas.append(pa)

    if acte_noms_raw:
        noms = [n.strip() for n in acte_noms_raw.split("|||") if n.strip()]
        for nom_acte in noms:
            pa = PrestataireActe.objects.filter(organisme=org, acte__name__iexact=nom_acte).first()
            if not pa:
                am = ActeMedical.objects.filter(name__iexact=nom_acte, level=3).first()
                if not am:
                    am = ActeMedical.objects.filter(name__icontains=nom_acte, level=3).first()
                if am:
                    pa, _ = PrestataireActe.objects.get_or_create(
                        organisme=org,
                        acte=am,
                        defaults={"price": am.reference_price or 0, "is_available": True}
                    )
            if pa and pa not in selected_pas:
                selected_pas.append(pa)

    panel.actes.set(selected_pas)

    if is_ajax:
        return JsonResponse({
            "ok": True,
            "id": panel.pk,
            "kind": panel.kind,
            "nom": panel.nom,
            "desc": panel.description,
            "token": panel.token,
            "total_price": float(panel.total_price),
            "actes": [pa.acte.name for pa in panel.actes.all()],
            "url": panel.get_public_path(),
        })

    label_type = "Ticket" if panel.kind == ExamenPanel.KIND_TICKET else "Panel"
    messages.success(request, f"{label_type} « {panel.nom} » enregistré avec succès !")
    return redirect("healthcare:prestataire_panels")


@login_required
def panel_toggle(request, pk):
    """Activer / désactiver un panel ou ticket."""
    if request.method != "POST":
        return redirect("healthcare:prestataire_panels")
    org = _get_user_org(request)
    pk_str = str(pk)
    if pk_str.startswith("pt_"):
        from healthcare.models import PrestationTicket
        pt_pk = int(pk_str.replace("pt_", ""))
        ticket = get_object_or_404(PrestationTicket, pk=pt_pk, organisme=org)
        ticket.is_active = not ticket.is_active
        ticket.save(update_fields=["is_active"])
        if _wants_json(request):
            return JsonResponse({"ok": True, "is_active": ticket.is_active})
        return redirect("healthcare:prestataire_panels")
    panel = get_object_or_404(ExamenPanel, pk=pk, organisme=org)
    panel.is_active = not panel.is_active
    panel.save(update_fields=["is_active"])
    if _wants_json(request):
        return JsonResponse({"ok": True, "is_active": panel.is_active})
    return redirect("healthcare:prestataire_panels")


@login_required
def panel_delete(request, pk):
    """Supprimer un panel ou ticket."""
    if request.method != "POST":
        return redirect("healthcare:prestataire_panels")
    org = _get_user_org(request)
    pk_str = str(pk)
    if pk_str.startswith("pt_"):
        from healthcare.models import PrestationTicket
        pt_pk = int(pk_str.replace("pt_", ""))
        ticket = get_object_or_404(PrestationTicket, pk=pt_pk, organisme=org)
        ticket.delete()
        if _wants_json(request):
            return JsonResponse({"ok": True})
        messages.success(request, "Ticket supprimé.")
        return redirect("healthcare:prestataire_panels")
    panel = get_object_or_404(ExamenPanel, pk=pk, organisme=org)
    panel.delete()
    if _wants_json(request):
        return JsonResponse({"ok": True})
    messages.success(request, "Panel supprimé.")
    return redirect("healthcare:prestataire_panels")


@login_required
def panel_send(request):
    """Envoyer le lien d'un panel dans la messagerie vers des patients sélectionnés."""
    if request.method != "POST":
        return redirect("healthcare:prestataire_panels")

    org = _get_user_org(request)
    if not org:
        return redirect("healthcare:organisme_create")

    panel_url = request.POST.get("panel_url", "").strip()
    panel_nom = request.POST.get("panel_nom", "Panel d'examens").strip()
    panel_token = request.POST.get("panel_token", "").strip()
    if not panel_token and "/t/" in panel_url:
        panel_token = panel_url.split("/t/")[-1].strip("/")
    if panel_token:
        ExamenPanel.objects.filter(token=panel_token, organisme=org).update(is_active=True)
    conv_ids = request.POST.getlist("conv_ids")

    if not conv_ids:
        if _wants_json(request):
            return JsonResponse({"error": "Sélectionnez au moins un patient."}, status=400)
        messages.error(request, "Sélectionnez au moins un patient.")
        return redirect("healthcare:prestataire_panels")

    from messaging.models import Conversation, Message
    sent = 0
    for conv_id in conv_ids:
        try:
            conv = Conversation.objects.get(pk=int(conv_id), prestataire=org.user)
        except (Conversation.DoesNotExist, ValueError):
            continue
        Message.objects.create(
            conversation=conv,
            sender=org.user,
            receiver=conv.patient,
            content=(
                f"🧩 **{panel_nom}**\n"
                f"Voici le lien pour accéder directement aux actes de ce panel :\n"
                f"{panel_url}\n\n"
                f"Cliquez sur le lien pour ajouter les examens à votre panier et obtenir votre devis personnalisé."
            ),
            message_type="internal",
            payload={"type": "panel_link", "panel_url": panel_url, "panel_token": panel_token, "panel_nom": panel_nom},
        )
        # Marquer la conversation comme mise à jour
        conv.save(update_fields=["updated_at"])
        sent += 1

    if _wants_json(request):
        if not sent:
            return JsonResponse({"error": "Aucun message envoyé."}, status=400)
        return JsonResponse({"ok": True, "sent": sent, "message": f"Lien envoyé à {sent} patient(s)."})
    if sent:
        messages.success(request, f"Lien envoyé à {sent} patient{'s' if sent > 1 else ''}.")
    else:
        messages.error(request, "Aucun message envoyé.")
    return redirect("healthcare:prestataire_panels")


def _panel_patient_view(request, panel):
    """
    Affiche la fiche publique d'un ExamenPanel ou pré-sélectionne directement les actes au panier.
    Conforme au brief : le lien /t/<token> pré-coche les actes au panier du patient.
    """
    from cart.models import Cart, CartItem

    wants_json = "application/json" in request.headers.get("Accept", "")
    if not wants_json:
        ExamenPanel.objects.filter(pk=panel.pk).update(views_count=F("views_count") + 1)
        panel.refresh_from_db()

    org = panel.organisme
    actes_pa = list(panel.actes.select_related("acte").all())
    preview_only = request.GET.get("preview") == "1"
    if request.method == "GET" and wants_json:
        return JsonResponse(
            {
                "kind": "panel",
                "token": panel.token,
                "title": panel.nom,
                "description": panel.description or "",
                "price": str(panel.total_price),
                "provider": {
                    "name": org.name,
                    "slug": org.slug,
                    "city": org.city or "",
                },
                "acts": [
                    {
                        "name": pa.acte.name,
                        "price": str(pa.price),
                    }
                    for pa in actes_pa
                ],
                "preview_only": preview_only,
                "login_url": f"/connexion/?next=/t/{panel.token}/",
                "signup_url": f"/inscription/?next=/t/{panel.token}/",
                "cart_url": f"/t/{panel.token}/",
                "contact_url": f"/messaging/demarrer/{org.slug}/",
            }
        )

    # Action d'ajout au panier : sur action explicite (POST action=add_cart ou paramètre ?add=1)
    should_add_to_cart = request.POST.get("action") == "add_cart" or request.GET.get("add") == "1"

    if should_add_to_cart and actes_pa:
        if request.user.is_authenticated and getattr(request.user, "is_patient", False):
            cart = Cart.get_active_cart(request.user)
            for pa in actes_pa:
                CartItem.objects.get_or_create(cart=cart, prestataire_acte=pa)
            messages.success(
                request,
                f"Les {len(actes_pa)} examen{'s' if len(actes_pa) > 1 else ''} de « {panel.nom} » ont été pré-sélectionnés dans votre panier !"
            )
        else:
            # Panier invité en session (clé officielle MedCare)
            guest_cart = request.session.get("medcare_guest_cart_session_v1") or {}
            if not isinstance(guest_cart, dict):
                guest_cart = {}
            for pa in actes_pa:
                guest_cart[str(pa.pk)] = 1
            request.session["medcare_guest_cart_session_v1"] = guest_cart
            request.session.modified = True
            messages.success(
                request,
                f"Les {len(actes_pa)} examen{'s' if len(actes_pa) > 1 else ''} de « {panel.nom} » ont été pré-sélectionnés dans votre panier !"
            )

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "status": "ok",
                "message": "Actes ajoutés au panier !",
                "cart_url": "/cart/",
            })

        return redirect("cart:cart_view")

    from medcare_connect.views import react_app

    return react_app(request)


@login_required
def start_predevis_conversation(request, slug):
    """
    Démarre ou reprend une conversation avec une structure en mode pré-devis.
    Utilisé depuis le bouton « Messagerie » du profil public.
    """
    org = get_object_or_404(OrganismeDeSante, slug=slug, is_active=True)
    prestataire_user = org.user

    if not getattr(request.user, "is_patient", False):
        return redirect("messaging:start_conversation", slug=slug)

    # Reprendre une conversation existante ou en créer une nouvelle
    conv = Conversation.objects.filter(
        patient=request.user,
        prestataire=prestataire_user,
        is_active=True,
    ).first()

    if not conv:
        conv = Conversation.objects.create(
            patient=request.user,
            prestataire=prestataire_user,
            subject=f"Contact — {org.name}",
            kind=Conversation.KIND_GENERAL,
        )
        # Message d'ouverture du fil pré-devis
        Message.objects.create(
            conversation=conv,
            sender=request.user,
            receiver=prestataire_user,
            content=(
                f"Bonjour, je vous contacte depuis votre profil public sur MedCare. "
                f"Je souhaite obtenir des informations ou un pré-devis pour vos examens."
            ),
            payload={"type": "predevis"},
        )

    return redirect("messaging:conversation_detail", pk=conv.pk)
