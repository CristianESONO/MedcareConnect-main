from django.urls import path

from . import admin_api

app_name = "react_admin"

urlpatterns = [
    path("api/session/", admin_api.admin_login_api, name="session"),
    path("api/logout/", admin_api.admin_logout_api, name="logout"),
    path("api/models/", admin_api.admin_models_api, name="models"),
    path(
        "api/models/<str:app_label>/<str:model_name>/form/",
        admin_api.admin_model_form_api,
        name="model_form",
    ),
    path(
        "api/models/<str:app_label>/<str:model_name>/<str:pk>/",
        admin_api.admin_model_detail_api,
        name="model_detail",
    ),
    path(
        "api/models/<str:app_label>/<str:model_name>/",
        admin_api.admin_model_collection_api,
        name="model_collection",
    ),
    path("", admin_api.admin_react_app, name="home"),
    path("<path:path>", admin_api.admin_react_app, name="react_app"),
]
