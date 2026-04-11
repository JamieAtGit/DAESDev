from django import forms
from .models import SurplusProduce


class SurplusProduceForm(forms.ModelForm):
    class Meta:
        model = SurplusProduce
        fields = ['product', 'original_price', 'discounted_price', 'quantity_available', 'reason', 'available_until']
        widgets = {
            'available_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'reason': forms.Textarea(attrs={'rows': 2}),
        }
