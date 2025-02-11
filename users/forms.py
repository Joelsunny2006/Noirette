from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
import re
from .models import UserProfile
import phonenumbers
from django.utils import timezone
from django.contrib.auth.hashers import check_password

class SignUpForm(forms.ModelForm):
    username = forms.CharField(
        min_length=3,
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 bg-white text-black border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500',
            'placeholder': 'Username',
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 bg-white text-black border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500',
            'placeholder': 'Email',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 bg-white text-black border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500',
            'placeholder': 'Password',
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 bg-white text-black border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500',
            'placeholder': 'Confirm Password',
        })
    )

    class Meta:
        model = UserProfile
        fields = ['username', 'email', 'password', 'confirm_password']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        
        # Check for minimum and maximum length
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")
        if len(username) > 30:
            raise ValidationError("Username cannot exceed 30 characters.")
        
        # Check for valid characters
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("Username can only contain letters, numbers, and underscores.")
        
        # Check if username already exists
        if UserProfile.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")
        
        # Check for offensive words (expand this list as needed)
        offensive_words = ['admin', 'root', 'superuser', 'administrator']
        if username.lower() in offensive_words:
            raise ValidationError("This username is not allowed.")
        
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Basic email format validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError("Please enter a valid email address.")
        
        # Check for disposable email domains (expand this list as needed)
        disposable_domains = ['tempmail.com', 'throwaway.com']
        domain = email.split('@')[1]
        if domain in disposable_domains:
            raise ValidationError("Please use a valid email address. Disposable email addresses are not allowed.")
        
        # Check if email already exists
        if UserProfile.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email is already registered.")
        
        return email.lower()

    def clean_password(self):
        password = self.cleaned_data.get('password')
        
        # Check minimum length
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        # Check for maximum length to prevent DOS attacks
        if len(password) > 128:
            raise ValidationError("Password cannot exceed 128 characters.")
        
        # Check for complexity requirements
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r'[0-9]', password):
            raise ValidationError("Password must contain at least one number.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password must contain at least one special character.")
        
        # Check for common passwords (expand this list as needed)
        common_passwords = ['password123', 'admin123', '12345678']
        if password.lower() in common_passwords:
            raise ValidationError("This password is too common. Please choose a stronger password.")
        
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        username = cleaned_data.get('username', '').lower()  # Default to empty string if username is None
        email = cleaned_data.get('email', '').lower()  # Default to empty string if email is None
        email_prefix = email.split('@')[0] if email else ''

        if password and confirm_password:
            # Check if passwords match
            if password != confirm_password:
                raise ValidationError("Passwords do not match.")

            # Check if password contains personal information
            if username and username in password.lower():
                raise ValidationError("Password cannot contain your username.")

            if email_prefix and email_prefix in password.lower():
                raise ValidationError("Password cannot contain your email address.")

        return cleaned_data


    def get_error_messages(self):
            """Returns all form errors as a list of strings"""
            errors = []
            for field, field_errors in self.errors.items():
                if field == '__all__':  # Non-field errors
                    errors.extend([str(e) for e in field_errors])
                else:
                    field_name = self.fields[field].label or field
                    errors.extend([f"{field_name}: {str(e)}" for e in field_errors])
            return errors
class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-amber-500 focus:border-amber-500',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-amber-500 focus:border-amber-500',
            'autocomplete': 'current-password'
        })
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if not email:
            raise ValidationError("Email is required.")
        if not password:
            raise ValidationError("Password is required.")

        # Normalize email to lowercase
        email = email.lower()

        # Check for too many failed login attempts
        if self.request:
            failed_attempts = self.request.session.get('failed_login_attempts', 0)
            last_attempt = self.request.session.get('last_login_attempt')
            
            if failed_attempts >= 5:
                if last_attempt and (timezone.now() - timezone.datetime.fromtimestamp(last_attempt)).seconds < 300:
                    raise ValidationError("Too many failed login attempts. Please try again in 5 minutes.")
                else:
                    # Reset counter after timeout
                    self.request.session['failed_login_attempts'] = 0
                    failed_attempts = 0

        # Attempt authentication
        user = authenticate(self.request, username=email, password=password)



        if user is None:
            if self.request:
                # Increment failed attempts counter
                self.request.session['failed_login_attempts'] = failed_attempts + 1
                self.request.session['last_login_attempt'] = timezone.now().timestamp()
            raise ValidationError("Invalid email or password.")

        if not user.is_active:
            raise ValidationError("Your account is inactive. Please verify your email or contact support.")

        if user.is_blocked:
            raise ValidationError("Your account has been blocked. Please contact support.")

        cleaned_data['user'] = user
        return cleaned_data
    
    def get_error_messages(self):
            """Returns all form errors as a list of strings"""
            errors = []
            for field, field_errors in self.errors.items():
                if field == '__all__':
                    errors.extend([str(e) for e in field_errors])
                else:
                    field_name = self.fields[field].label or field
                    errors.extend([f"{field_name}: {str(e)}" for e in field_errors])
            return errors

class OTPForm(forms.Form):
    otp_code = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'otp-input w-full px-3 py-2 bg-white text-black border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500',
            'placeholder': 'Enter OTP',
            'maxlength': '6',
            'minlength': '6'
        }),
        max_length=6,
        min_length=6,
        required=True,
    )

    def clean_otp_code(self):
        otp_code = self.cleaned_data.get('otp_code')
        
        # Check if OTP is numeric
        if not otp_code.isdigit():
            raise ValidationError("OTP must contain only numbers.")
        
        # Check length
        if len(otp_code) != 6:
            raise ValidationError("OTP must be exactly 6 digits.")
        
        # Check for sequential numbers
        if otp_code in ['123456', '654321']:
            raise ValidationError("Invalid OTP code.")
        
        # Check for repeated numbers
        if len(set(otp_code)) == 1:
            raise ValidationError("Invalid OTP code.")
        
        return otp_code

class PasswordResetForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 bg-white text-black border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500',
            'placeholder': 'New Password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 bg-white text-black border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500',
            'placeholder': 'Confirm New Password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError("Passwords do not match.")
            
            # Reuse password validation from SignUpForm
            if len(password) < 8:
                raise ValidationError("Password must be at least 8 characters long.")
            if len(password) > 128:
                raise ValidationError("Password cannot exceed 128 characters.")
            if not re.search(r'[A-Z]', password):
                raise ValidationError("Password must contain at least one uppercase letter.")
            if not re.search(r'[a-z]', password):
                raise ValidationError("Password must contain at least one lowercase letter.")
            if not re.search(r'[0-9]', password):
                raise ValidationError("Password must contain at least one number.")
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                raise ValidationError("Password must contain at least one special character.")
            
        return cleaned_data