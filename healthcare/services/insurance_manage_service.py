"""
InsuranceManageService — Logique métier pour la gestion des assurances prestataire.

Extrait de healthcare/views.py::insurances_manage.
"""
from __future__ import annotations

from collections import defaultdict


class InsuranceManageService:
    """
    Toute la logique de la vue insurances_manage :
      - Ajout d'assurance personnalisée
      - Sauvegarde des cases cochées + tarifs/délais
      - Construction du contexte de rendu
    """

    # ------------------------------------------------------------------ #
    #  Actions POST                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def add_custom_assurance(org, name: str, segment: str, description: str = "") -> str:
        """
        Crée (ou réactive) une assurance personnalisée et la lie à l'organisme.

        Args:
            org: OrganismeDeSante
            name: nom de l'assurance
            segment: segment Assurance.Segment
            description: texte libre

        Returns:
            Nom de l'assurance créée/trouvée (pour le message flash)

        Raises:
            ValueError: si name est vide
        """
        from django.utils.text import slugify
        from healthcare.models import Assurance, PriseEnChargeAssurance

        name = name.strip()
        if not name:
            raise ValueError("Veuillez renseigner le nom de l'assurance.")

        valid_segments = dict(Assurance.Segment.choices)
        if segment not in valid_segments:
            segment = Assurance.Segment.PRIVEE_IARD

        existing = Assurance.objects.filter(name__iexact=name)
        if existing.exists():
            assurance_obj = existing.first()
            if not assurance_obj.is_active:
                assurance_obj.is_active = True
                assurance_obj.save(update_fields=["is_active"])
        else:
            base_slug = slugify(name) or "assurance"
            slug = base_slug
            counter = 1
            while Assurance.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            assurance_obj = Assurance.objects.create(
                name=name,
                slug=slug,
                segment=segment,
                description=description or None,
                is_active=True,
            )

        pec, _ = PriseEnChargeAssurance.objects.get_or_create(
            organisme=org,
            assurance=assurance_obj,
            defaults={"is_active": True},
        )
        if not pec.is_active:
            pec.is_active = True
            pec.save(update_fields=["is_active"])

        return assurance_obj.name

    @staticmethod
    def save_assurances(org, raw_ids: list[str], tarifs_delais: str) -> None:
        """
        Met à jour les assurances cochées et le champ assurances_tarifs_delais.

        Args:
            org: OrganismeDeSante
            raw_ids: liste brute de strings (issus du POST)
            tarifs_delais: texte libre
        """
        from django.db import transaction
        from healthcare.models import Assurance, PriseEnChargeAssurance

        valid = set(Assurance.objects.filter(is_active=True).values_list("pk", flat=True))
        selected: set[int] = set()
        for x in raw_ids:
            try:
                selected.add(int(x))
            except (TypeError, ValueError):
                continue
        selected &= valid

        org.assurances_tarifs_delais = tarifs_delais.strip()
        org.save(update_fields=["assurances_tarifs_delais", "updated_at"])

        with transaction.atomic():
            current_ids = set(
                PriseEnChargeAssurance.objects.filter(organisme=org).values_list(
                    "assurance_id", flat=True
                )
            )
            for aid in current_ids - selected:
                PriseEnChargeAssurance.objects.filter(
                    organisme=org, assurance_id=aid
                ).delete()
            for aid in selected - current_ids:
                PriseEnChargeAssurance.objects.get_or_create(
                    organisme=org,
                    assurance_id=aid,
                    defaults={"is_active": True},
                )

    # ------------------------------------------------------------------ #
    #  Construction du contexte GET                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_context(org, q: str = "", seg_filter: str = "") -> dict:
        """
        Construit le contexte complet pour le template prestataire/insurances.html.

        Args:
            org: OrganismeDeSante
            q: recherche texte
            seg_filter: filtre par segment

        Returns:
            dict prêt pour render()
        """
        from healthcare.models import Assurance, PriseEnChargeAssurance
        from healthcare.insurance_icons import (
            block_hint_for_assurance_segment,
            chip_label_for_assurance_segment,
            filter_icon_for_assurance_segment,
            filter_label_for_assurance_segment,
            icon_for_assurance_segment,
        )
        from django.db.models import Q

        prises_qs = PriseEnChargeAssurance.objects.filter(organisme=org).select_related("assurance")
        selected_assurance_ids = set(
            PriseEnChargeAssurance.objects.filter(organisme=org).values_list(
                "assurance_id", flat=True
            )
        )

        if q:
            prises_qs = prises_qs.filter(
                Q(assurance__name__icontains=q) | Q(assurance__description__icontains=q)
            )
        if seg_filter in dict(Assurance.Segment.choices):
            prises_qs = prises_qs.filter(assurance__segment=seg_filter)
        prises = list(prises_qs.order_by("assurance__segment", "assurance__name"))

        recap_seg_rows = []
        for seg, lbl in Assurance.Segment.choices:
            n = PriseEnChargeAssurance.objects.filter(
                organisme=org, assurance__segment=seg
            ).count()
            if n:
                recap_seg_rows.append(
                    {
                        "segment": seg,
                        "label": lbl,
                        "chip_label": chip_label_for_assurance_segment(seg, lbl),
                        "icon": icon_for_assurance_segment(seg),
                        "n": n,
                    }
                )

        by_seg: dict = defaultdict(list)
        all_active = list(Assurance.objects.filter(is_active=True).order_by("segment", "name"))
        for a in all_active:
            by_seg[a.segment].append(a)
        seg_labels = dict(Assurance.Segment.choices)

        segment_blocks = []
        for seg, long_lbl in Assurance.Segment.choices:
            if seg not in by_seg:
                continue
            icon = icon_for_assurance_segment(seg)
            chip_lbl = chip_label_for_assurance_segment(seg, seg_labels.get(seg, seg))
            block_hint = block_hint_for_assurance_segment(seg)
            lst = by_seg[seg]
            n_sel = sum(1 for x in lst if x.pk in selected_assurance_ids)
            segment_blocks.append(
                {
                    "segment": seg,
                    "chip_icon": icon,
                    "filter_icon": filter_icon_for_assurance_segment(seg),
                    "chip_label": chip_lbl,
                    "filter_label": filter_label_for_assurance_segment(seg, chip_lbl),
                    "block_title": long_lbl,
                    "block_hint": block_hint,
                    "assurances": lst,
                    "n_selected": n_sel,
                    "n_total": len(lst),
                }
            )

        return {
            "org": org,
            "prises": prises,
            "segment_blocks": segment_blocks,
            "insurance_catalog_total": len(all_active),
            "insurance_selected_count": len(selected_assurance_ids),
            "selected_assurance_ids": selected_assurance_ids,
            "q": q,
            "seg_filter": seg_filter,
            "recap_seg_rows": recap_seg_rows,
            "segment_choices": Assurance.Segment.choices,
        }
