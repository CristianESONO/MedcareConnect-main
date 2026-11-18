"""Utilitaires healthcare (UI, regroupements)."""

from healthcare.models import Assurance


def assurances_grouped_for_select(exclude_ids=None):
    """
    Assurances actives groupées par segment (ordre document ASSURANCES_SENEGAL.pdf).
    Retourne une liste de tuples (libellé_segment, liste d'objets Assurance).

    exclude_ids : PK à exclure (ex. déjà liées au prestataire sur l'écran PEC).
    """
    exclude_ids = exclude_ids or ()
    order = [
        Assurance.Segment.PRIVEE_IARD,
        Assurance.Segment.DIGITALE,
        Assurance.Segment.REGIME_PUBLIC,
        Assurance.Segment.MUTUELLE,
        Assurance.Segment.PROGRAMME,
    ]
    out = []
    for seg in order:
        qs = list(
            Assurance.objects.filter(is_active=True, segment=seg)
            .exclude(pk__in=exclude_ids)
            .order_by("name")
        )
        if qs:
            out.append((Assurance.Segment(seg).label, qs))
    return out
