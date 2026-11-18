"""
Commande de gestion sécurisée pour détecter et fusionner les actes médicaux en doublon.
RÈGLES STRICTES (spec MedCare) :
- --dry-run par défaut (simulation sans modification en base).
- --apply pour exécuter les modifications réelles.
- Pour chaque groupe d'actes doublons (même pilier, libellé normalisé identique ou alias synonyme) :
  * Sélectionne une fiche canonique (fiche ayant le plus d'offres réelles, ou ID le plus ancien).
  * Déplace les PrestataireActe des fiches doublons vers la fiche canonique.
  * Détecte et rapporte les CONFLITS (structure ayant déjà une offre sur la fiche canonique).
  * DÉSACTIVE les actes doublons (is_active=False).
  * NE SUPPRIME JAMAIS AUCUN ACTE NI AUCUNE OFFRE (aucun delete).
"""
from collections import defaultdict
import re
from django.core.management.base import BaseCommand
from django.db import transaction
from healthcare.models import ActeMedical, PrestataireActe
from healthcare.catalog_excel import _normalize_str, MEDICAL_SYNONYMS


def _canonical_key_for_acte(name: str) -> str:
    norm = _normalize_str(name)
    # Vérifier synonymes médicaux connus
    for canon, syn_list in MEDICAL_SYNONYMS.items():
        c_norm = _normalize_str(canon)
        if norm == c_norm:
            return c_norm
        for syn in syn_list:
            s_norm = _normalize_str(syn)
            if norm == s_norm:
                return c_norm
            # Cas inversé (ex: "VS" vs "VITESSE DE SEDIMENTATION")
            words_norm = set(norm.split())
            words_syn = set(s_norm.split())
            if words_syn and words_syn == words_norm:
                return c_norm
    # Normalisation supplémentaire des parenthèses inversées (ex: "VS (Vitesse...)" vs "Vitesse... (VS)")
    clean_paren = re.sub(r"[\(\)\[\]/\-+]", " ", name)
    tokens = sorted(list(_normalize_str(clean_paren).split()))
    return " ".join(tokens)


class Command(BaseCommand):
    help = "Détecte et fusionne les actes en doublon vers une fiche canonique (sans suppression)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="Applique réellement les modifications en base de données. Par défaut en simulation (--dry-run).",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        mode_label = "MODE APPLICATION RÉELLE" if apply_changes else "MODE SIMULATION (--dry-run par défaut)"
        self.stdout.write(self.style.WARNING(f"\n=== FUSION DES ACTES DOUBLONS — {mode_label} ===\n"))

        actes_qs = ActeMedical.objects.filter(is_active=True, level=3).select_related("service_medical_category")
        groups = defaultdict(list)

        for acte in actes_qs:
            pilier_id = acte.service_medical_category_id or 0
            key = (pilier_id, _canonical_key_for_acte(acte.name))
            groups[key].append(acte)

        duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}
        self.stdout.write(f"Nombre de groupes de doublons détectés : {len(duplicate_groups)}\n")

        total_moved = 0
        total_conflicts = 0
        total_deactivated = 0

        with transaction.atomic():
            for (pilier_id, canon_key), actes_list in sorted(duplicate_groups.items(), key=lambda x: str(x[0])):
                # Choisir la fiche canonique : celle avec le plus d'offres PrestataireActe, puis le plus petit ID
                sorted_actes = sorted(
                    actes_list,
                    key=lambda a: (-a.prestataire_actes.count(), a.pk),
                )
                canonical_acte = sorted_actes[0]
                duplicates = sorted_actes[1:]

                self.stdout.write(self.style.MIGRATE_HEADING(
                    f"\nGroupe: Pilier {pilier_id} | Clé: '{canon_key}'"
                ))
                self.stdout.write(
                    f"  -> Canonique retenu : #{canonical_acte.pk} '{canonical_acte.name}' "
                    f"({canonical_acte.prestataire_actes.count()} offres)"
                )

                canonical_org_ids = set(canonical_acte.prestataire_actes.values_list("organisme_id", flat=True))

                for dup in duplicates:
                    dup_offers = list(dup.prestataire_actes.select_related("organisme"))
                    self.stdout.write(
                        f"  -> Doublon : #{dup.pk} '{dup.name}' ({len(dup_offers)} offres)"
                    )

                    for offer in dup_offers:
                        if offer.organisme_id in canonical_org_ids:
                            # Conflit : la structure a déjà une offre sur l'acte canonique
                            existing_offer = canonical_acte.prestataire_actes.get(organisme_id=offer.organisme_id)
                            total_conflicts += 1
                            self.stdout.write(self.style.WARNING(
                                f"     [CONFLIT] Structure '{offer.organisme.name}' a déjà une offre #{existing_offer.pk} "
                                f"({existing_offer.price} F) sur l'acte canonique. Offre #{offer.pk} ({offer.price} F) laissée inchangée."
                            ))
                        else:
                            # Déplacement sécurisé vers l'acte canonique
                            total_moved += 1
                            self.stdout.write(
                                f"     [DÉPLACEMENT] Offre #{offer.pk} ({offer.organisme.name} - {offer.price} F) -> rattachée à #{canonical_acte.pk}"
                            )
                            if apply_changes:
                                offer.acte = canonical_acte
                                offer.save(update_fields=["acte", "updated_at"])
                            canonical_org_ids.add(offer.organisme_id)

                    # Désactivation du doublon (jamais de suppression)
                    total_deactivated += 1
                    self.stdout.write(self.style.NOTICE(f"     [DÉSACTIVATION] Acte doublon #{dup.pk} mis à is_active=False"))
                    if apply_changes:
                        dup.is_active = False
                        dup.save(update_fields=["is_active"])

            if not apply_changes:
                # Annulation automatique de toute transaction si c'était dry-run
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"\n=== BILAN ({mode_label}) ===\n"
            f"- Groupes de doublons : {len(duplicate_groups)}\n"
            f"- Offres à déplacer/déplacées : {total_moved}\n"
            f"- Conflits signalés (offres non écrasées) : {total_conflicts}\n"
            f"- Actes doublons à désactiver/désactivés : {total_deactivated}\n"
        ))
        if not apply_changes:
            self.stdout.write(self.style.WARNING("Rappel : Aucune donnée n'a été modifiée. Lancez avec --apply pour exécuter réellement.\n"))

