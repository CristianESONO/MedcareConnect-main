"""Helpers TypeOrganisme (inscription & profil prestataire)."""

from __future__ import annotations

from django import forms
from django.db.models import QuerySet

from .data.organisme_types import CANONICAL_ORGANISME_TYPES, LEGACY_TYPE_ALIASES
from .models import TypeOrganisme


class TypeOrganismeSelectWidget(forms.Select):
    """Select avec description par option (data-description pour l'UI inscription)."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value:
            try:
                obj = TypeOrganisme.objects.filter(pk=value).values("description").first()
                if obj and obj["description"]:
                    option.setdefault("attrs", {})["data-description"] = obj["description"]
            except (ValueError, TypeError):
                pass
        return option


def sync_organisme_types() -> dict[str, int]:
    """Crée / met à jour les types canoniques. Fusionne les libellés legacy."""
    created = updated = merged = 0
    for legacy, canonical in LEGACY_TYPE_ALIASES.items():
        legacy_row = TypeOrganisme.objects.filter(name=legacy).first()
        if not legacy_row:
            continue
        canonical_row = TypeOrganisme.objects.filter(name=canonical).first()
        if canonical_row and canonical_row.pk != legacy_row.pk:
            legacy_row.organismes.update(type_organisme=canonical_row)
            legacy_row.delete()
        else:
            legacy_row.name = canonical
            legacy_row.save(update_fields=["name"])
        merged += 1

    for order, name, description in CANONICAL_ORGANISME_TYPES:
        row, was_created = TypeOrganisme.objects.get_or_create(
            name=name,
            defaults={"order": order, "description": description},
        )
        if was_created:
            created += 1
            continue
        changed = False
        if row.order != order:
            row.order = order
            changed = True
        if (row.description or "") != description:
            row.description = description
            changed = True
        if changed:
            row.save(update_fields=["order", "description"])
            updated += 1
    return {"created": created, "updated": updated, "merged": merged}


def type_organisme_queryset() -> QuerySet[TypeOrganisme]:
    return TypeOrganisme.objects.all().order_by("order", "name")
