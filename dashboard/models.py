from django.db import models


class ComplianceChecklistSettings(models.Model):
    """
    Singleton (pk=1) : état des cases « fait / à faire » sur la page
    Données & Conformité CDP (`/dashboard/conformite/`).
    Clés = slugs définis dans `COMPLIANCE_CHECKLIST` (views).
    """

    checks = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dict slug → bool (ex. {'hebergement_souverain': true, ...})",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Checklist conformité CDP"
        verbose_name_plural = "Checklist conformité CDP"

    def __str__(self):
        return "Checklist conformité CDP"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
