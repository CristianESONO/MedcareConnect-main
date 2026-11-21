import json
import logging
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import views as shared
from .models import ActeMedical, OrganismeDeSante, PrestataireActe

logger = logging.getLogger("healthcare.views")


@shared._require_prestataire
def actes_list(request):
    """
    Catalogue actes — parcours simplifié type démo : cases par pilier (segmentation),
    champ libre « Tarifs & délais », puis tableau récap (filtres) et saisie avancée.
    """
    from django.db import transaction

    ctx = shared._dash_context(request, "actes")
    org = OrganismeDeSante.objects.get(pk=ctx["org"].pk)

    if not org.is_active:
        messages.warning(request, "Votre structure est en attente d'activation. L'offre de soins sera disponible dès validation de votre compte.")
        return redirect("healthcare:prestataire_dashboard")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_domicile":
            from healthcare.prestataire_domicile import handle_domicile_post

            resp = handle_domicile_post(request, org)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return resp
            payload = json.loads(resp.content)
            messages.success(request, payload.get("message") or "Prestations à domicile enregistrées.")
            return redirect("healthcare:actes_list")

        if action == "save_catalogue":
            selectable = set(shared._prestataire_leaf_actes_queryset().values_list("pk", flat=True))
            selected: set[int] = set()
            for x in request.POST.getlist("acte_ids"):
                try:
                    selected.add(int(x))
                except (TypeError, ValueError):
                    continue
            selected &= selectable
            skipped_acte_ids = []
            try:
                with transaction.atomic():
                    org.catalogue_tarifs_delais = (
                        request.POST.get("catalogue_tarifs_delais") or ""
                    ).strip()
                    org.save(update_fields=["catalogue_tarifs_delais", "updated_at"])

                    existing_rows = list(
                        PrestataireActe.objects.select_for_update().filter(organisme=org)
                    )
                    skipped_acte_ids = sorted(
                        {pa.acte_id for pa in existing_rows if pa.acte_id not in selectable}
                    )
                    if skipped_acte_ids:
                        PrestataireActe.objects.filter(
                            organisme=org,
                            acte_id__in=skipped_acte_ids,
                            is_available=True,
                        ).update(is_available=False, updated_at=timezone.now())
                    existing = {
                        pa.acte_id: pa
                        for pa in existing_rows
                        if pa.acte_id in selectable
                    }
                    need_ids = set(existing.keys()) | selected
                    acte_ref = {
                        a.pk: a
                        for a in ActeMedical.objects.filter(pk__in=need_ids)
                    }
                    for aid, pa in existing.items():
                        want = aid in selected
                        new_price = shared._catalog_price_from_post(request.POST, aid, pa.price)
                        new_delai = shared._catalog_delai_from_post(request.POST, aid, pa.delai)
                        if want and (new_price is None or new_price <= 0):
                            raise ValidationError(
                                {
                                    "price": (
                                        f"Le tarif de l’acte « {pa.acte.name} » doit être "
                                        "strictement supérieur à 0 FCFA."
                                    )
                                }
                            )
                        if not want:
                            update_values = {
                                "is_available": False,
                                "delai": new_delai,
                                "updated_at": timezone.now(),
                            }
                            if new_price is not None and new_price > 0:
                                update_values["price"] = new_price
                            PrestataireActe.objects.filter(pk=pa.pk).update(**update_values)
                            continue
                        pa.price = new_price
                        pa.delai = new_delai
                        pa.is_available = want
                        pa.save(
                            update_fields=["price", "delai", "is_available", "updated_at"]
                        )
                    for aid in selected:
                        if aid in existing:
                            continue
                        acte = acte_ref.get(aid)
                        if acte is None:
                            acte = ActeMedical.objects.get(pk=aid)
                        ref = (
                            acte.reference_price
                            if acte.reference_price is not None
                            else Decimal("0")
                        )
                        price = shared._catalog_price_from_post(request.POST, aid, ref)
                        if price is None or price <= 0:
                            raise ValidationError(
                                {
                                    "price": (
                                        f"Le tarif de l’acte « {acte.name} » doit être "
                                        "strictement supérieur à 0 FCFA."
                                    )
                                }
                            )
                        delai = shared._catalog_delai_from_post(request.POST, aid, "")
                        PrestataireActe.objects.create(
                            organisme=org,
                            acte=acte,
                            price=price,
                            delai=delai,
                            is_available=True,
                        )
            except ValidationError as exc:
                logger.exception(
                    "Validation error while saving practitioner catalogue",
                    extra={"organisme_id": org.pk},
                )
                error_message = (
                    "Le catalogue n’a pas été enregistré. Vérifiez que chaque acte est "
                    "sélectionnable et que les tarifs sont supérieurs à 0 FCFA."
                )
                details = "; ".join(exc.messages)
                if details:
                    error_message = f"{error_message} {details}"
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {"ok": False, "message": error_message}, status=400
                    )
                messages.error(request, error_message)
                return redirect("healthcare:actes_list")
            except DatabaseError:
                logger.exception(
                    "Database error while saving practitioner catalogue",
                    extra={"organisme_id": org.pk},
                )
                error_message = (
                    "Une erreur est survenue pendant l’enregistrement. "
                    "Aucune modification n’a été appliquée ; réessayez."
                )
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {"ok": False, "message": error_message}, status=500
                    )
                messages.error(request, error_message)
                return redirect("healthcare:actes_list")

            if skipped_acte_ids:
                logger.warning(
                    "Skipped non-selectable legacy catalogue acts",
                    extra={
                        "organisme_id": org.pk,
                        "acte_ids": skipped_acte_ids,
                    },
                )
                warning_message = (
                    "Catalogue enregistré. Certains anciens actes non sélectionnables "
                    "ont été ignorés."
                )
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {"ok": True, "warning": True, "message": warning_message}
                    )
                messages.warning(request, warning_message)
            else:
                messages.success(
                    request,
                    "Votre offre d’actes et le texte Tarifs & délais ont été enregistrés.",
                )
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"ok": True})
            return redirect("healthcare:actes_list")

    selected_acte_ids = set(
        PrestataireActe.objects.filter(
            organisme=org, is_available=True,
        ).values_list("acte_id", flat=True)
    )

    pa_lookup = {
        pa.acte_id: pa
        for pa in PrestataireActe.objects.filter(organisme=org)
    }
    from healthcare.prestataire_catalogue import (
        applicable_pilier_slugs,
        merge_catalog_blocks,
        prep_display_for_acte,
        prep_panel_payload,
        type_structure_context,
    )

    catalog_raw = shared._prestataire_leaf_actes_catalog_by_pilier()
    catalog_by_pilier = merge_catalog_blocks(catalog_raw, org)
    type_ctx = type_structure_context(org)
    for block in catalog_by_pilier:
        for sg in block.get("subgroups") or []:
            rows = []
            for acte in sg["actes"]:
                pa = pa_lookup.get(acte.pk)
                ref = (
                    acte.reference_price
                    if acte.reference_price is not None
                    else Decimal("0")
                )
                price_val = pa.price if pa is not None else ref
                delai_val = (pa.delai if pa is not None else "") or ""
                rows.append(
                    {
                        "acte": acte,
                        "pa": pa,
                        "price_val": price_val,
                        "delai_val": delai_val,
                        "prep": prep_display_for_acte(acte, pa),
                    }
                )
            sg["rows"] = rows

    prep_data = {}
    for block in catalog_by_pilier:
        pilier_name = block["pilier"].name
        pilier_slug = block["pilier"].slug
        for sg in block.get("subgroups") or []:
            for row in sg.get("rows") or []:
                acte = row["acte"]
                prep_data[str(acte.pk)] = prep_panel_payload(
                    acte,
                    sg["label"],
                    pilier_name,
                    row.get("pa"),
                    org=org,
                    pilier_slug=pilier_slug,
                )

    first_applicable_pilier_id = next(
        (b["pilier"].pk for b in catalog_by_pilier if b.get("applicable")),
        None,
    )
    first_applicable_pilier_slug = next(
        (b["pilier"].slug for b in catalog_by_pilier if b.get("applicable")),
        "",
    )

    # Enrichit chaque bloc avec le nombre d'actes actifs de cette structure
    for block in catalog_by_pilier:
        block_acte_pks = set(
            acte.pk
            for sg in block.get("subgroups") or []
            for acte in sg.get("actes") or []
        )
        block["active_count"] = len(block_acte_pks & selected_acte_ids)

    from healthcare.prestataire_domicile import (
        DOMICILE_DAYS,
        DOMICILE_DELAI_CHOICES,
        domicile_all_actes_active,
        parse_domicile_schedule,
        domicile_subgroups_from_catalog,
        domicile_zones_queryset,
        show_domicile_block,
    )

    from healthcare.forms import PrestataireActeForm
    add_form = PrestataireActeForm(organisme=org)

    applicable_slugs_raw = applicable_pilier_slugs(org)
    domicile_subgroups, domicile_all_acte_ids = domicile_subgroups_from_catalog(catalog_by_pilier)
    ctx.update(
        {
            "org": org,
            "add_form": add_form,
            **shared._presta_acte_form_ui(add_form.fields["acte"].queryset),
            "catalog_by_pilier": catalog_by_pilier,
            "selected_acte_ids": selected_acte_ids,
            "prestataire_delai_choices": PrestataireActe.DELAI_CHOICES,
            "total_count": PrestataireActe.objects.filter(organisme=org, is_available=True).count(),
            "first_applicable_pilier_id": first_applicable_pilier_id,
            "first_applicable_pilier_slug": first_applicable_pilier_slug,
            "show_domicile_block": show_domicile_block(org, applicable_slugs_raw),
            "domicile_zones": domicile_zones_queryset(org),
            "domicile_subgroups": domicile_subgroups,
            "domicile_all_acte_ids": domicile_all_acte_ids,
            "domicile_all_active": domicile_all_actes_active(
                domicile_all_acte_ids, set(selected_acte_ids)
            ),
            "domicile_delai_choices": DOMICILE_DELAI_CHOICES,
            "domicile_days": DOMICILE_DAYS,
            "domicile_schedule_rows": [
                {
                    "code": code,
                    "label": label,
                    **parse_domicile_schedule(org.domicile_plages_horaires).get(code, {
                        "closed": False,
                        "open": "",
                        "close": "",
                    }),
                }
                for code, label in DOMICILE_DAYS
            ],
            "prep_data": prep_data,
            "prep_save_url_tpl": reverse(
                "healthcare:prestataire_acte_prerequisites", args=[0]
            ).replace("/0/", "/ACTE_ID/"),
            "reminder_add_url_tpl": reverse(
                "healthcare:prestataire_acte_reminder_add", args=[999]
            ).replace("999", "ACTE_ID"),
            "reminder_delete_url_tpl": reverse(
                "healthcare:prestataire_acte_reminder_delete", args=[999, 888]
            ).replace("999", "ACTE_ID").replace("888", "SCHEDULE_PK"),
            **type_ctx,
        }
    )
    return render(request, "healthcare/prestataire/actes_list.html", ctx)


@shared._require_prestataire
@require_POST
def actes_import_excel(request):
    """
    Importe ou met à jour les actes du catalogue depuis un fichier Excel (.xlsx, .xls) ou CSV (.csv).
    Gère les soumissions formulaire standard et les requêtes AJAX avec gestion d'erreurs sécurisée.
    """
    is_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )
    try:
        ctx = shared._dash_context(request, "actes")
        org = ctx["org"]
        upload = request.FILES.get("file") or request.FILES.get("catalog_file")

        if not upload:
            msg = "Veuillez sélectionner un fichier Excel (.xlsx) ou CSV (.csv) à importer."
            if is_ajax:
                return JsonResponse({"ok": False, "error": msg}, status=400)
            messages.error(request, msg)
            return redirect("healthcare:actes_list")

        auto_activate = request.POST.get("auto_activate", "1") in ("1", "true", "on", "yes")

        from healthcare.catalog_excel import import_catalog_from_file

        result = import_catalog_from_file(upload, org, auto_activate=auto_activate)

        if not result.get("success"):
            err = result.get("error") or "Erreur lors du traitement du fichier."
            if is_ajax:
                return JsonResponse(
                    {"ok": False, "error": err, "details": result.get("errors", [])},
                    status=400,
                )
            messages.error(request, err)
            return redirect("healthcare:actes_list")

        imp = result.get("imported_count", 0)
        created = result.get("created_count", 0)
        updated = result.get("updated_count", 0)
        errors = result.get("errors", [])
        skipped = result.get("skipped_count", 0)

        summary_msg = (
            f"Catalogue mis à jour avec succès : {imp} acte(s) importé(s) "
            f"({created} nouveau(x), {updated} mis à jour)."
        )
        if skipped:
            summary_msg += f" {skipped} ligne(s) ignorée(s)."

        if is_ajax:
            return JsonResponse(
                {
                    "ok": True,
                    "message": summary_msg,
                    "imported_count": imp,
                    "created_count": created,
                    "updated_count": updated,
                    "skipped_count": skipped,
                    "errors": errors,
                }
            )

        messages.success(request, summary_msg)
        if errors:
            preview = " · ".join(errors[:3])
            if len(errors) > 3:
                preview += f" (+{len(errors) - 3} autres avertissements)"
            messages.warning(request, f"Remarques d'import : {preview}")

        return redirect("healthcare:actes_list")

    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Erreur inattendue dans actes_import_excel : %s", exc)
        err_msg = f"Erreur lors du traitement du fichier : {str(exc)}"
        if is_ajax:
            return JsonResponse(
                {"ok": False, "error": err_msg, "details": [str(exc)]},
                status=400,
            )
        messages.error(request, err_msg)
        return redirect("healthcare:actes_list")


@shared._require_prestataire
@require_GET
def actes_template_excel(request):
    """
    Télécharge le modèle Excel pré-rempli avec les actes applicables pour la structure.
    """
    from django.utils.text import slugify
    from healthcare.catalog_excel import generate_catalog_template_excel

    ctx = shared._dash_context(request, "actes")
    org = ctx["org"]

    excel_buffer = generate_catalog_template_excel(org)
    slug = slugify(org.name) or "structure"
    filename = f"catalogue_actes_{slug}.xlsx"

    response = HttpResponse(
        excel_buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@shared._require_prestataire
@require_POST
def prestataire_acte_prerequisites(request, acte_id):
    """Enregistre consignes / prérequis RDV pour un acte du catalogue structure."""
    from healthcare.forms import PrestataireActePrerequisitesForm

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    acte = get_object_or_404(
        ActeMedical.objects.filter(level=3, is_active=True),
        pk=acte_id,
    )
    pa = PrestataireActe.objects.filter(organisme=org, acte=acte).first()
    if pa is None:
        ref = acte.reference_price if acte.reference_price is not None else Decimal("0")
        fallback_price = ref if ref is not None and ref > 0 else Decimal("1")
        pa = PrestataireActe.objects.create(
            organisme=org,
            acte=acte,
            price=fallback_price,
            delai="",
            is_available=False,
        )
    form = PrestataireActePrerequisitesForm(request.POST, instance=pa)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if form.is_valid():
        obj = form.save(commit=False)
        obj.rdv_prerequisites_active = request.POST.get("rdv_prerequisites_active") == "1"
        # Les consignes peuvent être configurées avant que l'acte ait un tarif
        # public positif. On ne valide donc pas ici le prix du catalogue.
        PrestataireActe.objects.filter(pk=obj.pk).update(
            rdv_prerequisites=obj.rdv_prerequisites,
            rdv_prerequisites_active=obj.rdv_prerequisites_active,
            updated_at=timezone.now(),
        )
        message = (obj.rdv_prerequisites or "").strip() or (acte.rdv_prerequisites or "").strip()
        configured = bool((obj.rdv_prerequisites or "").strip()) or (
            obj.rdv_prerequisites_active and bool((acte.rdv_prerequisites or "").strip())
        )
        if is_ajax:
            return JsonResponse(
                {
                    "ok": True,
                    "configured": configured and bool(message),
                    "active": obj.rdv_prerequisites_active,
                    "message": obj.rdv_prerequisites or "",
                }
            )
        messages.success(request, f"Consignes enregistrées pour « {acte.name} ».")
    else:
        if is_ajax:
            return JsonResponse({"ok": False, "error": "Données invalides."}, status=400)
        messages.error(request, "Impossible d'enregistrer les consignes.")
    next_url = request.POST.get("next") or reverse("healthcare:actes_list")
    return redirect(next_url)


@shared._require_prestataire
@require_POST
def prestataire_acte_reminder_add(request, acte_id):
    """Ajoute un rappel H-N pour un acte (panneau préparation catalogue)."""
    from healthcare.prestataire_prep_reminders import add_hourly_reminder, reminders_for_acte

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    acte = get_object_or_404(
        ActeMedical.objects.filter(level=3, is_active=True),
        pk=acte_id,
    )
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    try:
        hours = int(request.POST.get("hours", ""))
    except (TypeError, ValueError):
        hours = 0
    _, err = add_hourly_reminder(org, acte, hours)
    if err:
        if is_ajax:
            return JsonResponse({"ok": False, "error": err}, status=400)
        messages.error(request, err)
        return redirect(reverse("healthcare:actes_list"))
    if is_ajax:
        return JsonResponse(
            {
                "ok": True,
                "reminders": reminders_for_acte(org, acte.pk),
            }
        )
    messages.success(request, f"Rappel H-{hours} ajouté pour « {acte.name} ».")
    return redirect(reverse("healthcare:actes_list"))


@shared._require_prestataire
@require_POST
def prestataire_acte_reminder_delete(request, acte_id, pk):
    """Supprime un rappel lié à un acte (panneau préparation catalogue)."""
    from healthcare.prestataire_prep_reminders import delete_acte_reminder, reminders_for_acte

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    acte = get_object_or_404(
        ActeMedical.objects.filter(level=3, is_active=True),
        pk=acte_id,
    )
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if not delete_acte_reminder(org, acte.pk, pk):
        if is_ajax:
            return JsonResponse({"ok": False, "error": "Rappel introuvable."}, status=404)
        messages.error(request, "Rappel introuvable.")
        return redirect(reverse("healthcare:actes_list"))
    if is_ajax:
        return JsonResponse(
            {
                "ok": True,
                "reminders": reminders_for_acte(org, acte.pk),
            }
        )
    messages.success(request, "Rappel supprimé.")
    return redirect(reverse("healthcare:actes_list"))


@shared._require_prestataire
def prestataire_rdv_reminder_list(request):
    from appointments.models import RdvReminderSchedule
    from django.db.models import Count

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    schedules = (
        RdvReminderSchedule.objects.filter(organisme=org)
        .prefetch_related("actes")
        .annotate(sent_count=Count("sent_logs"))
        .order_by("order", "-offset_value")
    )
    ctx = shared._dash_context(request, "actes")
    ctx.update({"schedules": schedules, "org": org})
    return render(request, "healthcare/prestataire/rdv_reminder_schedules_list.html", ctx)


@shared._require_prestataire
def prestataire_rdv_reminder_create(request):
    from appointments.models import RdvReminderSchedule
    from healthcare.forms import PrestataireRdvReminderScheduleForm

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    if request.method == "POST":
        form = PrestataireRdvReminderScheduleForm(request.POST, organisme=org)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.organisme = org
            obj.save()
            form.save_m2m()
            messages.success(request, "Règle de rappel créée.")
            return redirect("healthcare:prestataire_rdv_reminder_list")
    else:
        form = PrestataireRdvReminderScheduleForm(organisme=org)
    ctx = shared._dash_context(request, "actes")
    ctx.update({"form": form, "title": "Nouvelle règle de rappel RDV", "org": org})
    return render(request, "healthcare/prestataire/rdv_reminder_schedule_form.html", ctx)


@shared._require_prestataire
def prestataire_rdv_reminder_edit(request, pk):
    from appointments.models import RdvReminderSchedule
    from healthcare.forms import PrestataireRdvReminderScheduleForm

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    schedule = get_object_or_404(RdvReminderSchedule, pk=pk, organisme=org)
    if request.method == "POST":
        form = PrestataireRdvReminderScheduleForm(
            request.POST, instance=schedule, organisme=org
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Règle de rappel mise à jour.")
            return redirect("healthcare:prestataire_rdv_reminder_list")
    else:
        form = PrestataireRdvReminderScheduleForm(instance=schedule, organisme=org)
    ctx = shared._dash_context(request, "actes")
    ctx.update(
        {
            "form": form,
            "title": f"Modifier : {schedule.label}",
            "object": schedule,
            "org": org,
        }
    )
    return render(request, "healthcare/prestataire/rdv_reminder_schedule_form.html", ctx)


@shared._require_prestataire
@require_POST
def prestataire_rdv_reminder_delete(request, pk):
    from appointments.models import RdvReminderSchedule

    org = get_object_or_404(OrganismeDeSante, user=request.user)
    schedule = get_object_or_404(RdvReminderSchedule, pk=pk, organisme=org)
    schedule.delete()
    messages.success(request, "Règle supprimée.")
    return redirect("healthcare:prestataire_rdv_reminder_list")
