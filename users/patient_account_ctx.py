"""Contexte partagé pour les pages « Mon compte » (patients)."""


def patient_account_tab(active: str) -> dict:
    return {"account_active": active}
