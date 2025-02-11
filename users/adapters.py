from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from users.models import UserProfile
from allauth.exceptions import ImmediateHttpResponse

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Extract email and username from the social account's extra data
        user_data = sociallogin.account.extra_data
        email = user_data.get('email')
        if not email:
            # You might want to handle cases where email is not provided
            messages.error(request, "No email found in social account data.")
            raise ImmediateHttpResponse(HttpResponseRedirect(reverse('login')))

        username = user_data.get('name') or email.split('@')[0]

        # If the social account is already connected to a user, use that
        if sociallogin.is_existing:
            user = sociallogin.user
            if user.is_blocked:
                messages.error(request, "Your account has been blocked. Please contact support.")
                raise ImmediateHttpResponse(HttpResponseRedirect(reverse('login')))
            return

        try:
            # Check if a user with this email already exists
            user = UserProfile.objects.get(email=email)
            if user.is_blocked:
                messages.error(request, "Your account has been blocked. Please contact support.")
                raise ImmediateHttpResponse(HttpResponseRedirect(reverse('login')))
        except UserProfile.DoesNotExist:
            # Create a new user if one doesn't exist
            user = UserProfile(
                email=email,
                username=username,
                is_active=True,
                is_admin=False,
            )
            # It's often better to generate a secure random password
            user.set_password(UserProfile.objects.make_random_password())
            user.save()

        # Connect the social account with the user
        sociallogin.connect(request, user)

