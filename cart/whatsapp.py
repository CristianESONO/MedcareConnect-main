"""Outils de génération des liens WhatsApp pré-remplis par structure depuis le panier.

Un *« devis WhatsApp »* est envoyé **par structure** : si le panier contient des actes
de N organismes différents, le patient envoie N messages distincts (un par
prestataire). Ce module groupe les lignes par organisme et prépare un payload
réutilisable côté template (patient connecté ou visiteur).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Iterable
from urllib.parse import quote

from .devis_split import group_cart_items_by_organisme


@dataclass
class WaLine:
    acte_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    delai_display: str = ""


@dataclass
class WaGroup:
    """Tout ce qu'il faut pour rendre un bouton WhatsApp dans le template."""

    organisme_id: int
    organisme_name: str
    whatsapp_digits: str  # numéro chiffres-uniquement (vide si pas de WhatsApp)
    contact_phone: str
    tel_href: str
    address: str
    lines: list[WaLine]
    total: Decimal
    # Si renseignés : message « devis déjà généré » (fiche devis / DevisPart), pas panier.
    devis_reference: str | None = None
    part_reference: str | None = None

    @property
    def has_whatsapp(self) -> bool:
        return bool(self.whatsapp_digits)

    @property
    def items_count(self) -> int:
        return sum(l.quantity for l in self.lines)

    @property
    def wa_url(self) -> str:
        if not self.has_whatsapp:
            return ""
        text = self._build_message()
        return f"https://wa.me/{self.whatsapp_digits}?text={quote(text)}"

    def _build_message(self) -> str:
        if self.devis_reference and self.part_reference:
            return self._build_message_formal_devis()
        bullet_lines = []
        for l in self.lines:
            line = f"• {l.acte_name}"
            if l.quantity > 1:
                line += f" ×{l.quantity}"
            line += f" — {int(l.subtotal):,} XOF".replace(",", " ")
            if l.delai_display:
                line += f" ({l.delai_display})"
            bullet_lines.append(line)
        body = "\n".join(bullet_lines)
        total = f"{int(self.total):,} XOF".replace(",", " ")
        return (
            "Bonjour,\n"
            f"Je souhaite un devis MedCare Connect chez « {self.organisme_name} » pour :\n"
            f"{body}\n"
            f"Total estimé : {total}.\n"
            "Merci de me confirmer la disponibilité et un créneau."
        )

    def _build_message_formal_devis(self) -> str:
        from notifications.dispatcher import render_notification_template_string
        from notifications.models import (
            PATIENT_WA_ME_DEVIS_FORMAL_DEFAULT,
            NotificationSettings,
        )

        ns = NotificationSettings.load()
        template_str = (getattr(ns, "patient_wa_me_message_devis_formal", None) or "").strip()
        ctx = formal_devis_wa_template_context(self)
        if template_str:
            rendered = render_notification_template_string(template_str, ctx).strip()
            if rendered:
                return rendered
        return render_notification_template_string(PATIENT_WA_ME_DEVIS_FORMAL_DEFAULT, ctx).strip()


def formal_devis_wa_template_context(group: "WaGroup") -> dict[str, Any]:
    """Contexte Django Template pour patient_wa_me_message_devis_formal."""
    line_rows: list[dict[str, Any]] = []
    for l in group.lines:
        qty = int(l.quantity)
        subtotal_display = f"{int(l.subtotal):,} XOF".replace(",", " ")
        name = (l.acte_name or "").strip() or "(acte)"
        if qty > 1:
            line_display = f"{name} ×{qty} : {subtotal_display}"
        else:
            line_display = f"{name} : {subtotal_display}"
        line_rows.append(
            {
                "acte_name": name,
                "quantity": qty,
                "subtotal_display": subtotal_display,
                "line_display": line_display,
            }
        )
    total_display = f"{int(group.total):,} XOF".replace(",", " ")
    return {
        "devis": SimpleNamespace(reference=group.devis_reference or ""),
        "devis_part": SimpleNamespace(reference=group.part_reference or ""),
        "org": SimpleNamespace(name=group.organisme_name or ""),
        "lines": line_rows,
        "total_display": total_display,
        "examens_block": "\n".join(r["line_display"] for r in line_rows),
    }


def _group_key(pa) -> int:
    return pa.organisme_id


def wa_group_from_devis_part(devis, part) -> WaGroup:
    """
    Un lien WhatsApp par sous-devis : lignes figées dans part.details, numéro du part.organisme.
    """
    org = part.organisme
    lines: list[WaLine] = []
    total = Decimal(0)
    for row in part.details or []:
        qty = int(row.get("quantity") or 1)
        subtotal = Decimal(str(row.get("subtotal", "0")))
        unit_price = Decimal(str(row.get("unit_price", "0")))
        lines.append(
            WaLine(
                acte_name=(row.get("acte") or "").strip() or "(acte)",
                quantity=qty,
                unit_price=unit_price,
                subtotal=subtotal,
                delai_display="",
            )
        )
        total += subtotal
    if lines and total != part.total_brut:
        total = part.total_brut
    return WaGroup(
        organisme_id=org.pk,
        organisme_name=org.name,
        whatsapp_digits=getattr(org, "whatsapp_digits", "") or "",
        contact_phone=org.contact_phone or "",
        tel_href=getattr(org, "tel_href", "") or "",
        address=org.address or "",
        lines=lines,
        total=part.total_brut,
        devis_reference=devis.reference,
        part_reference=part.reference,
    )


def build_wa_groups_from_devis_parts(devis) -> list[WaGroup]:
    """Liste ordonnée (nom structure) : un WaGroup par DevisPart."""
    parts = (
        devis.parts.all()
        .select_related("organisme")
        .order_by("organisme__name", "pk")
    )
    groups = [wa_group_from_devis_part(devis, p) for p in parts]
    return groups


def _ensure_iterable(rows):
    return rows if rows is not None else []


def build_wa_groups_from_cart_items(items) -> list[WaGroup]:
    """Items = QuerySet `CartItem` (déjà préfetché : prestataire_acte, organisme, acte)."""
    by_org: dict[int, dict] = {}
    for _oid, item_list in group_cart_items_by_organisme(items).items():
        if not item_list:
            continue
        org = item_list[0].prestataire_acte.organisme
        lines: list[WaLine] = []
        total = Decimal(0)
        for item in item_list:
            pa = item.prestataire_acte
            line = WaLine(
                acte_name=pa.acte.name,
                quantity=int(item.quantity or 1),
                unit_price=pa.price,
                subtotal=pa.price * int(item.quantity or 1),
                delai_display=pa.get_delai_display() if pa.delai else "",
            )
            lines.append(line)
            total += line.subtotal
        by_org[org.pk] = {"org": org, "lines": lines, "total": total}
    return _to_groups(by_org)


def build_wa_groups_from_guest_rows(rows: Iterable[dict]) -> list[WaGroup]:
    """Rows = list[{'pa': PrestataireActe, 'qty': int, 'subtotal': Decimal}]."""
    by_org: dict[int, dict] = {}
    for row in _ensure_iterable(rows):
        pa = row["pa"]
        org = pa.organisme
        bucket = by_org.setdefault(_group_key(pa), {
            "org": org,
            "lines": [],
            "total": Decimal(0),
        })
        qty = int(row.get("qty", 1) or 1)
        line = WaLine(
            acte_name=pa.acte.name,
            quantity=qty,
            unit_price=pa.price,
            subtotal=pa.price * qty,
            delai_display=pa.get_delai_display() if pa.delai else "",
        )
        bucket["lines"].append(line)
        bucket["total"] += line.subtotal
    return _to_groups(by_org)


def _to_groups(by_org: dict[int, dict]) -> list[WaGroup]:
    groups: list[WaGroup] = []
    for org_id, b in by_org.items():
        org = b["org"]
        groups.append(WaGroup(
            organisme_id=org.pk,
            organisme_name=org.name,
            whatsapp_digits=getattr(org, "whatsapp_digits", "") or "",
            contact_phone=org.contact_phone or "",
            tel_href=getattr(org, "tel_href", "") or "",
            address=org.address or "",
            lines=b["lines"],
            total=b["total"],
        ))
    groups.sort(key=lambda g: g.organisme_name.lower())
    return groups
