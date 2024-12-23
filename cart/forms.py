from django import forms
from django.core.validators import RegexValidator
from order.models import Address

PAYMENT_CHOICES = [
    ('COD', 'Cash on Delivery'),
    ('bank', 'Direct Bank Transfer'),
    ('check', 'Check Payment'),
    ('paypal', 'PayPal'),
]

class CheckoutForm(forms.Form):
    # Saved Address Selection
    saved_address = forms.ChoiceField(
        choices=[],  # Initially empty
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    # New Address Fields
    first_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
    )
    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
    )
    street_address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street Address'}),
    )
    apartment = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apartment (optional)'}),
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
    )
    postcode = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postcode/ZIP'}),
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone'}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
    )

    # Payment Method
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect,
    )

    # Terms and Conditions
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput,
        error_messages={'required': 'You must accept the terms and conditions'},
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Populate the saved_address field with the user's saved addresses
            self.fields['saved_address'].queryset = Address.objects.filter(user=user)

    def clean(self):
        cleaned_data = super().clean()

        # If no saved address is selected, ensure new address fields are filled
        saved_address = cleaned_data.get('saved_address')
        if not saved_address:
            required_fields = ['first_name', 'last_name', 'street_address', 'city', 'postcode', 'phone', 'email']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, 'This field is required when no saved address is selected.')

        return cleaned_data
