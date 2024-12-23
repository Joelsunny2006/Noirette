from django.contrib.auth.models import AbstractBaseUser , BaseUserManager
from django.db import models
from datetime import timedelta
from django.utils import timezone

class UserProfileManager(BaseUserManager):
    def create_user(self, username, email, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        if not username:
            raise ValueError("Users must have a username")

        user = self.model(
            email=self.normalize_email(email),
            username=username,
        )
        if password:
            user.set_password(password)  # Use set_password to hash the password
        else:
            raise ValueError("Users must have a password")
        user.save(using=self._db)
        return user


    def create_superuser(self, username, email, password=None):
        if password is None:
            raise ValueError("Superusers must have a password")

        user = self.create_user(username, email, password)
        user.is_admin = True
        user.save(using=self._db)
        return user

class UserProfile(AbstractBaseUser ):
    username = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=False) 
    is_blocked = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    objects = UserProfileManager()


    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return self.is_admin
    
    @property
    def is_superuser(self):
        return self.is_admin



class OTP(models.Model):
    # Changed from User to UserProfile
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)  
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        expiration_time = self.created_at + timedelta(minutes=3)  
        return timezone.now() > expiration_time

    def __str__(self):
        return f"OTP for {self.user.username}"
    