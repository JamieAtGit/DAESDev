from django import forms
from .models import SurplusProduce


# Form for producers to list short-dated or excess stock at a discount
class SurplusProduceForm(forms.ModelForm):
    class Meta:
        model = SurplusProduce
        fields = ['product', 'original_price', 'discounted_price', 'quantity_available', 'reason', 'available_until']
        widgets = {
            'available_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'reason': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        # Platform rules: discount must be meaningful (≥10%) but not so steep it devalues products (≤50%)
        cleaned_data = super().clean()
        original = cleaned_data.get('original_price')
        discounted = cleaned_data.get('discounted_price')
        if original and discounted:
            if discounted >= original:
                raise forms.ValidationError('Discounted price must be lower than the original price.')
            discount_pct = ((original - discounted) / original) * 100
            if discount_pct < 10:
                raise forms.ValidationError('Discount must be at least 10%.')
            if discount_pct > 50:
                raise forms.ValidationError('Discount cannot exceed 50%.')
        return cleaned_data
