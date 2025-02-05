from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from users.models import *
from django.db.models import Sum

class Wallet(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit')
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"Wallet for {self.user.username}"
    
    def update_balance(self):
        """Recalculate balance from transactions"""
        total_credited = self.transactions.filter(transaction_type='credit').aggregate(Sum('amount'))['amount__sum'] or 0
        total_debited = self.transactions.filter(transaction_type='debit').aggregate(Sum('amount'))['amount__sum'] or 0
        self.balance = total_credited - total_debited
        self.save()



class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=Wallet.TRANSACTION_TYPES)
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.amount} - {self.timestamp}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.wallet.update_balance()  # Ensure balance is always recalculated
