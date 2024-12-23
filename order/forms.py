from django import forms
from .models import Address
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.validators import RegexValidator

class AddressForm(forms.ModelForm):
    # Regex validator for validating phone numbers
    phone = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$', 
                message="Phone number must be entered in the format: '+999999999'. Up to 10 digits allowed."
            )
        ]
    )
    

    class Meta:
        model = Address
        fields = [
            'first_name', 'last_name', 'street_address', 'apartment', 
            'city', 'state', 'postcode', 'phone', 'email', 'is_default', 
        ]

    # forms.py
from django import forms
from .models import Address

class CheckoutForm(forms.Form):
    saved_address = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label="Saved Address",
        widget=forms.RadioSelect,
    )
    first_name = forms.CharField(max_length=50, required=False)
    last_name = forms.CharField(max_length=50, required=False)
    street_address = forms.CharField(max_length=255, required=False)
    apartment = forms.CharField(max_length=50, required=False)
    city = forms.CharField(max_length=50, required=False)
    postcode = forms.CharField(max_length=20, required=False)
    phone = forms.CharField(max_length=15, required=False)
    email = forms.EmailField(required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['saved_address'].queryset = Address.objects.filter(user=user)

    def clean(self):
        cleaned_data = super().clean()
        saved_address = cleaned_data.get('saved_address')
        if not saved_address and not all(cleaned_data.get(field) for field in [
            'first_name', 'last_name', 'street_address', 'city', 'postcode', 'phone', 'email'
        ]):
            raise forms.ValidationError("Please provide a complete address or select a saved one.")
        return cleaned_data
