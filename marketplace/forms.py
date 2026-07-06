# forms.py — form classes for user input across the system.
# Each form handles validation before data reaches the database.
# The CheckoutForm enforces the 48-hour minimum delivery date here.

from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import CustomUser, Product, CommunityPost, RecallNotice, Review

UK_ALLERGENS = [
    ('Celery', 'Celery'),
    ('Cereals containing gluten', 'Cereals containing gluten (Wheat, Rye, Barley, Oats)'),
    ('Crustaceans', 'Crustaceans'),
    ('Eggs', 'Eggs'),
    ('Fish', 'Fish'),
    ('Lupin', 'Lupin'),
    ('Milk', 'Milk'),
    ('Molluscs', 'Molluscs'),
    ('Mustard', 'Mustard'),
    ('Peanuts', 'Peanuts'),
    ('Sesame seeds', 'Sesame seeds'),
    ('Soya', 'Soya'),
    ('Sulphites', 'Sulphur dioxide and sulphites'),
    ('Tree nuts', 'Tree nuts (Almonds, Hazelnuts, Walnuts, Cashews, Pecans, Brazil nuts, Pistachios, Macadamia)'),
]


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
    # Card payment fields — the actual charge is simulated, see payments.py
    card_number = forms.CharField(
        max_length=19, label='Card number',
        widget=forms.TextInput(attrs={'placeholder': '4242 4242 4242 4242', 'autocomplete': 'off'}),
    )
    card_expiry = forms.CharField(
        max_length=5, label='Expiry (MM/YY)',
        widget=forms.TextInput(attrs={'placeholder': 'MM/YY', 'autocomplete': 'off'}),
    )
    card_cvv = forms.CharField(
        max_length=4, label='CVV',
        widget=forms.TextInput(attrs={'placeholder': '123', 'autocomplete': 'off'}),
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

    def clean_card_number(self):
        number = self.cleaned_data.get('card_number', '').replace(' ', '')
        if not number.isdigit() or len(number) != 16:
            raise forms.ValidationError('Card number must be 16 digits.')
        return number

    def clean_card_cvv(self):
        cvv = self.cleaned_data.get('card_cvv', '').strip()
        if not cvv.isdigit() or len(cvv) not in (3, 4):
            raise forms.ValidationError('CVV must be 3 or 4 digits.')
        return cvv

    def clean_card_expiry(self):
        from datetime import date
        expiry = self.cleaned_data.get('card_expiry', '').strip()
        try:
            month, year = expiry.split('/')
            month, year = int(month), int(year) + 2000
            if not 1 <= month <= 12:
                raise ValueError
        except ValueError:
            raise forms.ValidationError('Enter expiry as MM/YY, e.g. 08/27.')
        # A card is usable until the end of its expiry month
        if (year, month) < (date.today().year, date.today().month):
            raise forms.ValidationError('This card has expired.')
        return expiry

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
        fields = ['post_type', 'title', 'content', 'product', 'image_url']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
            'image_url': forms.URLInput(attrs={'placeholder': 'https://example.com/image.jpg'}),
        }
        labels = {
            'image_url': 'Image URL (optional)',
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
    allergen_choices = forms.MultipleChoiceField(
        choices=UK_ALLERGENS,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Allergens (select all that apply)',
        help_text='All 14 major allergens recognised by UK law',
    )

    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'price', 'stock',
            'is_organic', 'harvest_date', 'best_before',
            'farm_origin', 'is_seasonal', 'seasonal_months',
            'season_start_month', 'season_end_month',
            'lead_time_hours', 'low_stock_threshold', 'is_active',
        ]
        widgets = {
            'harvest_date': forms.DateInput(attrs={'type': 'date'}),
            'best_before': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'seasonal_months': forms.TextInput(attrs={'placeholder': 'e.g. June – August (display label only)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.allergens:
            known_values = {v for v, _ in UK_ALLERGENS}
            existing = [a.strip() for a in self.instance.allergens.split(',') if a.strip()]
            self.initial['allergen_choices'] = [v for v in existing if v in known_values]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.allergens = ', '.join(self.cleaned_data.get('allergen_choices', []))
        if commit:
            instance.save()
        return instance


# Form for customers to leave a verified review on a product they have received
class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(i, f'{"★" * i}{"☆" * (5 - i)}  ({i} star{"s" if i > 1 else ""})') for i in range(1, 6)],
        coerce=int,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Review
        fields = ['rating', 'title', 'body']
        widgets = {
            'body': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'body': 'Your review',
        }
