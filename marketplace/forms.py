from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import CustomUser, Product


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'customer'
        if commit:
            user.save()
        return user


class ProducerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    business_name = forms.CharField(max_length=200)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    postcode = forms.CharField(max_length=10)
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=200)
    email = forms.EmailField()
    postcode = forms.CharField(max_length=10)
    delivery_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    delivery_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    def clean_delivery_date(self):
        from datetime import date, timedelta
        delivery_date = self.cleaned_data.get('delivery_date')
        min_date = date.today() + timedelta(hours=48)
        if delivery_date < min_date:
            raise forms.ValidationError('Delivery must be at least 48 hours from now.')
        return delivery_date


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'price', 'stock',
            'allergens', 'is_organic', 'harvest_date', 'best_before',
            'farm_origin', 'is_seasonal', 'seasonal_months',
            'lead_time_hours', 'is_active',
        ]
        widgets = {
            'harvest_date': forms.DateInput(attrs={'type': 'date'}),
            'best_before': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'allergens': forms.Textarea(attrs={'rows': 2}),
        }
