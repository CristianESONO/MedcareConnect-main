"""
Inscription patient — base de test pytest uniquement (jamais la prod).
"""

import uuid

import pytest
from django.urls import reverse

from users.models import User


@pytest.mark.django_db
def test_inscription_patient_cree_compte(client):
    suffix = uuid.uuid4().hex[:8]
    username = f"qa_inscrit_{suffix}"
    r = client.post(
        reverse("users:register"),
        data={
            "username": username,
            "email": f"{username}@qa.test",
            "password1": "Test-Inscrit-QA-123!",
            "password2": "Test-Inscrit-QA-123!",
            "user_type": "patient",
        },
        follow=False,
    )
    assert r.status_code == 302
    assert User.objects.filter(username=username, user_type="patient").exists()
