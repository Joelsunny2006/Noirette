from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from users.models import UserProfile

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return

        user_data = sociallogin.account.extra_data
        email = user_data.get('email')
        username = user_data.get('name') or email.split('@')[0]

        try:
            user = UserProfile.objects.get(email=email)
        except UserProfile.DoesNotExist:
            user = UserProfile.objects.create(
                email=email,
                username=username,
                is_active=True,
                is_admin=False,
            )
            user.set_password('randompassword')  # Temporarily set a password
            user.save()

        sociallogin.connect(request, user)
