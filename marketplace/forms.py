from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import CustomUser, Product, CommunityPost, RecallNotice


# Registration form for regular customers — captures delivery details at sign-up
class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False, label='Phone number')
    delivery_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False, label='Delivery address')
    delivery_postcode = forms.CharField(max_length=10, required=False, label='Postcode')

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'delivery_address', 'delivery_postcode', 'password1', 'password2']

    def clean_email(self):
        # Prevent two accounts sharing the same email address
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        # Set the role to 'customer' before saving the new user
        user = super().save(commit=False)
        user.role = 'customer'
        user.phone = self.cleaned_data.get('phone', '')
        user.delivery_address = self.cleaned_data.get('delivery_address', '')
        user.delivery_postcode = self.cleaned_data.get('delivery_postcode', '')
        if commit:
            user.save()
        return user


# Registration form for producers — includes extra fields for their business profile
class ProducerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False, label='Phone number')
    business_name = forms.CharField(max_length=200)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    postcode = forms.CharField(max_length=10)
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'password1', 'password2']

    def clean_email(self):
        # Prevent two accounts sharing the same email address
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


# Registration form for community groups (e.g. schools, food banks) — similar to customer but captures organisation name
class CommunityGroupRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False, label='Phone number')
    organisation_name = forms.CharField(max_length=200, label='Organisation name')
    delivery_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), label='Delivery address')
    delivery_postcode = forms.CharField(max_length=10, label='Postcode')

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'organisation_name', 'delivery_address', 'delivery_postcode', 'password1', 'password2']

    def clean_email(self):
        # Prevent two accounts sharing the same email address
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


# Form shown at checkout — collects delivery details and optional recurring order preferences
class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=200)
    email = forms.EmailField()
    postcode = forms.CharField(max_length=10)
    delivery_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    delivery_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    special_instructions = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        label='Special instructions (optional)',
        help_text='e.g. Delivery to kitchen entrance, contact kitchen manager',
    )
    # Recurring order fields — only required if the customer ticks the checkbox
    make_recurring = forms.BooleanField(required=False, label='Make this a recurring weekly order')
    recurrence_day = forms.ChoiceField(
        choices=[('', '-- Select day --'), ('monday', 'Monday'), ('tuesday', 'Tuesday'),
                 ('wednesday', 'Wednesday'), ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday')],
        required=False, label='Order placed every',
    )
    delivery_day = forms.ChoiceField(
        choices=[('', '-- Select day --'), ('monday', 'Monday'), ('tuesday', 'Tuesday'),
                 ('wednesday', 'Wednesday'), ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday')],
        required=False, label='Delivered every',
    )

    def clean(self):
        # If recurring is ticked, both day fields must also be filled in
        cleaned_data = super().clean()
        if cleaned_data.get('make_recurring'):
            if not cleaned_data.get('recurrence_day'):
                raise forms.ValidationError('Please select the day your recurring order should be placed.')
            if not cleaned_data.get('delivery_day'):
                raise forms.ValidationError('Please select your preferred delivery day.')
        return cleaned_data

    def clean_delivery_date(self):
        # Enforce the minimum 48-hour lead time required by producers
        from datetime import date, timedelta
        delivery_date = self.cleaned_data.get('delivery_date')
        min_date = date.today() + timedelta(hours=48)
        if delivery_date < min_date:
            raise forms.ValidationError('Delivery must be at least 48 hours from now.')
        return delivery_date


# Form for producers to write and share a community post (story, recipe, or storage tip)
class CommunityPostForm(forms.ModelForm):
    class Meta:
        model = CommunityPost
        fields = ['post_type', 'title', 'content', 'product']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
        }


# Form for producers to issue a food safety recall notice for one of their products
class RecallNoticeForm(forms.ModelForm):
    class Meta:
        model = RecallNotice
        fields = ['product', 'reason', 'batch_info', 'affected_from', 'affected_to']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3}),
            'affected_from': forms.DateInput(attrs={'type': 'date'}),
            'affected_to': forms.DateInput(attrs={'type': 'date'}),
        }


# Form for producers to create or edit a product listing
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
