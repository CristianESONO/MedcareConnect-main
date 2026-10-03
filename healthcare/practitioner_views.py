from decimal import Decimal
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.db.models import F

from healthcare.models import (
    OrganismeDeSante,
    ActeMedical,
    ServiceMedical,
    PrestationTicket,
    PractitionerAffiliation,
    PrestataireActe,
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


# ==============================================================================
# ÉTAPE 2 : TYPE D'ÉTABLISSEMENT & DÉCOUPLAGE DES PILIERS (STRUCTURE)
# ==============================================================================

@login_required
def prestataire_type_etablissement(request):
    org = _get_user_org(request)
    if not org:
        messages.error(request, "Veuillez d'abord créer votre établissement.")
        return redirect("healthcare:organisme_create")

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
    return render(request, "healthcare/prestataire/type_etablissement.html", context)



# ==============================================================================
# ÉTAPE 4 : TICKETS DE PRESTATION (ESPACE PRATICIEN INDÉPENDANT)
# ==============================================================================

@login_required
def prestataire_tickets(request):
    org = _get_user_org(request)
    if not org:
        return redirect("healthcare:organisme_create")

    tickets = PrestationTicket.objects.filter(organisme=org).order_by("-created_at")
    my_actes = PrestataireActe.objects.filter(organisme=org, is_available=True).select_related("acte")

    context = {
        "org": org,
        "dash_active": "tickets",
        "tickets": tickets,
        "my_actes": my_actes,
        "base_url": request.build_absolute_uri("/").rstrip("/"),
    }
    return render(request, "healthcare/prestataire/tickets_list.html", context)


@login_required
def prestataire_ticket_create(request):
    org = _get_user_org(request)
    if not org:
        return redirect("healthcare:organisme_create")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        price_raw = request.POST.get("price", "0").replace(" ", "").replace("F", "").replace("CFA", "")
        try:
            price = Decimal(price_raw)
        except Exception:
            price = Decimal("10000")

        mode = request.POST.get("mode", "domicile")
        zone = request.POST.get("zone", "Dakar").strip()
        disponibilite = request.POST.get("disponibilite", "Créneaux sur demande").strip()
        acte_id = request.POST.get("acte_id")

        acte = None
        if acte_id:
            acte = ActeMedical.objects.filter(id=acte_id).first()

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
    messages.success(request, f"Le ticket « {title} » a été supprimé.")
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
    return render(request, "healthcare/prestataire/acces.html", context)


@login_required
def prestataire_affiliation_create(request):
    """Praticien → demande d'accès à une structure."""
    org = _get_user_org(request)
    if not org:
        return redirect("healthcare:organisme_create")

    if request.method == "POST":
        structure_id = request.POST.get("structure_id")
        structure = get_object_or_404(OrganismeDeSante, id=structure_id, account_nature="structure")

        role_title = request.POST.get("role_title", "").strip() or "Praticien consultant"
        days_raw = request.POST.getlist("days")

        PractitionerAffiliation.objects.get_or_create(
            praticien=org,
            structure=structure,
            defaults={
                "role_title": role_title,
                "days_schedule": days_raw,
                "status": "pending",
                "initiated_by": "praticien",
            },
        )
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
            messages.warning(request, f"{praticien.name} est déjà rattaché ou a déjà une demande en cours.")
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
    messages.success(request, f"Vous avez rejoint {aff.structure.name} avec succès !")
    return redirect("healthcare:prestataire_acces")


@login_required
def prestataire_affiliation_approve(request, pk):
    """Structure valide une demande d'un praticien."""
    org = _get_user_org(request)
    aff = get_object_or_404(PractitionerAffiliation, pk=pk, structure=org)
    aff.status = "approved"
    aff.save(update_fields=["status", "updated_at"])
    messages.success(request, f"L'accès pour le praticien {aff.praticien.name} a été validé avec succès.")
    return redirect("healthcare:prestataire_acces")


@login_required
def prestataire_affiliation_delete(request, pk):
    org = _get_user_org(request)
    aff = get_object_or_404(PractitionerAffiliation, pk=pk)
    if aff.praticien != org and aff.structure != org:
        raise Http404("Non autorisé")
    aff.delete()
    messages.info(request, "Rattachement supprimé.")
    return redirect("healthcare:prestataire_acces")


# ==============================================================================
# ÉTAPE 5 : VUE PATIENT DU TICKET DIRECT (/t/<identifiant>)
# ==============================================================================

def patient_ticket_view(request, token):
    ticket = get_object_or_404(PrestationTicket, identifiant=token, is_active=True)
    PrestationTicket.objects.filter(pk=ticket.pk).update(views_count=F("views_count") + 1)
    ticket.refresh_from_db()

    praticien = ticket.organisme
    prestataire_user = praticien.user

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
            return JsonResponse({"status": "ok", "message": "Prestation ajoutée au panier !"})

        messages.success(request, f"« {ticket.title} » a été ajouté à votre panier.")
        return redirect(request.path)

    # Demande de devis / connexion depuis la page info visiteur
    if request.method == "POST" and request.POST.get("action") == "request_devis":
        if not request.user.is_authenticated:
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
            return redirect("messaging:conversation_detail", pk=conv.pk)

    # ──────────────────────────────────────────────────────────────────────────
    # Page d'information — visiteur non connecté (ou praticien sans compte user)
    # ──────────────────────────────────────────────────────────────────────────
    context = {
        "ticket": ticket,
        "praticien": praticien,
        "account_page_title": f"{ticket.title} · {praticien.name}",
        "login_url": f"/connexion/?next=/t/{token}/",
        "signup_url": f"/inscription/?next=/t/{token}/",
    }
    return render(request, "healthcare/patient_ticket_public.html", context)


def patient_mobile_view(request):
    """Interface mobile patient MedCare (alignée sur DEMO_PATIENT_MOBILE_TICKET)."""
    latest_ticket = (
        PrestationTicket.objects.filter(is_active=True)
        .select_related("organisme", "acte")
        .order_by("-created_at")
        .first()
    )
    context = {
        "ticket": latest_ticket,
        "praticien": latest_ticket.organisme if latest_ticket else None,
        "auto_open_ticket": False,
        "is_mobile_view": True,
    }
    return render(request, "healthcare/patient_mobile.html", context)


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
        # Structure en dict {jour: [heures]}
        schedule: dict[str, list[str]] = {}
        for slot in raw_slots:
            if "_" in slot:
                day, hour = slot.split("_", 1)
                schedule.setdefault(day, []).append(hour)

        aff.days_schedule = [
            f"{day} : {', '.join(sorted(hours))}"
            for day, hours in sorted(
                schedule.items(),
                key=lambda x: DAYS_FR.index(x[0]) if x[0] in DAYS_FR else 99,
            )
        ]
        aff.save(update_fields=["days_schedule", "updated_at"])
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
    return render(request, "healthcare/prestataire/agenda_praticien.html", context)


# ==============================================================================
# FICHE PUBLIQUE PRATICIEN (Étape 6 — visibilité via acte proposé)
# ==============================================================================

def praticien_public_detail(request, slug):
    """
    Fiche publique d'un praticien indépendant.
    Accessible via /sante/praticien/<slug>/ et apparaît dans les résultats
    de recherche si un acte correspondant est proposé.
    """
    from django.utils.text import slugify as dj_slugify

    # Recherche directe par slug ou pk
    praticien = OrganismeDeSante.objects.filter(slug=slug, is_active=True).first()
    if not praticien and slug.isdigit():
        praticien = OrganismeDeSante.objects.filter(pk=int(slug), is_active=True).first()

    if not praticien:
        all_praticiens = OrganismeDeSante.objects.filter(is_active=True)
        for p in all_praticiens:
            if p.is_praticien and (dj_slugify(p.name) == slug or p.slug == slug):
                praticien = p
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
    return render(request, "healthcare/praticien_public.html", context)


