from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from users.models import *

class Wallet(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit')
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"Wallet for {self.user.username}"

class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=Wallet.TRANSACTION_TYPES)
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.amount} - {self.timestamp}"

    def save(self, *args, **kwargs):
        # Update wallet balance when transaction is saved
        super().save(*args, **kwargs)
        if self.transaction_type == 'credit':
            self.wallet.balance += self.amount
        elif self.transaction_type == 'debit':
            self.wallet.balance -= self.amount
        self.wallet.save()