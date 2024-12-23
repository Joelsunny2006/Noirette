from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import datetime
import re
from .models import *

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = [
            'code', 'discount_type', 'discount_value', 
            'valid_from', 'valid_to', 'min_purchase_amount', 
            'usage_limit'
        ]
        widgets = {
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code:
            raise forms.ValidationError("Coupon code is required.")
        
        # Check if code follows the pattern (alphanumeric, min 6, max 20 chars)
        if not re.match("^[A-Za-z0-9]{6,20}$", code):
            raise forms.ValidationError(
                "Coupon code must be 6-20 characters long and contain only letters and numbers."
            )
        
        # Check for uniqueness (case-insensitive)
        if Coupon.objects.filter(code__iexact=code).exists():
            if self.instance and self.instance.code.upper() == code.upper():
                return code
            raise forms.ValidationError("This coupon code already exists.")
            
        return code.upper()

    def clean_discount_value(self):
        discount_type = self.cleaned_data.get('discount_type')
        value = self.cleaned_data.get('discount_value')

        if not value:
            raise forms.ValidationError("Discount value is required.")

        if value <= 0:
            raise forms.ValidationError("Discount value must be greater than 0.")

        if discount_type == 'percentage':
            if value > 100:
                raise forms.ValidationError("Percentage discount cannot exceed 100%.")
        else:  # fixed amount
            if value > 10000:  # Assuming $10000 is max discount
                raise forms.ValidationError("Fixed discount cannot exceed $10,000.")

        return value

    def clean_min_purchase_amount(self):
        amount = self.cleaned_data.get('min_purchase_amount')
        if amount is not None:
            if amount < 0:
                raise forms.ValidationError("Minimum purchase amount cannot be negative.")
            if amount > 100000:  # Assuming $100000 is max purchase requirement
                raise forms.ValidationError("Minimum purchase amount cannot exceed $100,000.")
        return amount

    def clean_usage_limit(self):
        limit = self.cleaned_data.get('usage_limit')
        if limit is not None:
            if limit < 1:
                raise forms.ValidationError("Usage limit must be at least 1.")
            if limit > 10000:  # Assuming 10000 is max usage limit
                raise forms.ValidationError("Usage limit cannot exceed 10,000.")
        return limit

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        
        if valid_from and valid_to:
            # Check if dates are in the past
            if valid_from < timezone.now():
                raise forms.ValidationError({
                    'valid_from': "Start date cannot be in the past."
                })

            # Check if end date is after start date
            if valid_to <= valid_from:
                raise forms.ValidationError({
                    'valid_to': "End date must be after start date."
                })

            # Check if duration is not too long (e.g., 1 year max)
            max_duration = timezone.timedelta(days=365)
            if valid_to - valid_from > max_duration:
                raise forms.ValidationError({
                    'valid_to': "Coupon duration cannot exceed 1 year."
                })

        return cleaned_data