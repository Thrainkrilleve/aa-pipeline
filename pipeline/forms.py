"""Forms for the in-app flow manager."""

# Django
from django import forms
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .models import FlowStatus, FlowStep, FlowType, OnboardingFlow, StepType


class FlowForm(forms.ModelForm):
    class Meta:
        model = OnboardingFlow
        fields = [
            "name",
            "slug",
            "description",
            "body_complete",
            "flow_type",
            "status",
            "auto_assign",
            "states",
            "groups",
            "corporations",
            "alliances",
            "factions",
            "characters",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "body_complete": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "flow_type": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "auto_assign": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "states": forms.SelectMultiple(attrs={"class": "form-select pipeline-multiselect", "size": "7"}),
            "groups": forms.SelectMultiple(attrs={"class": "form-select pipeline-multiselect", "size": "7"}),
            "corporations": forms.SelectMultiple(attrs={"class": "form-select pipeline-multiselect", "size": "7"}),
            "alliances": forms.SelectMultiple(attrs={"class": "form-select pipeline-multiselect", "size": "7"}),
            "factions": forms.SelectMultiple(attrs={"class": "form-select pipeline-multiselect", "size": "7"}),
            "characters": forms.SelectMultiple(attrs={"class": "form-select pipeline-multiselect", "size": "7"}),
        }
        help_texts = {
            "slug": _("Leave blank to auto-generate from the name."),
            "body_complete": _(
                "Shown when the user finishes all required steps. Supports Markdown. "
                "Use {{ user }} for their username."
            ),
            "auto_assign": _(
                "Automatically assign to users who match the audience when their profile updates."
            ),
        }

    def clean_slug(self):
        slug = self.cleaned_data.get("slug", "").strip()
        if not slug:
            slug = slugify(self.cleaned_data.get("name", ""))
        return slug


class FlowStepForm(forms.ModelForm):
    class Meta:
        model = FlowStep
        fields = [
            "name",
            "description",
            "body",
            "step_type",
            "order",
            "optional",
            "service_slug",
            "service_fallback_acknowledgement",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 8}),
            "step_type": forms.Select(attrs={"class": "form-select"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "optional": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "service_slug": forms.TextInput(attrs={"class": "form-control"}),
            "service_fallback_acknowledgement": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
        help_texts = {
            "body": _(
                "Main content shown to the user. Supports Markdown if the markdown "
                "package is installed."
            ),
            "service_slug": _(
                "Only required for service_check steps. "
                "e.g. discord, mumble, teamspeak3"
            ),
            "service_fallback_acknowledgement": _(
                "If the service is not installed, fall back to acknowledgement mode."
            ),
        }
