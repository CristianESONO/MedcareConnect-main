from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_GET, require_POST

from .geo import parse_lat_lng
from .nominatim import reverse as nominatim_reverse, search_places as nominatim_search


@require_GET
def api_geocode(request):
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": []})
    return JsonResponse({"results": nominatim_search(query, limit=6)})


@require_GET
def api_reverse(request):
    coordinates = parse_lat_lng(request.GET.get("lat"), request.GET.get("lon"))
    if not coordinates:
        return JsonResponse({"result": None}, status=400)
    result = nominatim_reverse(coordinates[0], coordinates[1])
    return JsonResponse({"result": result})


@login_required
@require_POST
def save_search_location(request):
    """Enregistre la position de recherche (session + profil patient)."""
    from users.models import PatientProfile

    coordinates = parse_lat_lng(request.POST.get("lat"), request.POST.get("lng"))
    if not coordinates:
        if request.POST.get("ajax") == "1":
            return JsonResponse({"ok": False, "error": "Position invalide."}, status=400)
        messages.error(request, "Position invalide.")
        return redirect("healthcare:search")

    request.session["search_lat"] = str(coordinates[0])
    request.session["search_lng"] = str(coordinates[1])
    if request.user.is_patient:
        profile, _ = PatientProfile.objects.get_or_create(user=request.user)
        profile.last_known_latitude = coordinates[0]
        profile.last_known_longitude = coordinates[1]
        profile.save(update_fields=["last_known_latitude", "last_known_longitude"])
        message = "Votre position a été enregistrée pour les prochaines recherches."
    else:
        message = "Position mémorisée pour cette session."
    messages.success(request, message)

    if request.POST.get("ajax") == "1":
        return JsonResponse({"ok": True, "message": message})
    next_url = request.POST.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect("healthcare:search")
