from django import forms
from .models import Address
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.validators import RegexValidator

class AddressForm(forms.ModelForm):
    # First Name, Last Name, City, and State: Only alphabets, no spaces or numbers
    alpha_validator = RegexValidator(
        regex=r'^[A-Za-z]+$',
        message="Only alphabets are allowed (No spaces or numbers)."
    )
    
    first_name = forms.CharField(validators=[alpha_validator], max_length=50)
    last_name = forms.CharField(validators=[alpha_validator], max_length=50)
    city = forms.CharField(validators=[alpha_validator], max_length=50)
    state = forms.CharField(validators=[alpha_validator], max_length=50)

    # Phone Number: Only digits (10-15 characters, no spaces)
    phone = forms.CharField(
        validators=[RegexValidator(regex=r'^\d{10,15}$', message="Only digits allowed (10-15 numbers, no spaces).")],
        max_length=15
    )

    # Postcode: Only digits (5-10 characters, no spaces)
    postcode = forms.CharField(
        validators=[RegexValidator(regex=r'^\d{5,10}$', message="Only digits allowed (5-10 numbers, no spaces).")],
        max_length=10
    )

    class Meta:
        model = Address
        fields = [
            'first_name', 'last_name', 'street_address', 'apartment', 
            'city', 'state', 'postcode', 'phone', 'email', 'is_default'
        ]
    def clean(self):
        cleaned_data = super().clean()
        required_fields = ['first_name', 'last_name', 'street_address', 'city', 'state', 'postcode', 'phone', 'email']
        for field in required_fields:
            if not cleaned_data.get(field):
                self.add_error(field, f"{field.replace('_', ' ').title()} is required.")
        return cleaned_data
    

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
