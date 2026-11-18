"""Backfill des fils de discussion (devis + RDV) et synchronisation des liens."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Count

from appointments.models import RendezVous
from cart.models import DevisPart
from messaging.models import Conversation
from messaging.thread import (
    ensure_devis_thread,
    fix_notification_links_for_conv,
    sync_rdv_thread,
    thread_url,
)


class Command(BaseCommand):
    help = (
        "Crée ou complète les fils messagerie pour tous les DevisPart / RDV existants "
        "et met à jour les liens de notifications."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche ce qui serait fait sans écrire en base.",
        )
        parser.add_argument(
            "--skip-notifs",
            action="store_true",
            help="Ne pas mettre à jour les liens des notifications.",
        )
        parser.add_argument(
            "--force-resync-rdv",
            action="store_true",
            help="Re-synchronise les messages RDV même si des marqueurs existent déjà.",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        skip_notifs = options["skip_notifs"]
        force_rdv = options["force_resync_rdv"]

        parts = (
            DevisPart.objects.select_related("devis__patient", "organisme__user")
            .order_by("pk")
        )
        rdvs = (
            RendezVous.objects.filter(devis_part__isnull=False)
            .select_related("devis_part", "organisme", "patient")
            .order_by("created_at")
        )

        stats = {
            "parts_total": parts.count(),
            "threads_created": 0,
            "threads_seeded": 0,
            "threads_existing": 0,
            "rdv_synced": 0,
            "notifs_updated": 0,
            "errors": 0,
        }

        self.stdout.write(f"DevisPart à traiter : {stats['parts_total']}")
        self.stdout.write(f"RDV à synchroniser : {rdvs.count()}")

        if dry:
            self.stdout.write(self.style.WARNING("Mode dry-run — aucune écriture."))

        for part in parts:
            try:
                existing = Conversation.objects.filter(devis_part=part).first()
                if dry:
                    if not existing:
                        stats["threads_created"] += 1
                        self.stdout.write(f"  [dry] fil à créer · {part.reference} · {part.organisme.name}")
                    elif not existing.messages.exists():
                        stats["threads_seeded"] += 1
                        self.stdout.write(f"  [dry] fil à peupler · {part.reference}")
                    else:
                        stats["threads_existing"] += 1
                    continue

                conv, seeded = ensure_devis_thread(part)
                if not existing:
                    stats["threads_created"] += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Fil créé #{conv.pk} · {part.reference} · {part.organisme.name}"
                        )
                    )
                elif seeded:
                    stats["threads_seeded"] += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Fil peuplé #{conv.pk} · {part.reference}"
                        )
                    )
                else:
                    stats["threads_existing"] += 1
            except Exception as exc:
                stats["errors"] += 1
                self.stdout.write(
                    self.style.ERROR(f"  Erreur DevisPart {part.reference}: {exc}")
                )

        for rdv in rdvs:
            try:
                if dry:
                    conv = Conversation.objects.filter(devis_part=rdv.devis_part_id).first()
                    if not conv:
                        self.stdout.write(f"  [dry] RDV {rdv.reference} — fil manquant (sera créé via part)")
                    stats["rdv_synced"] += 1
                    continue

                if force_rdv:
                    conv = Conversation.objects.filter(devis_part=rdv.devis_part_id).first()
                    if conv:
                        conv.messages.filter(payload__rdv_ref=rdv.reference).delete()

                sync_rdv_thread(rdv, notify=False)
                stats["rdv_synced"] += 1
            except Exception as exc:
                stats["errors"] += 1
                self.stdout.write(
                    self.style.ERROR(f"  Erreur RDV {rdv.reference}: {exc}")
                )

        if not skip_notifs and not dry:
            for conv in Conversation.objects.filter(devis_part__isnull=False).iterator():
                try:
                    n = fix_notification_links_for_conv(conv)
                    stats["notifs_updated"] += n
                except Exception as exc:
                    stats["errors"] += 1
                    self.stdout.write(
                        self.style.ERROR(f"  Erreur notifs conv #{conv.pk}: {exc}")
                    )

        # Fils orphelins sans messages
        empty = (
            Conversation.objects.filter(devis_part__isnull=False)
            .annotate(n=Count("messages"))
            .filter(n=0)
            .count()
        )

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Résumé backfill"))
        self.stdout.write(f"  Fils créés        : {stats['threads_created']}")
        self.stdout.write(f"  Fils peuplés      : {stats['threads_seeded']}")
        self.stdout.write(f"  Fils déjà OK      : {stats['threads_existing']}")
        self.stdout.write(f"  RDV synchronisés  : {stats['rdv_synced']}")
        self.stdout.write(f"  Notifs MAJ        : {stats['notifs_updated']}")
        self.stdout.write(f"  Fils vides restants: {empty}")
        self.stdout.write(f"  Erreurs           : {stats['errors']}")

        total_convs = Conversation.objects.filter(devis_part__isnull=False).count()
        self.stdout.write(f"  Total fils devis  : {total_convs}")

        if not dry and total_convs:
            sample = Conversation.objects.filter(devis_part__isnull=False).first()
            self.stdout.write(f"  Exemple URL       : {thread_url(sample)}")

        if stats["errors"]:
            self.stdout.write(self.style.ERROR("Terminé avec erreurs."))
        else:
            self.stdout.write(self.style.SUCCESS("Backfill terminé avec succès."))
