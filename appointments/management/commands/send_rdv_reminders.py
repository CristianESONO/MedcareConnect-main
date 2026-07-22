"""Rappels RDV configurables (prérequis actes + délais admin).

À exécuter régulièrement (cron toutes les 15–30 min). Pour chaque règle active
(`RdvReminderSchedule`), envoie un rappel aux RDV confirmés dont l'heure de début
tombe dans la fenêtre `[now + délai ± tolérance]`.

Exemples :
    python manage.py send_rdv_reminders
    python manage.py send_rdv_reminders --dry-run
    python manage.py send_rdv_reminders --schedule 2
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from appointments.models import RdvReminderSchedule
from appointments.reminders import due_reminders, send_rdv_reminder


class Command(BaseCommand):
    help = "Envoie les rappels RDV selon les règles configurées en admin."

    def add_arguments(self, parser):
        parser.add_argument(
            "--schedule",
            type=int,
            default=None,
            help="ID d'une règle précise (sinon toutes les règles actives).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="N'envoie rien, affiche seulement les RDV concernés.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        schedule = None
        if options["schedule"]:
            schedule = RdvReminderSchedule.objects.filter(pk=options["schedule"]).first()
            if not schedule:
                self.stderr.write(self.style.ERROR("Règle introuvable."))
                return

        pairs = due_reminders(schedule=schedule)
        active_count = RdvReminderSchedule.objects.filter(is_active=True).count()
        self.stdout.write(
            f"{len(pairs)} rappel(s) à envoyer ({active_count} règle(s) active(s))."
        )

        sent = 0
        for rdv, rule in pairs:
            label = (
                f"{rule.label} · {rdv.reference} · {rdv.organisme.name} · "
                f"{rdv.start:%d/%m %H:%M}"
            )
            if dry_run:
                self.stdout.write(f"  [dry-run] {label}")
                continue
            if send_rdv_reminder(rdv, rule):
                sent += 1
                self.stdout.write(self.style.SUCCESS(f"  rappel envoyé — {label}"))
            else:
                self.stderr.write(f"  échec — {label}")

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"Terminé : {sent} rappel(s) envoyé(s)."))
