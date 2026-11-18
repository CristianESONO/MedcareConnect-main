import json

from django import forms
from django.test import SimpleTestCase

from healthcare.views import _form_fields_json


class ProviderPortalFormJsonTests(SimpleTestCase):
    def test_file_and_checkbox_fields_are_json_serializable(self):
        class PortalForm(forms.Form):
            logo = forms.FileField(required=False)
            services = forms.MultipleChoiceField(
                choices=(("lab", "Laboratoire"), ("imaging", "Imagerie")),
                widget=forms.CheckboxSelectMultiple,
                initial=("lab",),
            )
            enabled = forms.BooleanField(required=False, initial=True)

        fields = _form_fields_json(PortalForm())
        json.dumps(fields)
        by_name = {field["name"]: field for field in fields}

        self.assertEqual(by_name["logo"]["type"], "file")
        self.assertIsNone(by_name["logo"]["value"])
        self.assertEqual(by_name["services"]["type"], "checkboxes")
        self.assertEqual(by_name["services"]["value"], ["lab"])
        self.assertEqual(by_name["enabled"]["type"], "checkbox")
        self.assertTrue(by_name["enabled"]["value"])
