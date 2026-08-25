"""
Module d'Agent IA pour la recherche intelligente de soins sur la plateforme MedCare.
Analyse les requêtes des patients en langage naturel et génère des réponses conversationnelles
avec des cartes de résultats interactives liées à 'Trouver un service'.
"""
import re
from django.db.models import Q
from django.urls import reverse
from urllib.parse import urlencode

from .models import ActeMedical, ServiceMedical, OrganismeDeSante


def process_ai_patient_request(user_prompt: str) -> dict:
    """
    Traite la demande du patient et retourne une réponse d'Agent IA enrichie de résultats.
    """
    prompt = (user_prompt or "").strip()
    if not prompt:
        return {
            "answer": "Bonjour ! Je suis l'Agent IA MedCare. Comment puis-je vous aider aujourd'hui ? Vous pouvez me demander un acte médical, un laboratoire, une imagerie ou une localisation.",
            "results": [],
            "suggested_chips": [
                "🔬 Échographie abdominale à Dakar",
                "🩸 Prise de sang & Bilan sanguin",
                "🏥 Laboratoire ouvert à Mermoz",
                "🚑 Service d'ambulance 24h/7j"
            ]
        }

    prompt_lower = prompt.lower()
    results = []
    
    # 1. Recherche d'actes médicaux correspondants
    matched_actes = (
        ActeMedical.objects.filter(is_active=True)
        .filter(Q(name__icontains=prompt) | Q(code__icontains=prompt) | Q(service_medical_category__name__icontains=prompt))
        .select_related("service_medical_category")
        .order_by("name")[:5]
    )

    if not matched_actes:
        # Recherche par mots clés individuels
        words = [w for w in re.split(r'\s+', prompt_lower) if len(w) >= 3]
        if words:
            q_obj = Q()
            for word in words:
                q_obj |= Q(name__icontains=word) | Q(service_medical_category__name__icontains=word)
            matched_actes = (
                ActeMedical.objects.filter(is_active=True)
                .filter(q_obj)
                .select_related("service_medical_category")
                .order_by("name")[:5]
            )

    # 2. Recherche de familles de services
    matched_services = (
        ServiceMedical.objects.filter(is_active=True)
        .filter(Q(name__icontains=prompt) | Q(description__icontains=prompt))
        .order_by("order")[:3]
    )

    # 3. Recherche de structures (Organismes)
    matched_orgs = (
        OrganismeDeSante.objects.filter(is_active=True)
        .filter(Q(name__icontains=prompt) | Q(city__icontains=prompt) | Q(quartier__icontains=prompt))
        .select_related("type_organisme")
        .order_by("-is_verified", "name")[:4]
    )

    # Construction des cartes de résultats
    search_base_url = reverse("healthcare:search")

    for acte in matched_actes:
        search_url = f"{search_base_url}?acte={acte.pk}&sort=price_asc"
        results.append({
            "type": "acte",
            "title": acte.name,
            "category": acte.service_medical_category.name if acte.service_medical_category else "Acte médical",
            "detail": "Disponible auprès des laboratoires & centres partenaires",
            "url": search_url,
            "action_text": "Trouver au meilleur prix",
            "badge": "Examen"
        })

    for service in matched_services:
        search_url = f"{search_base_url}?service={service.pk}&sort=price_asc"
        results.append({
            "type": "service",
            "title": service.name,
            "category": "Famille de soins",
            "detail": service.description or "Comparer les établissements proposant ce service",
            "url": search_url,
            "action_text": "Parcourir la catégorie",
            "badge": "Service"
        })

    for org in matched_orgs:
        search_url = f"{search_base_url}?q={org.name}"
        type_name = org.type_organisme.name if org.type_organisme else "Établissement"
        loc = f"{org.quartier}, {org.city}" if org.quartier else org.city
        results.append({
            "type": "structure",
            "title": org.name,
            "category": f"{type_name} · {loc}",
            "detail": "Prise de rendez-vous en ligne & Tarifs partenaires",
            "url": search_url,
            "action_text": "Voir la fiche & Tarifs",
            "badge": "Établissement"
        })

    # Génération de la réponse conversationnelle de l'Agent IA
    if results:
        count_actes = len(matched_actes)
        count_orgs = len(matched_orgs)
        
        answer_parts = []
        answer_parts.append(f"J'ai analysé votre demande « **{prompt}** » sur toute la plateforme MedCare.")
        
        if count_actes > 0:
            answer_parts.append(f"J'ai identifié **{count_actes} examen(s)** correspondant à votre recherche.")
        if count_orgs > 0:
            answer_parts.append(f"J'ai également trouvé **{count_orgs} établissement(s)** partenaire(s).")
            
        answer_parts.append("Voici les meilleurs résultats disponibles pour comparer les prix, la couverture assurance et réserver :")
        answer = " ".join(answer_parts)
    else:
        answer = f"Je n'ai pas trouvé de résultat exact pour « **{prompt}** ». Cependant, vous pouvez explorer la recherche globale ou préciser votre demande avec un type d'examen (ex: *Échographie*, *Prise de sang*, *Scanner*) ou une ville."
        # Résultats de secours (services populaires)
        pop_services = ServiceMedical.objects.filter(is_active=True).order_by("order")[:3]
        for service in pop_services:
            search_url = f"{search_base_url}?service={service.pk}"
            results.append({
                "type": "service",
                "title": service.name,
                "category": "Service populaire",
                "detail": "Rechercher des prestations et comparer les tarifs",
                "url": search_url,
                "action_text": "Explorer ce service",
                "badge": "Recommandé"
            })

    return {
        "answer": answer,
        "results": results[:6], # Limiter à 6 cartes maximum pour garder une interface fluide
        "suggested_chips": [
            "🔬 Échographie",
            "🩸 Biologie médicale",
            "📻 Radiologie & Scanner",
            "🚑 Urgence Ambulance"
        ]
    }
