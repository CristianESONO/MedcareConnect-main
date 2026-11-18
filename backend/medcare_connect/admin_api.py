from datetime import date, datetime
from decimal import Decimal

from django import forms
from django.contrib import admin
from django.contrib.auth import authenticate, login, logout
from django.contrib.admin.utils import label_for_field, lookup_field
from django.core.paginator import Paginator
from django.db import models, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods, require_POST

from .views import react_app


def _admin_user(request):
    return bool(
        request.user.is_authenticated
        and request.user.is_active
        and (
            request.user.is_staff
            or request.user.is_superuser
            or getattr(request.user, "is_admin_user", False)
        )
    )


def _admin_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentification requise."}, status=401)
    if not _admin_user(request):
        return JsonResponse({"error": "Accès réservé aux administrateurs."}, status=403)
    return None


def _registered_model(app_label, model_name):
    for model, model_admin in admin.site._registry.items():
        if model._meta.app_label == app_label and model._meta.model_name == model_name:
            return model, model_admin
    return None, None


def _has_model_permission(request, model_admin, permission, obj=None):
    if request.user.is_superuser or getattr(request.user, "is_admin_user", False):
        return True
    return getattr(model_admin, f"has_{permission}_permission")(request, obj)


def _serialize_value(value):
    if value is None:
        return ""
    if isinstance(value, models.Model):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value)
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _list_value(model_admin, field_name, obj):
    try:
        _field, _attr, value = lookup_field(field_name, obj, model_admin)
    except (AttributeError, ValueError):
        return ""
    if callable(value):
        value = value()
    return _serialize_value(value)


def _choice_list(choices):
    result = []
    for value, label in choices:
        if isinstance(label, (list, tuple)):
            result.extend(_choice_list(label))
        else:
            result.append({"value": str(value), "label": str(label)})
    return result


def _form_schema(model_admin, request, obj=None):
    form_class = model_admin.get_form(request, obj)
    form = form_class(instance=obj)
    schema = []
    for name, field in form.fields.items():
        if name == "password":
            continue
        bound_value = form[name].value()
        if isinstance(bound_value, models.Model):
            bound_value = bound_value.pk
        elif isinstance(bound_value, (list, tuple)):
            bound_value = [
                item.pk if isinstance(item, models.Model) else item
                for item in bound_value
            ]

        if isinstance(field, forms.BooleanField):
            field_type = "boolean"
        elif isinstance(field, forms.ModelMultipleChoiceField):
            field_type = "multiselect"
        elif isinstance(field, forms.ModelChoiceField):
            field_type = "select"
        elif isinstance(field, forms.MultipleChoiceField):
            field_type = "multiselect"
        elif isinstance(field, forms.ChoiceField):
            field_type = "select"
        elif isinstance(field, forms.DateTimeField):
            field_type = "datetime"
        elif isinstance(field, forms.DateField):
            field_type = "date"
        elif isinstance(field, forms.JSONField):
            field_type = "json"
        elif isinstance(field, forms.FileField):
            field_type = "file"
        elif isinstance(field.widget, forms.Textarea):
            field_type = "textarea"
        elif isinstance(field.widget, forms.PasswordInput):
            field_type = "password"
        else:
            field_type = "text"

        choices = []
        if isinstance(field, forms.ModelMultipleChoiceField):
            choices = [
                {"value": str(item.pk), "label": str(item)}
                for item in field.queryset.all()
            ]
        elif isinstance(field, forms.ModelChoiceField):
            choices = [
                {"value": str(item.pk), "label": str(item)}
                for item in field.queryset.all()
            ]
        elif getattr(field, "choices", None):
            choices = _choice_list(field.choices)

        schema.append(
            {
                "name": name,
                "label": str(field.label or name.replace("_", " ").capitalize()),
                "type": field_type,
                "required": field.required,
                "help_text": str(field.help_text or ""),
                "value": _serialize_value(bound_value),
                "values": (
                    [str(value) for value in bound_value]
                    if field_type == "multiselect" and isinstance(bound_value, (list, tuple))
                    else []
                ),
                "choices": choices,
            }
        )
    return schema


def _form_errors(form):
    return {
        field: [str(error) for error in errors]
        for field, errors in form.errors.items()
    }


def _save_form(request, model, model_admin, obj=None):
    form_class = model_admin.get_form(request, obj)
    form = form_class(request.POST, request.FILES, instance=obj)
    if not form.is_valid():
        return None, form
    change = obj is not None
    with transaction.atomic():
        saved = model_admin.save_form(request, form, change)
        model_admin.save_model(request, saved, form, change)
        model_admin.save_related(request, form, [], change)
        if change:
            model_admin.log_change(request, saved, "Updated in React admin")
        else:
            model_admin.log_addition(request, saved, "Created in React admin")
    return saved, form


@require_http_methods(["GET", "POST"])
def admin_login_api(request):
    if request.method == "GET":
        if _admin_user(request):
            return JsonResponse({"ok": True, "username": request.user.get_username()})
        return JsonResponse({"ok": False}, status=401)

    username = (request.POST.get("username") or "").strip()
    password = request.POST.get("password") or ""
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active or not (
        user.is_staff or user.is_superuser or getattr(user, "is_admin_user", False)
    ):
        return JsonResponse({"error": "Identifiants administrateur invalides."}, status=401)
    login(request, user)
    return JsonResponse({"ok": True, "username": user.get_username()})


@require_POST
def admin_logout_api(request):
    if not _admin_user(request):
        return JsonResponse({"error": "Accès réservé aux administrateurs."}, status=403)
    logout(request)
    return JsonResponse({"ok": True})


@require_http_methods(["GET"])
def admin_models_api(request):
    denied = _admin_required(request)
    if denied:
        return denied
    models_list = []
    for model, model_admin in admin.site._registry.items():
        if not (
            _has_model_permission(request, model_admin, "view")
            or _has_model_permission(request, model_admin, "change")
            or _has_model_permission(request, model_admin, "add")
        ):
            continue
        opts = model._meta
        models_list.append(
            {
                "app_label": opts.app_label,
                "model_name": opts.model_name,
                "label": str(opts.verbose_name_plural).capitalize(),
                "can_add": _has_model_permission(request, model_admin, "add"),
                "can_change": _has_model_permission(request, model_admin, "change"),
                "can_delete": _has_model_permission(request, model_admin, "delete"),
            }
        )
    models_list.sort(key=lambda item: (item["app_label"], item["label"].lower()))
    return JsonResponse({"models": models_list})


@require_http_methods(["GET", "POST"])
def admin_model_collection_api(request, app_label, model_name):
    denied = _admin_required(request)
    if denied:
        return denied
    model, model_admin = _registered_model(app_label, model_name)
    if model is None:
        return JsonResponse({"error": "Modèle introuvable."}, status=404)

    if request.method == "POST":
        if not _has_model_permission(request, model_admin, "add"):
            return JsonResponse({"error": "Création interdite."}, status=403)
        saved, form = _save_form(request, model, model_admin)
        if saved is None:
            return JsonResponse({"errors": _form_errors(form)}, status=400)
        return JsonResponse({"ok": True, "pk": str(saved.pk)})

    if not (
        _has_model_permission(request, model_admin, "view")
        or _has_model_permission(request, model_admin, "change")
    ):
        return JsonResponse({"error": "Consultation interdite."}, status=403)

    queryset = model_admin.get_queryset(request)
    search = (request.GET.get("q") or "").strip()
    if search:
        query = models.Q()
        for raw_field in model_admin.get_search_fields(request):
            lookup = "icontains"
            field_name = raw_field
            if raw_field.startswith("^"):
                lookup, field_name = "istartswith", raw_field[1:]
            elif raw_field.startswith("="):
                lookup, field_name = "iexact", raw_field[1:]
            query |= models.Q(**{f"{field_name}__{lookup}": search})
        if query:
            queryset = queryset.filter(query)

    ordering = model_admin.get_ordering(request)
    if ordering:
        queryset = queryset.order_by(*ordering)
    page = Paginator(queryset, 50).get_page(request.GET.get("page"))
    columns = []
    for field_name in model_admin.get_list_display(request):
        try:
            label = label_for_field(field_name, model, model_admin)
        except (AttributeError, TypeError):
            label = str(field_name).replace("_", " ").capitalize()
        columns.append({"name": str(field_name), "label": str(label)})
    rows = [
        {
            "pk": str(obj.pk),
            "values": {
                column["name"]: _list_value(model_admin, column["name"], obj)
                for column in columns
            },
        }
        for obj in page.object_list
    ]
    return JsonResponse(
        {
            "app_label": app_label,
            "model_name": model_name,
            "label": str(model._meta.verbose_name_plural).capitalize(),
            "columns": columns,
            "rows": rows,
            "page": page.number,
            "pages": page.paginator.num_pages,
            "total": page.paginator.count,
            "can_add": _has_model_permission(request, model_admin, "add"),
            "can_change": _has_model_permission(request, model_admin, "change"),
            "can_delete": _has_model_permission(request, model_admin, "delete"),
        }
    )


@require_http_methods(["GET", "POST"])
def admin_model_form_api(request, app_label, model_name):
    denied = _admin_required(request)
    if denied:
        return denied
    model, model_admin = _registered_model(app_label, model_name)
    if model is None:
        return JsonResponse({"error": "Modèle introuvable."}, status=404)
    if not _has_model_permission(request, model_admin, "add"):
        return JsonResponse({"error": "Création interdite."}, status=403)
    if request.method == "POST":
        saved, form = _save_form(request, model, model_admin)
        if saved is None:
            return JsonResponse({"errors": _form_errors(form)}, status=400)
        return JsonResponse({"ok": True, "pk": str(saved.pk)})
    return JsonResponse(
        {
            "label": f"Créer {model._meta.verbose_name}",
            "fields": _form_schema(model_admin, request),
        }
    )


@require_http_methods(["GET", "POST"])
def admin_model_detail_api(request, app_label, model_name, pk):
    denied = _admin_required(request)
    if denied:
        return denied
    model, model_admin = _registered_model(app_label, model_name)
    if model is None:
        return JsonResponse({"error": "Modèle introuvable."}, status=404)
    obj = get_object_or_404(model_admin.get_queryset(request), pk=pk)

    if request.method == "POST" and request.POST.get("action") == "delete":
        if not _has_model_permission(request, model_admin, "delete", obj):
            return JsonResponse({"error": "Suppression interdite."}, status=403)
        with transaction.atomic():
            model_admin.log_deletion(request, obj, str(obj))
            model_admin.delete_model(request, obj)
        return JsonResponse({"ok": True})

    if request.method == "POST":
        if not _has_model_permission(request, model_admin, "change", obj):
            return JsonResponse({"error": "Modification interdite."}, status=403)
        saved, form = _save_form(request, model, model_admin, obj)
        if saved is None:
            return JsonResponse({"errors": _form_errors(form)}, status=400)
        return JsonResponse({"ok": True, "pk": str(saved.pk)})

    if not (
        _has_model_permission(request, model_admin, "view", obj)
        or _has_model_permission(request, model_admin, "change", obj)
    ):
        return JsonResponse({"error": "Consultation interdite."}, status=403)
    if not _has_model_permission(request, model_admin, "change", obj):
        return JsonResponse({"error": "Modification interdite."}, status=403)
    return JsonResponse(
        {
            "label": str(obj),
            "fields": _form_schema(model_admin, request, obj),
            "can_delete": _has_model_permission(request, model_admin, "delete", obj),
        }
    )


def admin_react_app(request, path=""):
    return react_app(request)
