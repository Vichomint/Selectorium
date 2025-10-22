# matchmaker/forms.py
from django import forms
from .models import Job

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ["titulo", "descripcion", "skills_obligatorias", "skills_deseables"]
        widgets = {
            "descripcion": forms.Textarea(attrs={
                "class": "w-full border rounded p-2",
                "rows": 4,
                "placeholder": "Describe brevemente el cargo..."
            }),
        }
