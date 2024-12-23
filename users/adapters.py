from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.contrib import messages

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get('email')
        if not email:
            messages.error(request, "No email found with Google account.")
            return redirect('login')  # Redirect to login page

        # Find users with this email
        users = User.objects.filter(email=email)
        
        if users.count() > 1:
            # Log multiple users scenario
            messages.warning(request, "Multiple accounts found. Contact support.")
            return redirect('login')

        try:
            # Connect existing user if email exists
            existing_user = users.first()
            if existing_user:
                sociallogin.connect(request, existing_user)
                return redirect('home')  # Redirect to home page after login
        
        except Exception as e:
            messages.error(request, f"Login error: {e}")
            return redirect('login')