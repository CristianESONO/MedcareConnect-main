from django.test import SimpleTestCase

from healthcare.opening_hours_display import (
    format_time_fr,
    group_opening_hours,
    profil_hours_meta,
    profil_hours_meta_chunks,
)


class OpeningHoursDisplayTests(SimpleTestCase):
    def _week(self, ven_close="17:00"):
        return [
            {"day": "Lundi", "open": "08:00", "close": "18:00", "closed": False},
            {"day": "Mardi", "open": "08:00", "close": "18:00", "closed": False},
            {"day": "Mercredi", "open": "08:00", "close": "18:00", "closed": False},
            {"day": "Jeudi", "open": "08:00", "close": "18:00", "closed": False},
            {"day": "Vendredi", "open": "08:00", "close": ven_close, "closed": False},
            {"day": "Samedi", "closed": True},
            {"day": "Dimanche", "closed": True},
        ]

    def test_format_time_fr(self):
        self.assertEqual(format_time_fr("08:00"), "8h")
        self.assertEqual(format_time_fr("07:30"), "7h30")

    def test_groups_consecutive_days(self):
        groups = group_opening_hours(self._week())
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["start"], "Lun")
        self.assertEqual(groups[0]["end"], "Jeu")
        self.assertEqual(groups[1]["start"], "Ven")
        self.assertEqual(groups[1]["end"], "Ven")

    def test_profil_hours_meta_compact(self):
        meta = profil_hours_meta(self._week())
        self.assertEqual(meta, "Lun–Jeu 8h–18h · Ven 8h–17h")
        self.assertEqual(
            profil_hours_meta_chunks(self._week()),
            ["Lun–Jeu 8h–18h", "Ven 8h–17h"],
        )

    def test_same_hours_all_week(self):
        week = [
            {"day": day, "open": "08:00", "close": "18:00", "closed": False}
            for day in (
                "Lundi",
                "Mardi",
                "Mercredi",
                "Jeudi",
                "Vendredi",
                "Samedi",
                "Dimanche",
            )
        ]
        self.assertEqual(profil_hours_meta(week), "Lun–Dim 8h–18h")
